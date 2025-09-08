"""
Comprehensive tests for MCP Client implementations.

This module tests the MCP client functionality including connection management,
request handling, error recovery, and schema-specific operations.
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json

from backend.schema_management.client import (
    BackendMCPClient, EnhancedMCPClient, MCPConnectionError, MCPRequestError
)
from backend.schema_management.config import MCPSchemaConfig
from backend.schema_management.models import (
    SchemaDiscoveryResult, DetailedTableSchema, QueryValidationResult,
    ConstraintInfo, CompatibilityResult, DatabaseInfo, TableSchema,
    ColumnInfo, IndexInfo, ForeignKeyInfo
)


class TestBackendMCPClient:
    """Test cases for BackendMCPClient core functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock MCP configuration."""
        return MCPSchemaConfig(
            mcp_server_url="http://test-server:8000",
            connection_timeout=5,
            request_timeout=10,
            max_retries=2,
            retry_delay=0.1
        )
    
    @pytest.fixture
    def mcp_client(self, mock_config):
        """Create BackendMCPClient instance."""
        return BackendMCPClient(mock_config)
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, mock_config):
        """Test client initialization with configuration."""
        client = BackendMCPClient(mock_config)
        
        assert client.config == mock_config
        assert client.session is None
        assert client.is_connected is False
    
    @pytest.mark.asyncio
    async def test_connect_success(self, mcp_client):
        """Test successful connection to MCP server."""
        mock_response = {"status": "healthy", "uptime": 3600}
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Mock successful response
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)
            
            mock_session.post.return_value.__aenter__.return_value = mock_response_obj
            
            result = await mcp_client.connect()
            
            assert result is True
            assert mcp_client.is_connected is True
            assert mcp_client.session is not None
    
    @pytest.mark.asyncio
    async def test_connect_failure_max_retries(self, mcp_client):
        """Test connection failure after max retries."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Mock connection error
            mock_session.post.side_effect = aiohttp.ClientError("Connection refused")
            
            with pytest.raises(MCPConnectionError):
                await mcp_client.connect()
            
            assert mcp_client.is_connected is False
    
    @pytest.mark.asyncio
    async def test_disconnect(self, mcp_client):
        """Test disconnection from MCP server."""
        # Set up connected state
        mock_session = AsyncMock()
        mcp_client.session = mock_session
        mcp_client.is_connected = True
        
        await mcp_client.disconnect()
        
        mock_session.close.assert_called_once()
        assert mcp_client.session is None
        assert mcp_client.is_connected is False
    
    @pytest.mark.asyncio
    async def test_send_request_success(self, mcp_client):
        """Test successful request sending."""
        mock_response_data = {"result": "success", "data": []}
        
        # Set up session
        mock_session = AsyncMock()
        mcp_client.session = mock_session
        
        # Mock successful response
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 200
        mock_response_obj.json = AsyncMock(return_value=mock_response_data)
        
        mock_session.post.return_value.__aenter__.return_value = mock_response_obj
        
        result = await mcp_client._send_request("test_method", {"param": "value"})
        
        assert result == mock_response_data
        mock_session.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_request_http_error(self, mcp_client):
        """Test request with HTTP error response."""
        # Set up session
        mock_session = AsyncMock()
        mcp_client.session = mock_session
        
        # Mock error response
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 500
        mock_response_obj.text = AsyncMock(return_value="Internal Server Error")
        
        mock_session.post.return_value.__aenter__.return_value = mock_response_obj
        
        result = await mcp_client._send_request("test_method", {})
        
        assert "error" in result
        assert "HTTP 500" in result["error"]
    
    @pytest.mark.asyncio
    async def test_send_request_timeout_retry(self, mcp_client):
        """Test request timeout with retry logic."""
        # Set up session
        mock_session = AsyncMock()
        mcp_client.session = mock_session
        
        # Mock timeout on first call, success on second
        mock_session.post.side_effect = [
            asyncio.TimeoutError("Request timeout"),
            AsyncMock()
        ]
        
        # Mock successful response for retry
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 200
        mock_response_obj.json = AsyncMock(return_value={"success": True})
        mock_session.post.return_value.__aenter__.return_value = mock_response_obj
        
        with pytest.raises(MCPRequestError):
            await mcp_client._send_request("test_method", {})
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, mcp_client):
        """Test successful health check."""
        mock_response = {"status": "healthy"}
        
        with patch.object(mcp_client, '_send_request', return_value=mock_response):
            result = await mcp_client.health_check()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, mcp_client):
        """Test health check failure."""
        with patch.object(mcp_client, '_send_request', side_effect=Exception("Connection error")):
            result = await mcp_client.health_check()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_server_stats_success(self, mcp_client):
        """Test successful server stats retrieval."""
        mock_stats = {
            "uptime": 3600,
            "requests_processed": 1000,
            "active_connections": 5
        }
        
        with patch.object(mcp_client, '_send_request', return_value=mock_stats):
            result = await mcp_client.get_server_stats()
            assert result == mock_stats
    
    @pytest.mark.asyncio
    async def test_get_server_stats_failure(self, mcp_client):
        """Test server stats retrieval failure."""
        with patch.object(mcp_client, '_send_request', side_effect=Exception("Server error")):
            result = await mcp_client.get_server_stats()
            assert result is None


class TestEnhancedMCPClient:
    """Test cases for EnhancedMCPClient schema-specific functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock MCP configuration."""
        return MCPSchemaConfig(
            mcp_server_url="http://test-server:8000",
            connection_timeout=5,
            request_timeout=10,
            max_retries=2,
            retry_delay=0.1
        )
    
    @pytest.fixture
    def enhanced_client(self, mock_config):
        """Create EnhancedMCPClient instance."""
        return EnhancedMCPClient(mock_config)
    
    @pytest.fixture
    def sample_database_response(self):
        """Sample database discovery response."""
        return [
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
    
    @pytest.fixture
    def sample_table_schema_response(self):
        """Sample table schema response."""
        return {
            "columns": [
                {
                    "name": "id",
                    "data_type": "int",
                    "is_nullable": False,
                    "default_value": None,
                    "is_primary_key": True,
                    "is_foreign_key": False,
                    "is_auto_increment": True
                },
                {
                    "name": "name",
                    "data_type": "varchar",
                    "is_nullable": False,
                    "default_value": None,
                    "is_primary_key": False,
                    "is_foreign_key": False,
                    "max_length": 255
                }
            ],
            "indexes": [
                {
                    "name": "PRIMARY",
                    "columns": ["id"],
                    "is_unique": True,
                    "is_primary": True,
                    "index_type": "BTREE"
                }
            ],
            "primary_keys": ["id"],
            "foreign_keys": [],
            "statistics": {
                "row_count": 1000,
                "avg_row_length": 256
            }
        }
    
    @pytest.mark.asyncio
    async def test_discover_schema_success(self, enhanced_client, sample_database_response):
        """Test successful schema discovery."""
        with patch.object(enhanced_client, '_send_request', return_value=sample_database_response):
            result = await enhanced_client.discover_schema("test_db")
            
            assert isinstance(result, SchemaDiscoveryResult)
            assert len(result.databases) == 1  # Filtered for test_db
            assert result.databases[0].name == "test_db"
            assert result.discovery_time_ms > 0
            assert result.error is None
    
    @pytest.mark.asyncio
    async def test_discover_schema_all_databases(self, enhanced_client, sample_database_response):
        """Test discovery of all databases."""
        with patch.object(enhanced_client, '_send_request', return_value=sample_database_response):
            result = await enhanced_client.discover_schema("")
            
            assert isinstance(result, SchemaDiscoveryResult)
            assert len(result.databases) == 2  # All databases
            assert result.databases[0].name == "test_db"
            assert result.databases[1].name == "financial_db"
    
    @pytest.mark.asyncio
    async def test_discover_schema_error(self, enhanced_client):
        """Test schema discovery with error."""
        with patch.object(enhanced_client, '_send_request', return_value={"error": "Database not found"}):
            result = await enhanced_client.discover_schema("nonexistent_db")
            
            assert isinstance(result, SchemaDiscoveryResult)
            assert len(result.databases) == 0
            assert result.error is not None
            assert "Database not found" in result.error
    
    @pytest.mark.asyncio
    async def test_discover_all_databases(self, enhanced_client, sample_database_response):
        """Test discover_all_databases method."""
        with patch.object(enhanced_client, 'discover_schema') as mock_discover:
            mock_result = SchemaDiscoveryResult(
                databases=[DatabaseInfo("test_db", "utf8mb4", "utf8mb4_general_ci", True)],
                discovery_time_ms=100
            )
            mock_discover.return_value = mock_result
            
            result = await enhanced_client.discover_all_databases()
            
            assert result == mock_result
            mock_discover.assert_called_once_with("")
    
    @pytest.mark.asyncio
    async def test_get_table_schema_detailed_success(self, enhanced_client, sample_table_schema_response):
        """Test successful detailed table schema retrieval."""
        # Mock schema response
        with patch.object(enhanced_client, '_send_request', return_value=sample_table_schema_response):
            # Mock sample data response
            sample_data_response = {
                "data": [
                    {"id": 1, "name": "Test Item 1"},
                    {"id": 2, "name": "Test Item 2"}
                ]
            }
            
            with patch.object(enhanced_client, '_send_request') as mock_send:
                mock_send.side_effect = [sample_table_schema_response, sample_data_response]
                
                result = await enhanced_client.get_table_schema_detailed("test_db", "test_table")
                
                assert isinstance(result, DetailedTableSchema)
                assert result.schema.database == "test_db"
                assert result.schema.table == "test_table"
                assert len(result.schema.columns) == 2
                assert result.schema.columns[0].name == "id"
                assert result.schema.columns[0].is_primary_key is True
                assert result.sample_data is not None
                assert len(result.sample_data) == 2
                assert result.discovery_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_get_table_schema_detailed_no_sample_data(self, enhanced_client, sample_table_schema_response):
        """Test table schema retrieval when sample data fails."""
        with patch.object(enhanced_client, '_send_request') as mock_send:
            # First call returns schema, second call fails for sample data
            mock_send.side_effect = [
                sample_table_schema_response,
                Exception("Sample data not available")
            ]
            
            result = await enhanced_client.get_table_schema_detailed("test_db", "test_table")
            
            assert isinstance(result, DetailedTableSchema)
            assert result.schema.database == "test_db"
            assert result.sample_data is None  # Should handle gracefully
    
    @pytest.mark.asyncio
    async def test_get_table_schema_detailed_error(self, enhanced_client):
        """Test table schema retrieval with error."""
        with patch.object(enhanced_client, '_send_request', return_value={"error": "Table not found"}):
            with pytest.raises(MCPRequestError):
                await enhanced_client.get_table_schema_detailed("test_db", "nonexistent_table")
    
    @pytest.mark.asyncio
    async def test_validate_query_against_schema_success(self, enhanced_client):
        """Test successful query validation."""
        mock_validation_response = {
            "is_valid": True,
            "errors": [],
            "warnings": ["Query may be slow on large datasets"],
            "affected_tables": ["test_table"],
            "estimated_rows": 1000,
            "execution_plan": {"type": "SELECT", "cost": 10.5}
        }
        
        with patch.object(enhanced_client, '_send_request', return_value=mock_validation_response):
            result = await enhanced_client.validate_query_against_schema("SELECT * FROM test_table")
            
            assert isinstance(result, QueryValidationResult)
            assert result.is_valid is True
            assert len(result.errors) == 0
            assert len(result.warnings) == 1
            assert "test_table" in result.affected_tables
            assert result.estimated_rows == 1000
    
    @pytest.mark.asyncio
    async def test_validate_query_against_schema_invalid(self, enhanced_client):
        """Test query validation with invalid query."""
        mock_validation_response = {
            "is_valid": False,
            "errors": ["Syntax error near 'SELCT'", "Unknown table 'nonexistent_table'"],
            "warnings": [],
            "affected_tables": []
        }
        
        with patch.object(enhanced_client, '_send_request', return_value=mock_validation_response):
            result = await enhanced_client.validate_query_against_schema("SELCT * FROM nonexistent_table")
            
            assert isinstance(result, QueryValidationResult)
            assert result.is_valid is False
            assert len(result.errors) == 2
            assert "Syntax error" in result.errors[0]
            assert "Unknown table" in result.errors[1]
    
    @pytest.mark.asyncio
    async def test_validate_query_against_schema_error(self, enhanced_client):
        """Test query validation with server error."""
        with patch.object(enhanced_client, '_send_request', side_effect=Exception("Server error")):
            result = await enhanced_client.validate_query_against_schema("SELECT * FROM test_table")
            
            assert isinstance(result, QueryValidationResult)
            assert result.is_valid is False
            assert len(result.errors) == 1
            assert "Validation error" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_get_constraint_info_placeholder(self, enhanced_client):
        """Test constraint info retrieval (placeholder implementation)."""
        result = await enhanced_client.get_constraint_info("test_db", "test_table")
        
        assert isinstance(result, ConstraintInfo)
        # This is a placeholder implementation, so it returns empty constraint info
        assert result.name == ""
        assert result.constraint_type == ""
    
    @pytest.mark.asyncio
    async def test_check_schema_compatibility_placeholder(self, enhanced_client):
        """Test schema compatibility check (placeholder implementation)."""
        expected_schema = {
            "tables": ["test_table"],
            "columns": {"test_table": ["id", "name"]}
        }
        
        result = await enhanced_client.check_schema_compatibility(expected_schema)
        
        assert isinstance(result, CompatibilityResult)
        # This is a placeholder implementation, so it returns compatible
        assert result.is_compatible is True
        assert len(result.missing_tables) == 0


class TestMCPClientErrorHandling:
    """Test error handling and edge cases in MCP clients."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock MCP configuration."""
        return MCPSchemaConfig(
            mcp_server_url="http://test-server:8000",
            connection_timeout=1,
            request_timeout=2,
            max_retries=1,
            retry_delay=0.1
        )
    
    @pytest.mark.asyncio
    async def test_connection_refused(self, mock_config):
        """Test handling of connection refused error."""
        client = BackendMCPClient(mock_config)
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            mock_session.post.side_effect = aiohttp.ClientConnectorError(
                connection_key=None, os_error=None
            )
            
            with pytest.raises(MCPConnectionError):
                await client.connect()
    
    @pytest.mark.asyncio
    async def test_invalid_json_response(self, mock_config):
        """Test handling of invalid JSON response."""
        client = BackendMCPClient(mock_config)
        
        # Set up session
        mock_session = AsyncMock()
        client.session = mock_session
        
        # Mock response with invalid JSON
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 200
        mock_response_obj.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        mock_session.post.return_value.__aenter__.return_value = mock_response_obj
        
        with pytest.raises(MCPRequestError):
            await client._send_request("test_method", {})
    
    @pytest.mark.asyncio
    async def test_network_interruption_during_request(self, mock_config):
        """Test handling of network interruption during request."""
        client = BackendMCPClient(mock_config)
        
        # Set up session
        mock_session = AsyncMock()
        client.session = mock_session
        
        # Mock network interruption
        mock_session.post.side_effect = aiohttp.ClientError("Network unreachable")
        
        with pytest.raises(MCPRequestError):
            await client._send_request("test_method", {})
    
    @pytest.mark.asyncio
    async def test_server_overload_503(self, mock_config):
        """Test handling of server overload (503 error)."""
        client = BackendMCPClient(mock_config)
        
        # Set up session
        mock_session = AsyncMock()
        client.session = mock_session
        
        # Mock 503 response
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 503
        mock_response_obj.text = AsyncMock(return_value="Service Unavailable")
        
        mock_session.post.return_value.__aenter__.return_value = mock_response_obj
        
        result = await client._send_request("test_method", {})
        
        assert "error" in result
        assert "HTTP 503" in result["error"]


class TestMCPClientPerformance:
    """Test performance-related aspects of MCP clients."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock MCP configuration."""
        return MCPSchemaConfig(
            mcp_server_url="http://test-server:8000",
            connection_timeout=5,
            request_timeout=10,
            max_retries=3,
            retry_delay=0.01  # Fast retry for testing
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, mock_config):
        """Test handling of concurrent requests."""
        client = BackendMCPClient(mock_config)
        
        # Set up session
        mock_session = AsyncMock()
        client.session = mock_session
        
        # Mock successful responses
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 200
        mock_response_obj.json = AsyncMock(return_value={"success": True})
        
        mock_session.post.return_value.__aenter__.return_value = mock_response_obj
        
        # Send multiple concurrent requests
        tasks = [
            client._send_request(f"method_{i}", {"param": i})
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert all(result["success"] for result in results)
        assert mock_session.post.call_count == 10
    
    @pytest.mark.asyncio
    async def test_request_timeout_measurement(self, mock_config):
        """Test that request timeouts are properly measured."""
        enhanced_client = EnhancedMCPClient(mock_config)
        
        # Mock a slow response
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate slow response
            return [{"name": "test_db", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True}]
        
        with patch.object(enhanced_client, '_send_request', side_effect=slow_response):
            start_time = datetime.now()
            result = await enhanced_client.discover_schema("test_db")
            end_time = datetime.now()
            
            # Check that discovery time is measured
            assert result.discovery_time_ms > 0
            
            # Check that actual time elapsed is reasonable
            actual_time_ms = (end_time - start_time).total_seconds() * 1000
            assert result.discovery_time_ms <= actual_time_ms + 50  # Allow some margin


if __name__ == "__main__":
    pytest.main([__file__, "-v"])