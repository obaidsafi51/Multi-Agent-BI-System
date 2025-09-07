"""Test client for validating TiDB MCP Server responses using MCP SDK."""

import asyncio
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Dict, Any, List

from tidb_mcp_server.config import ServerConfig
from tidb_mcp_server.mcp_server import TiDBMCPServer
from tidb_mcp_server.exceptions import QueryExecutionError, DatabaseConnectionError


class MCPTestClient:
    """Test client that simulates MCP protocol communication."""
    
    def __init__(self, server: TiDBMCPServer):
        self.server = server
        self.session_id = "test_session"
        self.request_id = 0
    
    def _next_request_id(self) -> int:
        """Generate next request ID."""
        self.request_id += 1
        return self.request_id
    
    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request to the server."""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
            "params": params or {}
        }
        
        # Simulate MCP protocol handling
        try:
            if method == "initialize":
                return await self._handle_initialize(params)
            elif method == "tools/list":
                return await self._handle_list_tools(params)
            elif method == "tools/call":
                return await self._handle_call_tool(params)
            elif method == "capabilities/get":
                return await self._handle_get_capabilities(params)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "error": {
                        "code": -32601,
                        "message": "Method not found"
                    }
                }
        except Exception as e:
            return {
                "jsonrpc": "2.0", 
                "id": request["id"],
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
            }
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": self.server.get_capabilities(),
                "serverInfo": {
                    "name": "tidb-mcp-server",
                    "version": "0.1.0"
                }
            }
        }
    
    async def _handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = await self.server.list_tools()
        return {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "result": {
                "tools": tools
            }
        }
    
    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        try:
            result = await self.server.call_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "result": result
            }
        except QueryExecutionError as e:
            return {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "error": {
                    "code": -32602,
                    "message": "Query execution error",
                    "data": str(e)
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
            }
    
    async def _handle_get_capabilities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle capabilities/get request."""
        return {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "result": self.server.get_capabilities()
        }


class TestMCPClientValidation:
    """Test MCP client validation scenarios."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock(spec=ServerConfig)
        config.tidb_host = "test-host.com"
        config.tidb_port = 4000
        config.tidb_user = "test_user"
        config.tidb_password = "test_password"
        config.tidb_database = "test_db"
        config.mcp_server_name = "tidb-mcp-server"
        config.mcp_server_version = "0.1.0"
        config.cache_ttl = 300
        config.cache_max_size = 1000
        config.rate_limit_requests = 100
        config.rate_limit_window = 60
        return config
    
    @pytest.fixture
    async def mcp_client(self, mock_config):
        """Create MCP test client."""
        with patch('tidb_mcp_server.mcp_server.QueryExecutor'):
            server = TiDBMCPServer(mock_config)
            client = MCPTestClient(server)
            yield client
    
    @pytest.mark.asyncio
    async def test_initialize_protocol(self, mcp_client):
        """Test MCP protocol initialization."""
        response = await mcp_client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        })
        
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        assert "protocolVersion" in response["result"]
        assert "capabilities" in response["result"]
        assert "serverInfo" in response["result"]
        assert response["result"]["serverInfo"]["name"] == "tidb-mcp-server"
    
    @pytest.mark.asyncio
    async def test_list_tools_request(self, mcp_client):
        """Test tools/list request."""
        with patch.object(mcp_client.server, 'list_tools') as mock_list_tools:
            mock_tools = [
                {
                    "name": "execute_query",
                    "description": "Execute a SQL query",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"}
                        },
                        "required": ["query"]
                    }
                }
            ]
            mock_list_tools.return_value = mock_tools
            
            response = await mcp_client.send_request("tools/list")
            
            assert response["jsonrpc"] == "2.0"
            assert "result" in response
            assert "tools" in response["result"]
            assert len(response["result"]["tools"]) == 1
            assert response["result"]["tools"][0]["name"] == "execute_query"
    
    @pytest.mark.asyncio
    async def test_call_tool_success(self, mcp_client):
        """Test successful tool call."""
        with patch.object(mcp_client.server, 'call_tool') as mock_call_tool:
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
            
            response = await mcp_client.send_request("tools/call", {
                "name": "execute_query",
                "arguments": {
                    "query": "SELECT * FROM test_table"
                }
            })
            
            assert response["jsonrpc"] == "2.0"
            assert "result" in response
            assert "content" in response["result"]
            assert len(response["result"]["content"]) == 1
    
    @pytest.mark.asyncio
    async def test_call_tool_error(self, mcp_client):
        """Test tool call with error."""
        with patch.object(mcp_client.server, 'call_tool') as mock_call_tool:
            mock_call_tool.side_effect = QueryExecutionError("Invalid SQL syntax")
            
            response = await mcp_client.send_request("tools/call", {
                "name": "execute_query",
                "arguments": {
                    "query": "INVALID SQL"
                }
            })
            
            assert response["jsonrpc"] == "2.0"
            assert "error" in response
            assert response["error"]["code"] == -32602
            assert "Query execution error" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_invalid_method(self, mcp_client):
        """Test invalid method request."""
        response = await mcp_client.send_request("invalid/method")
        
        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32601
        assert response["error"]["message"] == "Method not found"
    
    @pytest.mark.asyncio
    async def test_get_capabilities(self, mcp_client):
        """Test capabilities/get request."""
        with patch.object(mcp_client.server, 'get_capabilities') as mock_get_capabilities:
            mock_capabilities = {
                "tools": {"listSupported": True},
                "resources": {"listSupported": False},
                "prompts": {"listSupported": False}
            }
            mock_get_capabilities.return_value = mock_capabilities
            
            response = await mcp_client.send_request("capabilities/get")
            
            assert response["jsonrpc"] == "2.0"
            assert "result" in response
            assert response["result"] == mock_capabilities


class TestToolParameterValidation:
    """Test tool parameter validation scenarios."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock(spec=ServerConfig)
        config.tidb_host = "test-host.com"
        config.tidb_port = 4000
        config.tidb_user = "test_user"
        config.tidb_password = "test_password"
        config.tidb_database = "test_db"
        return config
    
    @pytest.fixture
    async def mcp_client(self, mock_config):
        """Create MCP test client."""
        with patch('tidb_mcp_server.mcp_server.QueryExecutor'):
            server = TiDBMCPServer(mock_config)
            client = MCPTestClient(server)
            yield client
    
    @pytest.mark.asyncio
    async def test_execute_query_valid_parameters(self, mcp_client):
        """Test execute_query with valid parameters."""
        with patch.object(mcp_client.server, 'call_tool') as mock_call_tool:
            mock_call_tool.return_value = {
                "content": [{"type": "text", "text": "{}"}]
            }
            
            response = await mcp_client.send_request("tools/call", {
                "name": "execute_query",
                "arguments": {
                    "query": "SELECT * FROM users",
                    "limit": 100
                }
            })
            
            assert "result" in response
            mock_call_tool.assert_called_once_with("execute_query", {
                "query": "SELECT * FROM users",
                "limit": 100
            })
    
    @pytest.mark.asyncio
    async def test_execute_query_missing_required_parameter(self, mcp_client):
        """Test execute_query with missing required parameter."""
        with patch.object(mcp_client.server, 'call_tool') as mock_call_tool:
            mock_call_tool.side_effect = ValueError("Missing required parameter: query")
            
            response = await mcp_client.send_request("tools/call", {
                "name": "execute_query",
                "arguments": {}
            })
            
            assert "error" in response
    
    @pytest.mark.asyncio
    async def test_describe_table_valid_parameters(self, mcp_client):
        """Test describe_table with valid parameters."""
        with patch.object(mcp_client.server, 'call_tool') as mock_call_tool:
            mock_call_tool.return_value = {
                "content": [{"type": "text", "text": "{}"}]
            }
            
            response = await mcp_client.send_request("tools/call", {
                "name": "describe_table",
                "arguments": {
                    "table_name": "users",
                    "include_indexes": True
                }
            })
            
            assert "result" in response
            mock_call_tool.assert_called_once_with("describe_table", {
                "table_name": "users",
                "include_indexes": True
            })
    
    @pytest.mark.asyncio
    async def test_list_tables_optional_parameters(self, mcp_client):
        """Test list_tables with optional parameters."""
        with patch.object(mcp_client.server, 'call_tool') as mock_call_tool:
            mock_call_tool.return_value = {
                "content": [{"type": "text", "text": "{}"}]
            }
            
            response = await mcp_client.send_request("tools/call", {
                "name": "list_tables",
                "arguments": {
                    "table_type": "TABLE"
                }
            })
            
            assert "result" in response
            mock_call_tool.assert_called_once_with("list_tables", {
                "table_type": "TABLE"
            })


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock(spec=ServerConfig)
        config.tidb_host = "test-host.com"
        config.tidb_port = 4000
        config.tidb_user = "test_user"
        config.tidb_password = "test_password"
        config.tidb_database = "test_db"
        return config
    
    @pytest.fixture
    async def mcp_client(self, mock_config):
        """Create MCP test client."""
        with patch('tidb_mcp_server.mcp_server.QueryExecutor'):
            server = TiDBMCPServer(mock_config)
            client = MCPTestClient(server)
            yield client
    
    @pytest.mark.asyncio
    async def test_empty_query_parameter(self, mcp_client):
        """Test handling of empty query parameter."""
        with patch.object(mcp_client.server, 'call_tool') as mock_call_tool:
            mock_call_tool.side_effect = ValueError("Query cannot be empty")
            
            response = await mcp_client.send_request("tools/call", {
                "name": "execute_query",
                "arguments": {
                    "query": ""
                }
            })
            
            assert "error" in response
    
    @pytest.mark.asyncio
    async def test_sql_injection_attempt(self, mcp_client):
        """Test handling of potential SQL injection."""
        with patch.object(mcp_client.server, 'call_tool') as mock_call_tool:
            mock_call_tool.side_effect = QueryExecutionError("Potentially dangerous query detected")
            
            response = await mcp_client.send_request("tools/call", {
                "name": "execute_query",
                "arguments": {
                    "query": "SELECT * FROM users; DROP TABLE users; --"
                }
            })
            
            assert "error" in response
    
    @pytest.mark.asyncio
    async def test_very_large_query(self, mcp_client):
        """Test handling of very large queries."""
        large_query = "SELECT * FROM users WHERE id IN (" + ",".join(str(i) for i in range(10000)) + ")"
        
        with patch.object(mcp_client.server, 'call_tool') as mock_call_tool:
            mock_call_tool.side_effect = ValueError("Query too large")
            
            response = await mcp_client.send_request("tools/call", {
                "name": "execute_query",
                "arguments": {
                    "query": large_query
                }
            })
            
            assert "error" in response
    
    @pytest.mark.asyncio
    async def test_nonexistent_table(self, mcp_client):
        """Test handling of queries on nonexistent tables."""
        with patch.object(mcp_client.server, 'call_tool') as mock_call_tool:
            mock_call_tool.side_effect = QueryExecutionError("Table 'nonexistent_table' doesn't exist")
            
            response = await mcp_client.send_request("tools/call", {
                "name": "describe_table",
                "arguments": {
                    "table_name": "nonexistent_table"
                }
            })
            
            assert "error" in response
            assert "doesn't exist" in response["error"]["data"]
    
    @pytest.mark.asyncio
    async def test_database_connection_lost(self, mcp_client):
        """Test handling of lost database connection."""
        with patch.object(mcp_client.server, 'call_tool') as mock_call_tool:
            mock_call_tool.side_effect = DatabaseConnectionError("Lost connection to database")
            
            response = await mcp_client.send_request("tools/call", {
                "name": "execute_query",
                "arguments": {
                    "query": "SELECT * FROM users"
                }
            })
            
            assert "error" in response
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, mcp_client):
        """Test concurrent tool calls."""
        with patch.object(mcp_client.server, 'call_tool') as mock_call_tool:
            mock_call_tool.return_value = {
                "content": [{"type": "text", "text": "{}"}]
            }
            
            # Execute multiple tool calls concurrently
            tasks = []
            for i in range(10):
                task = mcp_client.send_request("tools/call", {
                    "name": "execute_query",
                    "arguments": {
                        "query": f"SELECT * FROM table_{i}"
                    }
                })
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            
            # All requests should succeed
            for response in responses:
                assert "result" in response
                assert response["jsonrpc"] == "2.0"
            
            # Verify all calls were made
            assert mock_call_tool.call_count == 10