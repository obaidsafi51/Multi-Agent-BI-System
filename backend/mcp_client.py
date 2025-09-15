"""
Backend MCP Client for TiDB MCP Server integration.
Replaces direct database connections with MCP server communication.
Supports both HTTP and WebSocket modes for optimal performance.
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import aiohttp
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

try:
    from .websocket_mcp_client import WebSocketMCPClient
except ImportError:
    # Fallback for when running as script or in certain environments
    try:
        from websocket_mcp_client import WebSocketMCPClient
    except ImportError:
        # If WebSocket client is not available, disable WebSocket mode
        WebSocketMCPClient = None
        logger.warning("WebSocketMCPClient not available, WebSocket mode disabled")


class BackendMCPClient:
    """
    MCP Client for Backend to communicate with TiDB MCP Server.
    Provides database operations through MCP protocol.
    Supports both HTTP and WebSocket modes for optimal performance.
    """
    
    def __init__(self, server_url: Optional[str] = None, use_websocket: bool = True):
        self.use_websocket = use_websocket and os.getenv('USE_WEBSOCKET_MCP', 'false').lower() == 'true' and WebSocketMCPClient is not None
        
        # Choose appropriate server URL based on mode
        if self.use_websocket and WebSocketMCPClient is not None:
            self.server_url = server_url or os.getenv('MCP_SERVER_WS_URL', 'ws://tidb-mcp-server:8000/ws')
        else:
            self.server_url = server_url or os.getenv('TIDB_MCP_SERVER_URL', 'http://tidb-mcp-server:8000')
        
        # Initialize appropriate client
        if self.use_websocket and WebSocketMCPClient is not None:
            self.ws_client = WebSocketMCPClient(server_url=self.server_url, agent_type="backend")
            self.session = None
            logger.info("Initialized WebSocket MCP Client")
        else:
            self.ws_client = None
            self.session: Optional[aiohttp.ClientSession] = None
            if use_websocket and WebSocketMCPClient is None:
                logger.warning("WebSocket requested but not available, falling back to HTTP")
            logger.info("Initialized HTTP MCP Client")
            
        self.is_connected = False
        
    async def connect(self) -> bool:
        """Connect to the TiDB MCP Server."""
        try:
            if self.use_websocket and self.ws_client:
                self.is_connected = await self.ws_client.connect()
                if self.is_connected:
                    logger.info("Successfully connected to TiDB MCP Server via WebSocket")
                return self.is_connected
            else:
                # HTTP fallback
                if not self.session:
                    timeout = aiohttp.ClientTimeout(total=30)
                    self.session = aiohttp.ClientSession(timeout=timeout)
                
                # Test connection with health check
                async with self.session.get(f"{self.server_url}/health") as response:
                    if response.status == 200:
                        self.is_connected = True
                        logger.info("Successfully connected to TiDB MCP Server via HTTP")
                        return True
                    
        except Exception as e:
            logger.error(f"Failed to connect to TiDB MCP Server: {e}")
        
        self.is_connected = False
        return False
    
    async def disconnect(self):
        """Disconnect from the TiDB MCP Server."""
        if self.use_websocket and self.ws_client:
            await self.ws_client.disconnect()
        elif self.session:
            await self.session.close()
            self.session = None
        
        self.is_connected = False
        logger.info("Disconnected from TiDB MCP Server")
    
    async def execute_query(self, query: str, database: str = None, params: Dict = None) -> Dict[str, Any]:
        """Execute a query through MCP server."""
        try:
            payload = {
                "query": query,
                "timeout": 30,
                "use_cache": True
            }
            
            if params:
                payload["params"] = params
            
            # Use the generic call_tool method which handles both WebSocket and HTTP modes
            result = await self.call_tool("execute_query", payload)
            
            # The MCP server returns the result directly, convert to backend format
            if isinstance(result, dict) and "error" not in result:
                return {
                    "success": True,
                    "data": result.get("rows", []),
                    "columns": result.get("columns", []),
                    "metadata": result.get("metadata", {}),
                    "summary": result.get("summary", f"Query executed successfully"),
                    "query": query
                }
            else:
                return result if "error" in result else {"error": "Unexpected response format from MCP server"}
                    
        except Exception as e:
            logger.error(f"MCP execute query error: {e}")
            return {"error": str(e)}
    

    
    async def discover_databases(self) -> Optional[Dict[str, Any]]:
        """Discover all databases through MCP server."""
        try:
            # Use the generic call_tool method which handles both WebSocket and HTTP modes
            result = await self.call_tool("list_databases")
            return result
                    
        except Exception as e:
            logger.error(f"MCP database discovery error: {e}")
            return {"error": str(e)}
    
    async def discover_tables(self, database: str) -> Optional[Dict[str, Any]]:
        """Discover tables in a specific database through MCP server."""
        try:
            payload = {"database": database}
            
            # Use the generic call_tool method which handles both WebSocket and HTTP modes
            result = await self.call_tool("list_tables", payload)
            return result
                    
        except Exception as e:
            logger.error(f"MCP table discovery error: {e}")
            return {"error": str(e)}
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generic tool calling method for MCP server - handles both WebSocket and HTTP modes."""
        try:
            if params is None:
                params = {}
            
            # Map our generic tool names to MCP tool names
            tool_name_map = {
                "list_databases": "discover_databases",
                "list_tables": "discover_tables", 
                "get_table_schema": "get_table_schema",
                "execute_query": "execute_query",
                "get_sample_data": "get_sample_data",
                "validate_query": "validate_query"
            }
            
            mcp_tool_name = tool_name_map.get(tool_name, tool_name)
            
            # Use WebSocket client if enabled, otherwise use HTTP
            if self.use_websocket and self.ws_client:
                logger.debug(f"Calling MCP tool '{mcp_tool_name}' via WebSocket with params: {params}")
                result = await self.ws_client.call_tool(mcp_tool_name, **params)
                logger.debug(f"WebSocket MCP tool '{mcp_tool_name}' result: {result}")
                return result
            else:
                # HTTP fallback
                if not self.session:
                    await self.connect()
                
                # Map to HTTP endpoint names
                endpoint_map = {
                    "list_databases": "discover_databases_tool",
                    "list_tables": "discover_tables_tool", 
                    "get_table_schema": "get_table_schema_tool",
                    "execute_query": "execute_query_tool",
                    "get_sample_data": "get_sample_data_tool",
                    "validate_query": "validate_query_tool"
                }
                
                endpoint = endpoint_map.get(tool_name, f"{tool_name}_tool")
                
                async with self.session.post(
                    f"{self.server_url}/tools/{endpoint}",
                    json=params,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"MCP tool '{tool_name}' -> '{endpoint}' failed ({response.status}): {error_text}")
                        return {"error": f"HTTP {response.status}: {error_text}"}
                    
        except Exception as e:
            logger.error(f"MCP tool '{tool_name}' error: {e}")
            return {"error": str(e)}
    
    async def build_schema_context(self, database_name: str = None) -> Dict[str, Any]:
        """
        Build complete schema context using MCP server's database tools.
        This method uses the proper MCP tools to construct comprehensive schema information.
        """
        try:
            logger.info(f"🔨 Building schema context using MCP tools for: {database_name or 'all databases'}")
            
            # Get list of databases if none specified
            if database_name:
                databases_to_process = [database_name]
            else:
                db_result = await self.call_tool("list_databases", {})
                if not db_result.get("success"):
                    raise Exception(f"Failed to list databases: {db_result.get('error')}")
                databases_to_process = [db["name"] for db in db_result.get("databases", []) if db.get("accessible", True)]
            
            schema_context = {
                "databases": {},
                "tables": [],
                "total_tables": 0,
                "total_columns": 0,
                "last_updated": datetime.now().isoformat(),
                "cache_key": f"schema_context:{database_name or 'all'}"
            }
            
            for db_name in databases_to_process:
                try:
                    logger.info(f"📊 Processing database: {db_name}")
                    
                    # Get tables for this database using MCP tool
                    tables_result = await self.call_tool("list_tables", {"database": db_name})
                    if tables_result and "error" in tables_result:
                        logger.warning(f"⚠️ Failed to get tables for {db_name}: {tables_result.get('error')}")
                        schema_context["databases"][db_name] = {"error": f"Failed to list tables: {tables_result.get('error')}"}
                        continue
                    
                    # Handle direct array response from MCP server
                    tables = tables_result if isinstance(tables_result, list) else tables_result.get("tables", [])
                    database_info = {
                        "name": db_name,
                        "tables": [],
                        "table_count": len(tables)
                    }
                    
                    # Get detailed schema for each table using MCP tools
                    for table in tables:
                        table_name = table.get("name") if isinstance(table, dict) else str(table)
                        try:
                            # Use get_table_schema MCP tool
                            schema_result = await self.call_tool("get_table_schema", {
                                "database": db_name,
                                "table": table_name
                            })
                            
                            logger.debug(f"🔍 Schema result for {db_name}.{table_name}: {type(schema_result)}")
                            
                            # Handle different response formats - WebSocket MCP wraps in success/schema structure
                            actual_schema = schema_result
                            if isinstance(schema_result, dict) and schema_result.get("success") and "schema" in schema_result:
                                actual_schema = schema_result["schema"]
                            
                            if actual_schema and "columns" in actual_schema:
                                # MCP server returns schema directly, not nested
                                columns = actual_schema.get("columns", [])
                                indexes = actual_schema.get("indexes", [])
                                foreign_keys = actual_schema.get("foreign_keys", [])
                                primary_keys = actual_schema.get("primary_keys", [])
                                
                                # Build detailed table info with complete column metadata
                                table_info = {
                                    "name": table_name,
                                    "columns": columns,  # Full column details with data_types, constraints
                                    "column_count": len(columns),
                                    "indexes": indexes,
                                    "foreign_keys": foreign_keys,
                                    "primary_keys": primary_keys,
                                    "column_names": [col.get("name") for col in columns],
                                    "data_types": {col.get("name"): col.get("data_type") for col in columns},
                                    "nullable_columns": [col.get("name") for col in columns if col.get("is_nullable")],
                                    "primary_key_columns": [col.get("name") for col in columns if col.get("is_primary_key")]
                                }
                                
                                database_info["tables"].append(table_info)
                                schema_context["total_columns"] += len(columns)
                                schema_context["tables"].append(f"{db_name}.{table_name}")
                                
                                logger.debug(f"📋 {table_name}: {len(columns)} columns with detailed metadata")
                            else:
                                logger.warning(f"⚠️ Failed to get schema for {db_name}.{table_name}: {schema_result}")
                                if schema_result and "error" in schema_result:
                                    logger.error(f"❌ Schema error for {db_name}.{table_name}: {schema_result['error']}")
                                
                        except Exception as e:
                            logger.error(f"❌ Error getting schema for {db_name}.{table_name}: {e}")
                            continue
                    
                    schema_context["databases"][db_name] = database_info
                    schema_context["total_tables"] += len(database_info["tables"])
                    
                    logger.info(f"✅ Processed database {db_name}: {len(database_info['tables'])} tables, {sum(t.get('column_count', 0) for t in database_info['tables'])} columns")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing database {db_name}: {e}")
                    schema_context["databases"][db_name] = {"error": str(e)}
                    continue
            
            logger.info(f"🎉 Schema context built successfully: {schema_context['total_tables']} tables, {schema_context['total_columns']} columns across {len(schema_context['databases'])} databases")
            return schema_context
            
        except Exception as e:
            logger.error(f"💥 Failed to build schema context: {e}")
            raise Exception(f"Schema context building failed: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check MCP server health."""
        try:
            if self.use_websocket and self.ws_client and self.ws_client.is_connected:
                # WebSocket is connected, assume healthy
                return True
            elif not self.session:
                await self.connect()
            
            if self.session:
                async with self.session.get(f"{self.server_url}/health") as response:
                    return response.status == 200
            return False
                
        except Exception as e:
            logger.error(f"MCP health check failed: {e}")
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics from the MCP client."""
        base_stats = {
            "connection_type": "websocket" if self.use_websocket else "http",
            "is_connected": self.is_connected,
            "server_url": self.server_url
        }
        
        if self.use_websocket and self.ws_client:
            # Get WebSocket-specific stats
            ws_stats = self.ws_client.get_cache_stats()
            base_stats.update({
                "websocket_stats": ws_stats,
                "client_side_caching": True,
                "request_deduplication": True
            })
        else:
            base_stats.update({
                "websocket_stats": None,
                "client_side_caching": False,
                "request_deduplication": False
            })
        
        return base_stats
    
    def subscribe_to_schema_changes(self, handler):
        """Subscribe to real-time schema change events (WebSocket only)."""
        if self.use_websocket and self.ws_client:
            self.ws_client.subscribe_to_events("schema_changed", handler)
            logger.info("Subscribed to schema change events")
        else:
            logger.warning("Schema change events only available with WebSocket connection")


# Global MCP client instance
_backend_mcp_client: Optional[BackendMCPClient] = None
_client_creation_lock = asyncio.Lock()


def get_backend_mcp_client() -> BackendMCPClient:
    """Get the global backend MCP client instance."""
    global _backend_mcp_client
    if _backend_mcp_client is None:
        logger.debug("Creating new BackendMCPClient instance")
        _backend_mcp_client = BackendMCPClient()
    else:
        logger.debug("Returning existing BackendMCPClient instance")
    return _backend_mcp_client


async def close_backend_mcp_client():
    """Close the global backend MCP client instance."""
    global _backend_mcp_client
    if _backend_mcp_client:
        await _backend_mcp_client.disconnect()
        _backend_mcp_client = None


@asynccontextmanager
async def mcp_connection():
    """Context manager for MCP connections."""
    client = get_backend_mcp_client()
    
    try:
        if not client.is_connected:
            await client.connect()
        yield client
    except Exception as e:
        logger.error(f"MCP connection error: {e}")
        raise
    # Note: We keep the connection alive for reuse


async def execute_mcp_query(query: str, params: Optional[List] = None) -> Dict[str, Any]:
    """Execute a query through MCP client."""
    async with mcp_connection() as client:
        result = await client.execute_query(query, params)
        if result and result.get('success'):
            return result
        else:
            return {
                'success': False,
                'error': result.get('error', 'Unknown error') if result else 'No response from MCP server',
                'data': [],
                'columns': [],
                'row_count': 0
            }



