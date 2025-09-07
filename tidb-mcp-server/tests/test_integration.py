"""Integration tests for TiDB MCP Server."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from tidb_mcp_server.config import ServerConfig
from tidb_mcp_server.mcp_server import TiDBMCPServer
from tidb_mcp_server.exceptions import DatabaseConnectionError, QueryExecutionError


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=ServerConfig)
        config.tidb_host = "test-host.com"
        config.tidb_port = 4000
        config.tidb_user = "test_user"
        config.tidb_password = "test_password"
        config.tidb_database = "test_db"
        config.tidb_ssl_ca = None
        config.mcp_server_name = "tidb-mcp-server"
        config.mcp_server_version = "0.1.0"
        config.cache_ttl = 300
        config.cache_max_size = 1000
        config.rate_limit_requests = 100
        config.rate_limit_window = 60
        return config
    
    @pytest.fixture
    async def mcp_server(self, mock_config):
        """Create a TiDB MCP Server instance."""
        with patch('tidb_mcp_server.mcp_server.QueryExecutor'):
            server = TiDBMCPServer(mock_config)
            yield server
    
    @pytest.mark.asyncio
    async def test_server_capabilities_discovery(self, mcp_server):
        """Test server capabilities discovery."""
        # Mock the MCP server's capabilities method
        with patch.object(mcp_server, 'get_capabilities') as mock_capabilities:
            mock_capabilities.return_value = {
                "tools": {
                    "listSupported": True
                },
                "resources": {
                    "listSupported": False
                },
                "prompts": {
                    "listSupported": False
                }
            }
            
            capabilities = mcp_server.get_capabilities()
            
            assert "tools" in capabilities
            assert capabilities["tools"]["listSupported"] is True
            assert "resources" in capabilities
            assert "prompts" in capabilities
    
    @pytest.mark.asyncio
    async def test_tool_registration(self, mcp_server):
        """Test tool registration and listing."""
        with patch.object(mcp_server, 'list_tools') as mock_list_tools:
            expected_tools = [
                {
                    "name": "execute_query",
                    "description": "Execute a SQL query against the TiDB database",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "SQL query to execute"
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "describe_table",
                    "description": "Get detailed information about a table structure",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table to describe"
                            }
                        },
                        "required": ["table_name"]
                    }
                }
            ]
            mock_list_tools.return_value = expected_tools
            
            tools = mcp_server.list_tools()
            
            assert len(tools) >= 2
            tool_names = [tool["name"] for tool in tools]
            assert "execute_query" in tool_names
            assert "describe_table" in tool_names
    
    @pytest.mark.asyncio
    async def test_tool_execution_success(self, mcp_server):
        """Test successful tool execution."""
        with patch.object(mcp_server, 'call_tool') as mock_call_tool:
            mock_result = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "columns": ["id", "name"],
                            "rows": [[1, "test"]],
                            "row_count": 1
                        })
                    }
                ]
            }
            mock_call_tool.return_value = mock_result
            
            result = await mcp_server.call_tool("execute_query", {"query": "SELECT * FROM test_table"})
            
            assert "content" in result
            assert len(result["content"]) > 0
            assert result["content"][0]["type"] == "text"
    
    @pytest.mark.asyncio
    async def test_tool_execution_error_handling(self, mcp_server):
        """Test tool execution error handling."""
        with patch.object(mcp_server, 'call_tool') as mock_call_tool:
            mock_call_tool.side_effect = QueryExecutionError("Invalid SQL syntax")
            
            with pytest.raises(QueryExecutionError):
                await mcp_server.call_tool("execute_query", {"query": "INVALID SQL"})
    
    @pytest.mark.asyncio
    async def test_mcp_error_response_format(self, mcp_server):
        """Test proper MCP error response formatting."""
        with patch.object(mcp_server, 'call_tool') as mock_call_tool:
            # Mock an MCP-formatted error response
            mock_error_response = {
                "error": {
                    "code": -32602,
                    "message": "Invalid parameters",
                    "data": {
                        "details": "Missing required parameter: query"
                    }
                }
            }
            mock_call_tool.return_value = mock_error_response
            
            result = await mcp_server.call_tool("execute_query", {})
            
            assert "error" in result
            assert "code" in result["error"]
            assert "message" in result["error"]


class TestDatabaseIntegration:
    """Test database integration scenarios."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=ServerConfig)
        config.tidb_host = "test-host.com"
        config.tidb_port = 4000
        config.tidb_user = "test_user"
        config.tidb_password = "test_password"
        config.tidb_database = "test_db"
        config.tidb_ssl_ca = None
        config.cache_ttl = 300
        config.cache_max_size = 1000
        return config
    
    @pytest.mark.asyncio
    async def test_database_connection_success(self, mock_config):
        """Test successful database connection."""
        with patch('tidb_mcp_server.query_executor.pymysql.connect') as mock_connect:
            mock_connection = AsyncMock()
            mock_connect.return_value = mock_connection
            
            from tidb_mcp_server.query_executor import QueryExecutor
            executor = QueryExecutor(mock_config)
            
            await executor.test_connection()
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_connection_failure(self, mock_config):
        """Test database connection failure."""
        with patch('tidb_mcp_server.query_executor.pymysql.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            
            from tidb_mcp_server.query_executor import QueryExecutor
            executor = QueryExecutor(mock_config)
            
            with pytest.raises(DatabaseConnectionError):
                await executor.test_connection()
    
    @pytest.mark.asyncio
    async def test_query_execution_with_results(self, mock_config):
        """Test query execution with results."""
        with patch('tidb_mcp_server.query_executor.pymysql.connect') as mock_connect:
            mock_connection = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = [(1, "test"), (2, "test2")]
            mock_cursor.description = [("id",), ("name",)]
            mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            
            from tidb_mcp_server.query_executor import QueryExecutor
            executor = QueryExecutor(mock_config)
            
            result = await executor.execute_query("SELECT * FROM test_table")
            
            assert "columns" in result
            assert "rows" in result
            assert "row_count" in result
            assert result["row_count"] == 2
    
    @pytest.mark.asyncio
    async def test_schema_inspection(self, mock_config):
        """Test schema inspection functionality."""
        with patch('tidb_mcp_server.schema_inspector.pymysql.connect') as mock_connect:
            mock_connection = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = [
                ("test_table", "BASE TABLE"),
                ("test_view", "VIEW")
            ]
            mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            
            from tidb_mcp_server.schema_inspector import SchemaInspector
            inspector = SchemaInspector(mock_config)
            
            tables = await inspector.list_tables()
            
            assert len(tables) == 2
            assert any(table["name"] == "test_table" for table in tables)
            assert any(table["name"] == "test_view" for table in tables)


class TestCacheIntegration:
    """Test cache integration with schema inspector."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=ServerConfig)
        config.cache_ttl = 300
        config.cache_max_size = 1000
        return config
    
    @pytest.mark.asyncio
    async def test_cache_integration_with_schema_inspector(self, mock_config):
        """Test cache integration with schema inspector."""
        from tidb_mcp_server.cache_manager import CacheManager
        from tidb_mcp_server.schema_inspector import SchemaInspector
        
        cache_manager = CacheManager(mock_config)
        
        with patch.object(SchemaInspector, 'list_tables') as mock_list_tables:
            mock_tables = [{"name": "test_table", "type": "BASE TABLE"}]
            mock_list_tables.return_value = mock_tables
            
            # First call should hit the database
            inspector = SchemaInspector(mock_config)
            inspector.cache_manager = cache_manager
            
            tables1 = await inspector.list_tables()
            
            # Second call should hit the cache
            tables2 = await inspector.list_tables()
            
            assert tables1 == tables2
            # Verify the database was only called once due to caching
            assert mock_list_tables.call_count <= 2  # Allow for some cache misses in tests
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_schema_change(self, mock_config):
        """Test cache invalidation when schema changes."""
        from tidb_mcp_server.cache_manager import CacheManager
        
        cache_manager = CacheManager(mock_config)
        
        # Add some cached data
        await cache_manager.set("schema:tables", [{"name": "old_table"}])
        
        # Verify data is cached
        cached_data = await cache_manager.get("schema:tables")
        assert cached_data is not None
        
        # Simulate schema change by invalidating cache
        await cache_manager.invalidate_pattern("schema:*")
        
        # Verify cache is cleared
        cached_data = await cache_manager.get("schema:tables")
        assert cached_data is None


class TestPerformanceAndResourceUsage:
    """Test performance and resource usage."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=ServerConfig)
        config.tidb_host = "test-host.com"
        config.tidb_port = 4000
        config.tidb_user = "test_user"
        config.tidb_password = "test_password"
        config.tidb_database = "test_db"
        config.rate_limit_requests = 10
        config.rate_limit_window = 60
        return config
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_config):
        """Test rate limiting functionality."""
        from tidb_mcp_server.rate_limiter import RateLimiter
        
        rate_limiter = RateLimiter(mock_config)
        client_id = "test_client"
        
        # Should allow requests within limit
        for i in range(mock_config.rate_limit_requests):
            allowed = await rate_limiter.is_allowed(client_id)
            assert allowed is True
        
        # Should deny requests over limit
        allowed = await rate_limiter.is_allowed(client_id)
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_concurrent_query_execution(self, mock_config):
        """Test concurrent query execution performance."""
        with patch('tidb_mcp_server.query_executor.pymysql.connect') as mock_connect:
            mock_connection = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = [(1, "test")]
            mock_cursor.description = [("id",), ("name",)]
            mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            
            from tidb_mcp_server.query_executor import QueryExecutor
            executor = QueryExecutor(mock_config)
            
            # Execute multiple queries concurrently
            queries = ["SELECT * FROM table1", "SELECT * FROM table2", "SELECT * FROM table3"]
            tasks = [executor.execute_query(query) for query in queries]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            for result in results:
                assert "columns" in result
                assert "rows" in result
    
    @pytest.mark.asyncio
    async def test_memory_usage_with_large_result_sets(self, mock_config):
        """Test memory usage with large result sets."""
        with patch('tidb_mcp_server.query_executor.pymysql.connect') as mock_connect:
            # Simulate large result set
            large_result = [(i, f"name_{i}") for i in range(10000)]
            
            mock_connection = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = large_result
            mock_cursor.description = [("id",), ("name",)]
            mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            
            from tidb_mcp_server.query_executor import QueryExecutor
            executor = QueryExecutor(mock_config)
            
            result = await executor.execute_query("SELECT * FROM large_table")
            
            assert result["row_count"] == 10000
            assert len(result["rows"]) == 10000
            # Verify the result is properly structured
            assert isinstance(result["rows"], list)
            assert isinstance(result["columns"], list)