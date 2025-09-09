"""
Backend MCP Client for TiDB MCP Server integration.
Replaces direct database connections with MCP server communication.
"""

import asyncio
import logging
import os
import json
from typing import Any, Dict, List, Optional
import aiohttp
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class BackendMCPClient:
    """
    MCP Client for Backend to communicate with TiDB MCP Server.
    Provides database operations through MCP protocol.
    """
    
    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or os.getenv('TIDB_MCP_SERVER_URL', 'http://tidb-mcp-server:8000')
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_connected = False
        
    async def connect(self) -> bool:
        """Connect to the TiDB MCP Server."""
        try:
            if not self.session:
                timeout = aiohttp.ClientTimeout(total=30)
                self.session = aiohttp.ClientSession(timeout=timeout)
            
            # Test connection with health check
            async with self.session.get(f"{self.server_url}/health") as response:
                if response.status == 200:
                    self.is_connected = True
                    logger.info("Successfully connected to TiDB MCP Server")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to connect to TiDB MCP Server: {e}")
        
        self.is_connected = False
        return False
    
    async def disconnect(self):
        """Disconnect from the TiDB MCP Server."""
        if self.session:
            await self.session.close()
            self.session = None
        
        self.is_connected = False
        logger.info("Disconnected from TiDB MCP Server")
    
    async def execute_query(self, query: str, params: Optional[List] = None) -> Optional[Dict[str, Any]]:
        """Execute a SQL query through MCP server."""
        try:
            if not self.session:
                await self.connect()
            
            payload = {
                "query": query,
                "timeout": 30,
                "use_cache": True
            }
            
            if params:
                payload["params"] = params
            
            async with self.session.post(
                f"{self.server_url}/tools/execute_query_tool",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"MCP query execution failed ({response.status}): {error_text}")
                    return {"error": f"HTTP {response.status}: {error_text}"}
                    
        except Exception as e:
            logger.error(f"MCP query execution error: {e}")
            return {"error": str(e)}
    

    
    async def discover_schema(self, database: str = "Agentic_BI") -> Optional[Dict[str, Any]]:
        """Discover database schema through MCP server."""
        try:
            if not self.session:
                await self.connect()
            
            payload = {"database": database}
            
            async with self.session.post(
                f"{self.server_url}/tools/discover_databases_tool",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"MCP schema discovery failed ({response.status}): {error_text}")
                    return {"error": f"HTTP {response.status}: {error_text}"}
                    
        except Exception as e:
            logger.error(f"MCP schema discovery error: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> bool:
        """Check MCP server health."""
        try:
            if not self.session:
                await self.connect()
            
            async with self.session.get(f"{self.server_url}/health") as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"MCP health check failed: {e}")
            return False


# Global MCP client instance
_backend_mcp_client: Optional[BackendMCPClient] = None


def get_backend_mcp_client() -> BackendMCPClient:
    """Get the global backend MCP client instance."""
    global _backend_mcp_client
    if _backend_mcp_client is None:
        _backend_mcp_client = BackendMCPClient()
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
        if result and not result.get('error'):
            return {
                'success': True,
                'data': result.get('rows', []),
                'columns': result.get('columns', []),
                'row_count': result.get('row_count', 0)
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Unknown error'),
                'data': [],
                'columns': [],
                'row_count': 0
            }



