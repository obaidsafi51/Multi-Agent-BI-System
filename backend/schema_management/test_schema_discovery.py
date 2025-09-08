"""
Comprehensive tests for MCP schema discovery functionality.
"""

import asyncio
import sys
import os
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema_management.config import MCPSchemaConfig, SchemaValidationConfig
from schema_management.client import EnhancedMCPClient, MCPRequestError
from schema_management.manager import MCPSchemaManager
from schema_management.models import (
    DatabaseInfo, TableInfo, ColumnInfo, TableSchema, SchemaDiscoveryResult,
    DetailedTableSchema, serialize_schema_model, deserialize_database_info,
    deserialize_table_info, deserialize_column_info, deserialize_table_schema
)


class TestSchemaDiscovery:
    """Test suite for schema discovery functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = MCPSchemaConfig(
            mcp_server_url="http://test:8000",
            cache_ttl=300,
            enable_caching=True,
            fallback_enabled=True
        )
        self.manager = MCPSchemaManager(self.config)
    
    async def test_database_discovery(self):
        """Test database discovery through MCP server."""
        # Mock MCP response
        mock_response = [
            {
                "name": "test_db",
                "charset": "utf8mb4",
                "collation": "utf8mb4_general_ci",
                "accessible": True,
                "table_count": 5
            },
            {
                "name": "another_db",
                "charset": "utf8mb4",
                "collation": "utf8mb4_general_ci",
                "accessible": True,
                "table_count": 3
            }
        ]
        
        with patch.object(self.manager.client, '_send_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            databases = await self.manager.discover_databases()
            
            assert len(databases) == 2
            assert databases[0].name == "test_db"
            assert databases[0].table_count == 5
            assert databases[1].name == "another_db"
            assert databases[1].table_count == 3
            
            # Verify caching
            mock_request.assert_called_once()
            
            # Second call should use cache
            databases_cached = await self.manager.discover_databases()
            assert len(databases_cached) == 2
            mock_request.assert_called_once()  # Still only one call
    
    async def test_table_discovery(self):
        """Test table discovery and schema retrieval."""
        # Mock MCP response for table discovery
        mock_tables_response = [
            {
                "name": "users",
                "type": "BASE TABLE",
                "engine": "InnoDB",
                "rows": 1000,
                "size_mb": 2.5,
                "comment": "User accounts table",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z"
            },
            {
                "name": "orders",
                "type": "BASE TABLE",
                "engine": "InnoDB",
                "rows": 5000,
                "size_mb": 10.2,
                "comment": "Orders table"
            }
        ]
        
        with patch.object(self.manager.client, '_send_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_tables_response
            
            tables = await self.manager.get_tables("test_db")
            
            assert len(tables) == 2
            assert tables[0].name == "users"
            assert tables[0].rows == 1000
            assert tables[0].size_mb == 2.5
            assert tables[0].comment == "User accounts table"
            assert tables[0].created_at is not None
            assert tables[1].name == "orders"
            assert tables[1].rows == 5000
    
    async def test_table_schema_retrieval(self):
        """Test detailed table schema retrieval."""
        # Mock MCP response for table schema
        mock_schema_response = {
            "columns": [
                {
                    "name": "id",
                    "data_type": "bigint",
                    "is_nullable": False,
                    "default_value": None,
                    "is_primary_key": True,
                    "is_foreign_key": False,
                    "is_auto_increment": True,
                    "comment": "Primary key"
                },
                {
                    "name": "email",
                    "data_type": "varchar",
                    "is_nullable": False,
                    "default_value": None,
                    "is_primary_key": False,
                    "is_foreign_key": False,
                    "max_length": 255,
                    "comment": "User email address"
                }
            ],
            "indexes": [
                {
                    "name": "PRIMARY",
                    "columns": ["id"],
                    "is_unique": True,
                    "is_primary": True,
                    "index_type": "BTREE"
                },
                {
                    "name": "idx_email",
                    "columns": ["email"],
                    "is_unique": True,
                    "is_primary": False,
                    "index_type": "BTREE"
                }
            ],
            "primary_keys": ["id"],
            "foreign_keys": [],
            "constraints": []
        }
        
        with patch.object(self.manager.client, 'get_table_schema_detailed', new_callable=AsyncMock) as mock_detailed:
            mock_detailed.return_value = DetailedTableSchema(
                schema=TableSchema(
                    database="test_db",
                    table="users",
                    columns=[
                        ColumnInfo(
                            name="id",
                            data_type="bigint",
                            is_nullable=False,
                            default_value=None,
                            is_primary_key=True,
                            is_foreign_key=False,
                            is_auto_increment=True,
                            comment="Primary key"
                        ),
                        ColumnInfo(
                            name="email",
                            data_type="varchar",
                            is_nullable=False,
                            default_value=None,
                            is_primary_key=False,
                            is_foreign_key=False,
                            max_length=255,
                            comment="User email address"
                        )
                    ],
                    indexes=[],
                    primary_keys=["id"],
                    foreign_keys=[],
                    constraints=[]
                ),
                sample_data=[
                    {"id": 1, "email": "user1@example.com"},
                    {"id": 2, "email": "user2@example.com"}
                ],
                discovery_time_ms=50
            )
            
            schema = await self.manager.get_table_schema("test_db", "users")
            
            assert schema is not None
            assert schema.database == "test_db"
            assert schema.table == "users"
            assert len(schema.columns) == 2
            assert schema.columns[0].name == "id"
            assert schema.columns[0].is_primary_key is True
            assert schema.columns[1].name == "email"
            assert schema.columns[1].max_length == 255
    
    async def test_error_handling(self):
        """Test error handling for MCP communication failures."""
        # Test connection failure
        with patch.object(self.manager.client, '_send_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("Connection failed")
            
            # With fallback enabled, should return empty list
            databases = await self.manager.discover_databases()
            assert databases == []
            
            # Disable fallback and test exception propagation
            self.manager.mcp_config.fallback_enabled = False
            
            try:
                await self.manager.discover_databases()
                assert False, "Should have raised exception"
            except Exception as e:
                assert "Connection failed" in str(e)
    
    async def test_cache_management(self):
        """Test cache invalidation and refresh mechanisms."""
        # Set up initial cache
        test_data = [DatabaseInfo(name="test", charset="utf8mb4", collation="utf8mb4_general_ci", accessible=True)]
        cache_key = self.manager._get_cache_key("discover_databases")
        self.manager._set_cache(cache_key, test_data)
        
        # Test cache retrieval
        cached_data = self.manager._get_cache(cache_key)
        assert cached_data == test_data
        
        # Test cache refresh
        success = await self.manager.refresh_schema_cache("all")
        assert success is True
        
        # Verify cache is cleared
        cached_data = self.manager._get_cache(cache_key)
        assert cached_data is None
        
        # Test pattern-based invalidation
        self.manager._set_cache("tables:db1", ["table1"])
        self.manager._set_cache("tables:db2", ["table2"])
        self.manager._set_cache("schemas:db1:table1", {"schema": "data"})
        
        invalidated = await self.manager.invalidate_cache_by_pattern("tables:*")
        assert invalidated == 2
        
        # Verify only tables cache was cleared
        assert self.manager._get_cache("tables:db1") is None
        assert self.manager._get_cache("tables:db2") is None
        assert self.manager._get_cache("schemas:db1:table1") is not None
    
    async def test_cache_statistics(self):
        """Test cache statistics and monitoring."""
        # Generate some cache activity
        self.manager._cache_stats["hits"] = 10
        self.manager._cache_stats["misses"] = 5
        self.manager._cache_stats["evictions"] = 2
        
        # Add some cache entries
        self.manager._set_cache("test1", {"data": "value1"})
        self.manager._set_cache("test2", {"data": "value2"})
        
        stats = self.manager.get_cache_stats()
        
        assert stats.total_entries == 2
        expected_hit_rate = 10 / 15  # 10 hits out of 15 total requests
        expected_miss_rate = 5 / 15   # 5 misses out of 15 total requests
        assert abs(stats.hit_rate - expected_hit_rate) < 0.001
        assert abs(stats.miss_rate - expected_miss_rate) < 0.001
        assert stats.eviction_count == 2
        
        # Test detailed stats
        detailed_stats = self.manager.get_detailed_cache_stats()
        
        assert "basic_stats" in detailed_stats
        assert "operation_breakdown" in detailed_stats
        assert "cache_health" in detailed_stats
        assert "configuration" in detailed_stats
        assert "performance_metrics" in detailed_stats
        
        assert detailed_stats["performance_metrics"]["total_hits"] == 10
        assert detailed_stats["performance_metrics"]["total_misses"] == 5
    
    def test_serialization_deserialization(self):
        """Test serialization and deserialization methods."""
        # Test DatabaseInfo serialization
        db_info = DatabaseInfo(
            name="test_db",
            charset="utf8mb4",
            collation="utf8mb4_general_ci",
            accessible=True,
            table_count=5
        )
        
        serialized = serialize_schema_model(db_info)
        assert isinstance(serialized, str)
        
        # Test deserialization
        db_data = {
            "name": "test_db",
            "charset": "utf8mb4",
            "collation": "utf8mb4_general_ci",
            "accessible": True,
            "table_count": 5
        }
        
        deserialized_db = deserialize_database_info(db_data)
        assert deserialized_db.name == "test_db"
        assert deserialized_db.table_count == 5
        
        # Test TableInfo deserialization with datetime
        table_data = {
            "name": "users",
            "type": "BASE TABLE",
            "engine": "InnoDB",
            "rows": 1000,
            "size_mb": 2.5,
            "comment": "Users table",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z"
        }
        
        deserialized_table = deserialize_table_info(table_data)
        assert deserialized_table.name == "users"
        assert deserialized_table.rows == 1000
        assert deserialized_table.created_at is not None
        assert isinstance(deserialized_table.created_at, datetime)
        
        # Test ColumnInfo deserialization
        column_data = {
            "name": "id",
            "data_type": "bigint",
            "is_nullable": False,
            "default_value": None,
            "is_primary_key": True,
            "is_foreign_key": False,
            "is_auto_increment": True,
            "comment": "Primary key"
        }
        
        deserialized_column = deserialize_column_info(column_data)
        assert deserialized_column.name == "id"
        assert deserialized_column.is_primary_key is True
        assert deserialized_column.is_auto_increment is True
    
    async def test_table_validation(self):
        """Test table existence validation."""
        # Mock table discovery
        mock_tables = [
            TableInfo(name="users", type="BASE TABLE", engine="InnoDB", rows=100, size_mb=1.0),
            TableInfo(name="orders", type="BASE TABLE", engine="InnoDB", rows=200, size_mb=2.0)
        ]
        
        with patch.object(self.manager, 'get_tables', new_callable=AsyncMock) as mock_get_tables:
            mock_get_tables.return_value = mock_tables
            
            # Test existing table
            exists = await self.manager.validate_table_exists("test_db", "users")
            assert exists is True
            
            # Test non-existing table
            exists = await self.manager.validate_table_exists("test_db", "nonexistent")
            assert exists is False
    
    async def test_column_info_retrieval(self):
        """Test column information retrieval."""
        # Mock table schema
        mock_schema = TableSchema(
            database="test_db",
            table="users",
            columns=[
                ColumnInfo(name="id", data_type="bigint", is_nullable=False, 
                          default_value=None, is_primary_key=True, is_foreign_key=False),
                ColumnInfo(name="email", data_type="varchar", is_nullable=False,
                          default_value=None, is_primary_key=False, is_foreign_key=False, max_length=255)
            ],
            indexes=[],
            primary_keys=["id"],
            foreign_keys=[],
            constraints=[]
        )
        
        with patch.object(self.manager, 'get_table_schema', new_callable=AsyncMock) as mock_get_schema:
            mock_get_schema.return_value = mock_schema
            
            # Test existing column
            column_info = await self.manager.get_column_info("test_db", "users", "email")
            assert column_info is not None
            assert column_info.name == "email"
            assert column_info.data_type == "varchar"
            assert column_info.max_length == 255
            
            # Test non-existing column
            column_info = await self.manager.get_column_info("test_db", "users", "nonexistent")
            assert column_info is None


async def run_all_tests():
    """Run all schema discovery tests."""
    test_suite = TestSchemaDiscovery()
    
    print("Running schema discovery tests...")
    
    # Run each test method
    test_methods = [
        test_suite.test_database_discovery,
        test_suite.test_table_discovery,
        test_suite.test_table_schema_retrieval,
        test_suite.test_error_handling,
        test_suite.test_cache_management,
        test_suite.test_cache_statistics,
        test_suite.test_table_validation,
        test_suite.test_column_info_retrieval
    ]
    
    for test_method in test_methods:
        test_suite.setup_method()
        try:
            await test_method()
            print(f"✓ {test_method.__name__}")
        except Exception as e:
            print(f"✗ {test_method.__name__}: {e}")
            raise
    
    # Run synchronous tests
    try:
        test_suite.setup_method()
        test_suite.test_serialization_deserialization()
        print("✓ test_serialization_deserialization")
    except Exception as e:
        print(f"✗ test_serialization_deserialization: {e}")
        raise
    
    print("✓ All schema discovery tests passed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())