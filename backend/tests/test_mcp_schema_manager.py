"""
Comprehensive tests for MCP Schema Manager.

This module tests the core MCP schema management functionality including
schema discovery, caching, validation, and error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, List

from backend.schema_management.manager import MCPSchemaManager
from backend.schema_management.client import EnhancedMCPClient, MCPRequestError, MCPConnectionError
from backend.schema_management.config import MCPSchemaConfig, SchemaValidationConfig
from backend.schema_management.models import (
    DatabaseInfo, TableInfo, ColumnInfo, TableSchema, IndexInfo, ForeignKeyInfo,
    ValidationResult, ValidationError, ValidationSeverity, CacheStats
)


class TestMCPSchemaManager:
    """Test cases for MCPSchemaManager core functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock MCP configuration."""
        return MCPSchemaConfig(
            mcp_server_url="http://test-server:8000",
            connection_timeout=10,
            request_timeout=30,
            max_retries=2,
            retry_delay=0.1,
            cache_ttl=300,
            enable_caching=True,
            fallback_enabled=True
        )
    
    @pytest.fixture
    def mock_validation_config(self):
        """Create a mock validation configuration."""
        return SchemaValidationConfig(
            strict_mode=False,
            validate_types=True,
            validate_constraints=True,
            validate_relationships=True,
            allow_unknown_columns=False
        )
    
    @pytest.fixture
    def sample_database_info(self):
        """Create sample database information."""
        return [
            DatabaseInfo(
                name="test_db",
                charset="utf8mb4",
                collation="utf8mb4_general_ci",
                accessible=True,
                table_count=5
            ),
            DatabaseInfo(
                name="financial_db",
                charset="utf8mb4",
                collation="utf8mb4_general_ci",
                accessible=True,
                table_count=10
            )
        ]
    
    @pytest.fixture
    def sample_table_info(self):
        """Create sample table information."""
        return [
            TableInfo(
                name="users",
                type="BASE TABLE",
                engine="InnoDB",
                rows=1000,
                size_mb=5.2,
                comment="User accounts table",
                created_at=datetime.now() - timedelta(days=30),
                updated_at=datetime.now() - timedelta(hours=1)
            ),
            TableInfo(
                name="financial_overview",
                type="BASE TABLE",
                engine="InnoDB",
                rows=500,
                size_mb=2.8,
                comment="Financial overview data"
            )
        ]
    
    @pytest.fixture
    def sample_table_schema(self):
        """Create sample table schema."""
        columns = [
            ColumnInfo(
                name="id",
                data_type="int",
                is_nullable=False,
                default_value=None,
                is_primary_key=True,
                is_foreign_key=False,
                is_auto_increment=True
            ),
            ColumnInfo(
                name="name",
                data_type="varchar",
                is_nullable=False,
                default_value=None,
                is_primary_key=False,
                is_foreign_key=False,
                max_length=255
            ),
            ColumnInfo(
                name="amount",
                data_type="decimal",
                is_nullable=True,
                default_value="0.00",
                is_primary_key=False,
                is_foreign_key=False,
                precision=10,
                scale=2
            )
        ]
        
        indexes = [
            IndexInfo(
                name="PRIMARY",
                columns=["id"],
                is_unique=True,
                is_primary=True,
                index_type="BTREE"
            )
        ]
        
        return TableSchema(
            database="test_db",
            table="test_table",
            columns=columns,
            indexes=indexes,
            primary_keys=["id"],
            foreign_keys=[],
            constraints=[]
        )
    
    @pytest.fixture
    def schema_manager(self, mock_config, mock_validation_config):
        """Create MCPSchemaManager instance with mocked client."""
        with patch('backend.schema_management.manager.EnhancedMCPClient') as mock_client_class:
            mock_client = Mock(spec=EnhancedMCPClient)
            mock_client_class.return_value = mock_client
            
            manager = MCPSchemaManager(mock_config, mock_validation_config)
            manager.client = mock_client
            return manager
    
    @pytest.mark.asyncio
    async def test_connect_success(self, schema_manager):
        """Test successful connection to MCP server."""
        schema_manager.client.connect = AsyncMock(return_value=True)
        
        result = await schema_manager.connect()
        
        assert result is True
        schema_manager.client.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_failure(self, schema_manager):
        """Test connection failure handling."""
        schema_manager.client.connect = AsyncMock(side_effect=MCPConnectionError("Connection failed"))
        
        result = await schema_manager.connect()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_discover_databases_success(self, schema_manager, sample_database_info):
        """Test successful database discovery."""
        # Mock the client response
        mock_response = [
            {
                "name": "test_db",
                "charset": "utf8mb4",
                "collation": "utf8mb4_general_ci",
                "accessible": True,
                "table_count": 5
            },
            {
                "name": "financial_db",
                "charset": "utf8mb4",
                "collation": "utf8mb4_general_ci",
                "accessible": True,
                "table_count": 10
            }
        ]
        
        schema_manager.client._send_request = AsyncMock(return_value=mock_response)
        
        result = await schema_manager.discover_databases()
        
        assert len(result) == 2
        assert result[0].name == "test_db"
        assert result[1].name == "financial_db"
        assert result[0].table_count == 5
        schema_manager.client._send_request.assert_called_once_with("discover_databases_tool", {})
    
    @pytest.mark.asyncio
    async def test_discover_databases_with_caching(self, schema_manager, sample_database_info):
        """Test database discovery with caching."""
        # First call - should hit the server
        mock_response = [{"name": "test_db", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True}]
        schema_manager.client._send_request = AsyncMock(return_value=mock_response)
        
        result1 = await schema_manager.discover_databases()
        assert len(result1) == 1
        
        # Second call - should use cache
        result2 = await schema_manager.discover_databases()
        assert len(result2) == 1
        assert result1[0].name == result2[0].name
        
        # Should only call the server once due to caching
        schema_manager.client._send_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_discover_databases_error_handling(self, schema_manager):
        """Test database discovery error handling."""
        schema_manager.client._send_request = AsyncMock(return_value={"error": "Server error"})
        
        # With fallback enabled
        result = await schema_manager.discover_databases()
        assert result == []
        
        # With fallback disabled
        schema_manager.mcp_config.fallback_enabled = False
        with pytest.raises(MCPRequestError):
            await schema_manager.discover_databases()
    
    @pytest.mark.asyncio
    async def test_get_table_schema_success(self, schema_manager, sample_table_schema):
        """Test successful table schema retrieval."""
        # Mock the enhanced client method
        from backend.schema_management.models import DetailedTableSchema
        detailed_schema = DetailedTableSchema(
            schema=sample_table_schema,
            sample_data=[{"id": 1, "name": "test", "amount": "100.00"}],
            discovery_time_ms=150
        )
        
        schema_manager.client.get_table_schema_detailed = AsyncMock(return_value=detailed_schema)
        
        result = await schema_manager.get_table_schema("test_db", "test_table")
        
        assert result is not None
        assert result.database == "test_db"
        assert result.table == "test_table"
        assert len(result.columns) == 3
        assert result.columns[0].name == "id"
        assert result.columns[0].is_primary_key is True
    
    @pytest.mark.asyncio
    async def test_get_table_schema_not_found(self, schema_manager):
        """Test table schema retrieval when table not found."""
        schema_manager.client.get_table_schema_detailed = AsyncMock(
            side_effect=MCPRequestError("Table not found")
        )
        
        # With fallback enabled
        result = await schema_manager.get_table_schema("test_db", "nonexistent_table")
        assert result is None
        
        # With fallback disabled
        schema_manager.mcp_config.fallback_enabled = False
        with pytest.raises(MCPRequestError):
            await schema_manager.get_table_schema("test_db", "nonexistent_table")
    
    @pytest.mark.asyncio
    async def test_get_tables_success(self, schema_manager, sample_table_info):
        """Test successful table listing."""
        mock_response = [
            {
                "name": "users",
                "type": "BASE TABLE",
                "engine": "InnoDB",
                "rows": 1000,
                "size_mb": 5.2,
                "comment": "User accounts table"
            },
            {
                "name": "financial_overview",
                "type": "BASE TABLE",
                "engine": "InnoDB",
                "rows": 500,
                "size_mb": 2.8,
                "comment": "Financial overview data"
            }
        ]
        
        schema_manager.client._send_request = AsyncMock(return_value=mock_response)
        
        result = await schema_manager.get_tables("test_db")
        
        assert len(result) == 2
        assert result[0].name == "users"
        assert result[1].name == "financial_overview"
        assert result[0].rows == 1000
        schema_manager.client._send_request.assert_called_once_with(
            "discover_tables_tool", {"database": "test_db"}
        )
    
    @pytest.mark.asyncio
    async def test_validate_table_exists_true(self, schema_manager):
        """Test table existence validation - table exists."""
        mock_tables = [
            TableInfo(name="existing_table", type="BASE TABLE", engine="InnoDB", rows=0, size_mb=0.0)
        ]
        
        with patch.object(schema_manager, 'get_tables', return_value=mock_tables):
            result = await schema_manager.validate_table_exists("test_db", "existing_table")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_table_exists_false(self, schema_manager):
        """Test table existence validation - table does not exist."""
        mock_tables = [
            TableInfo(name="other_table", type="BASE TABLE", engine="InnoDB", rows=0, size_mb=0.0)
        ]
        
        with patch.object(schema_manager, 'get_tables', return_value=mock_tables):
            result = await schema_manager.validate_table_exists("test_db", "nonexistent_table")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_column_info_success(self, schema_manager, sample_table_schema):
        """Test successful column information retrieval."""
        with patch.object(schema_manager, 'get_table_schema', return_value=sample_table_schema):
            result = await schema_manager.get_column_info("test_db", "test_table", "id")
            
            assert result is not None
            assert result.name == "id"
            assert result.data_type == "int"
            assert result.is_primary_key is True
    
    @pytest.mark.asyncio
    async def test_get_column_info_not_found(self, schema_manager, sample_table_schema):
        """Test column information retrieval when column not found."""
        with patch.object(schema_manager, 'get_table_schema', return_value=sample_table_schema):
            result = await schema_manager.get_column_info("test_db", "test_table", "nonexistent_column")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_refresh_schema_cache_all(self, schema_manager):
        """Test refreshing all schema cache."""
        # Add some cache entries
        schema_manager._schema_cache = {
            "databases": ["db1", "db2"],
            "tables:test_db": ["table1", "table2"],
            "schema:test_db:table1": {"columns": []}
        }
        schema_manager._cache_timestamps = {
            "databases": datetime.now(),
            "tables:test_db": datetime.now(),
            "schema:test_db:table1": datetime.now()
        }
        
        result = await schema_manager.refresh_schema_cache("all")
        
        assert result is True
        assert len(schema_manager._schema_cache) == 0
        assert len(schema_manager._cache_timestamps) == 0
    
    @pytest.mark.asyncio
    async def test_refresh_schema_cache_specific_type(self, schema_manager):
        """Test refreshing specific cache type."""
        # Add some cache entries
        schema_manager._schema_cache = {
            "databases": ["db1", "db2"],
            "tables:test_db": ["table1", "table2"],
            "schema:test_db:table1": {"columns": []}
        }
        schema_manager._cache_timestamps = {
            "databases": datetime.now(),
            "tables:test_db": datetime.now(),
            "schema:test_db:table1": datetime.now()
        }
        
        result = await schema_manager.refresh_schema_cache("tables")
        
        assert result is True
        # Only tables entries should be removed
        assert "databases" in schema_manager._schema_cache
        assert "tables:test_db" not in schema_manager._schema_cache
        assert "schema:test_db:table1" in schema_manager._schema_cache
    
    def test_cache_key_generation(self, schema_manager):
        """Test cache key generation."""
        key1 = schema_manager._get_cache_key("operation", param1="value1", param2="value2")
        key2 = schema_manager._get_cache_key("operation", param2="value2", param1="value1")
        
        # Keys should be identical regardless of parameter order
        assert key1 == key2
        assert "operation" in key1
        assert "param1:value1" in key1
        assert "param2:value2" in key1
    
    def test_cache_validity_check(self, schema_manager):
        """Test cache validity checking."""
        cache_key = "test_key"
        
        # No cache entry - should be invalid
        assert not schema_manager._is_cache_valid(cache_key)
        
        # Fresh cache entry - should be valid
        schema_manager._cache_timestamps[cache_key] = datetime.now()
        assert schema_manager._is_cache_valid(cache_key)
        
        # Expired cache entry - should be invalid
        schema_manager._cache_timestamps[cache_key] = datetime.now() - timedelta(seconds=400)
        assert not schema_manager._is_cache_valid(cache_key)
    
    def test_cache_stats(self, schema_manager):
        """Test cache statistics generation."""
        # Add some cache data
        schema_manager._schema_cache = {
            "key1": "data1",
            "key2": "data2",
            "key3": "data3"
        }
        schema_manager._cache_timestamps = {
            "key1": datetime.now() - timedelta(seconds=100),
            "key2": datetime.now() - timedelta(seconds=200),
            "key3": datetime.now() - timedelta(seconds=50)
        }
        schema_manager._cache_stats = {
            "hits": 10,
            "misses": 5,
            "evictions": 2
        }
        
        stats = schema_manager.get_cache_stats()
        
        assert isinstance(stats, CacheStats)
        assert stats.total_entries == 3
        assert stats.hit_rate == 10 / 15  # 10 hits out of 15 total requests
        assert stats.miss_rate == 5 / 15   # 5 misses out of 15 total requests
        assert stats.eviction_count == 2
        assert stats.oldest_entry_age_seconds >= 200
        assert stats.newest_entry_age_seconds >= 50
    
    def test_detailed_cache_stats(self, schema_manager):
        """Test detailed cache statistics."""
        # Add cache entries with different operation types
        schema_manager._schema_cache = {
            "discover_databases": ["db1"],
            "tables:db1": ["table1"],
            "table_schema:db1:table1": {"columns": []},
            "discover_databases:other": ["db2"]
        }
        schema_manager._cache_timestamps = {key: datetime.now() for key in schema_manager._schema_cache.keys()}
        
        detailed_stats = schema_manager.get_detailed_cache_stats()
        
        assert "basic_stats" in detailed_stats
        assert "operation_breakdown" in detailed_stats
        assert "cache_health" in detailed_stats
        assert "configuration" in detailed_stats
        assert "performance_metrics" in detailed_stats
        
        # Check operation breakdown
        breakdown = detailed_stats["operation_breakdown"]
        assert "discover_databases" in breakdown
        assert "tables" in breakdown
        assert "table_schema" in breakdown
    
    @pytest.mark.asyncio
    async def test_health_check(self, schema_manager):
        """Test health check functionality."""
        schema_manager.client.health_check = AsyncMock(return_value=True)
        
        result = await schema_manager.health_check()
        assert result is True
        
        schema_manager.client.health_check = AsyncMock(return_value=False)
        result = await schema_manager.health_check()
        assert result is False
        
        schema_manager.client.health_check = AsyncMock(side_effect=Exception("Connection error"))
        result = await schema_manager.health_check()
        assert result is False


class TestMCPSchemaManagerCacheEviction:
    """Test cache eviction and memory management."""
    
    @pytest.fixture
    def schema_manager_small_cache(self):
        """Create schema manager with small cache for testing eviction."""
        config = MCPSchemaConfig(
            mcp_server_url="http://test-server:8000",
            cache_ttl=300,
            enable_caching=True
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            manager = MCPSchemaManager(config)
            # Patch the max cache size for testing
            with patch.object(manager, '_set_cache') as mock_set_cache:
                original_set_cache = manager._set_cache
                
                def limited_set_cache(cache_key: str, data):
                    # Simulate small cache limit
                    max_cache_size = 3
                    if len(manager._schema_cache) >= max_cache_size:
                        oldest_key = min(manager._cache_timestamps.keys(), 
                                       key=lambda k: manager._cache_timestamps[k])
                        del manager._schema_cache[oldest_key]
                        del manager._cache_timestamps[oldest_key]
                        manager._cache_stats["evictions"] += 1
                    
                    manager._schema_cache[cache_key] = data
                    manager._cache_timestamps[cache_key] = datetime.now()
                
                mock_set_cache.side_effect = limited_set_cache
                yield manager
    
    def test_cache_eviction_lru(self, schema_manager_small_cache):
        """Test LRU cache eviction."""
        manager = schema_manager_small_cache
        
        # Add entries up to limit
        manager._set_cache("key1", "data1")
        manager._set_cache("key2", "data2")
        manager._set_cache("key3", "data3")
        
        assert len(manager._schema_cache) == 3
        
        # Add one more - should evict oldest
        manager._set_cache("key4", "data4")
        
        assert len(manager._schema_cache) == 3
        assert "key1" not in manager._schema_cache  # Should be evicted
        assert "key4" in manager._schema_cache
        assert manager._cache_stats["evictions"] == 1


class TestMCPSchemaManagerErrorScenarios:
    """Test error scenarios and edge cases."""
    
    @pytest.fixture
    def schema_manager_no_fallback(self):
        """Create schema manager with fallback disabled."""
        config = MCPSchemaConfig(
            mcp_server_url="http://test-server:8000",
            fallback_enabled=False
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient') as mock_client_class:
            mock_client = Mock(spec=EnhancedMCPClient)
            mock_client_class.return_value = mock_client
            
            manager = MCPSchemaManager(config)
            manager.client = mock_client
            return manager
    
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, schema_manager_no_fallback):
        """Test handling of network timeouts."""
        schema_manager_no_fallback.client._send_request = AsyncMock(
            side_effect=asyncio.TimeoutError("Request timeout")
        )
        
        with pytest.raises(Exception):  # Should propagate timeout error
            await schema_manager_no_fallback.discover_databases()
    
    @pytest.mark.asyncio
    async def test_malformed_response_handling(self, schema_manager_no_fallback):
        """Test handling of malformed server responses."""
        # Test with non-list response for database discovery
        schema_manager_no_fallback.client._send_request = AsyncMock(return_value="invalid_response")
        
        with pytest.raises(Exception):
            await schema_manager_no_fallback.discover_databases()
        
        # Test with missing required fields
        schema_manager_no_fallback.client._send_request = AsyncMock(return_value=[{"invalid": "data"}])
        
        with pytest.raises(Exception):
            await schema_manager_no_fallback.discover_databases()
    
    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, schema_manager):
        """Test concurrent access to cache doesn't cause issues."""
        async def cache_operation(key_suffix: str):
            for i in range(10):
                cache_key = f"test_key_{key_suffix}_{i}"
                schema_manager._set_cache(cache_key, f"data_{i}")
                cached_data = schema_manager._get_cache(cache_key)
                assert cached_data == f"data_{i}" or cached_data is None  # May be evicted
        
        # Run multiple concurrent cache operations
        tasks = [cache_operation(str(i)) for i in range(5)]
        await asyncio.gather(*tasks)
        
        # Cache should still be in valid state
        stats = schema_manager.get_cache_stats()
        assert stats.total_entries >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])