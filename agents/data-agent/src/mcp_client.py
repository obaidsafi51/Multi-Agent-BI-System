"""
MCP Client for Data Agent to connect to TiDB MCP Server.

This module implements an MCP client that communicates with the TiDB MCP Server
to execute database operations through the Model Context Protocol.
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional
import structlog

import aiohttp
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class MCPRequest(BaseModel):
    """MCP request model."""
    jsonrpc: str = "2.0"
    id: str
    method: str
    params: Dict[str, Any] = {}


class MCPResponse(BaseModel):
    """MCP response model."""
    jsonrpc: str = "2.0"
    id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class TiDBMCPClient:
    """
    MCP Client for communicating with TiDB MCP Server.
    
    Provides methods to execute database operations through MCP protocol
    including schema discovery, query execution, and data retrieval.
    """
    
    def __init__(self, server_url: Optional[str] = None):
        """
        Initialize MCP client.
        
        Args:
            server_url: URL of the TiDB MCP Server
        """
        if server_url is None:
            server_url = os.getenv('TIDB_MCP_SERVER_URL', 'http://tidb-mcp-server:8000')
        
        self.server_url = server_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_connected = False
        
        logger.info(f"Initialized TiDB MCP Client for server: {server_url}")
    
    async def connect(self) -> bool:
        """
        Connect to the TiDB MCP Server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if not self.session:
                timeout = aiohttp.ClientTimeout(total=30)
                self.session = aiohttp.ClientSession(timeout=timeout)
            
            # Test connection with server stats
            result = await self._send_request("get_server_stats_tool", {})
            if result and not result.get('error'):
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
    
    async def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Send MCP request to the server.
        
        Args:
            method: MCP method name
            params: Request parameters
            
        Returns:
            Response data or None if failed
        """
        if not self.session:
            await self.connect()
        
        request_id = str(uuid.uuid4())
        request = MCPRequest(
            id=request_id,
            method=method,
            params=params
        )
        
        try:
            # Since TiDB MCP Server uses FastMCP, we need to call the tools directly
            # through HTTP endpoints rather than JSON-RPC
            url = f"{self.server_url}/tools/{method}"
            
            logger.debug(f"Sending MCP request to {url}: {method}")
            
            async with self.session.post(
                url,
                json=params,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.debug(f"MCP request successful: {method}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"MCP request failed ({response.status}): {error_text}")
                    return {"error": f"HTTP {response.status}: {error_text}"}
        
        except Exception as e:
            logger.error(f"MCP request error for {method}: {e}")
            return {"error": str(e)}
    
    async def discover_databases(self) -> List[Dict[str, Any]]:
        """
        Discover all accessible databases.
        
        Returns:
            List of database information
        """
        result = await self._send_request("discover_databases_tool", {})
        if result and not result.get('error'):
            return result
        return []
    
    async def discover_tables(self, database: str) -> List[Dict[str, Any]]:
        """
        Discover tables in a specific database.
        
        Args:
            database: Database name
            
        Returns:
            List of table information
        """
        result = await self._send_request("discover_tables_tool", {"database": database})
        if result and not result.get('error'):
            return result
        return []
    
    async def get_table_schema(self, database: str, table: str) -> Optional[Dict[str, Any]]:
        """
        Get table schema information.
        
        Args:
            database: Database name
            table: Table name
            
        Returns:
            Table schema information
        """
        result = await self._send_request("get_table_schema_tool", {
            "database": database,
            "table": table
        })
        
        if result and not result.get('error'):
            return result
        return None
    
    async def get_sample_data(
        self,
        database: str,
        table: str,
        limit: int = 10,
        masked_columns: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get sample data from a table.
        
        Args:
            database: Database name
            table: Table name
            limit: Number of rows to return
            masked_columns: Columns to mask
            
        Returns:
            Sample data information
        """
        params = {
            "database": database,
            "table": table,
            "limit": limit
        }
        
        if masked_columns:
            params["masked_columns"] = masked_columns
        
        result = await self._send_request("get_sample_data_tool", params)
        
        if result and not result.get('error'):
            return result
        return None
    
    async def execute_query(
        self,
        query: str,
        timeout: Optional[int] = None,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query to execute
            timeout: Query timeout in seconds
            use_cache: Whether to use caching
            
        Returns:
            Query results
        """
        params = {
            "query": query,
            "use_cache": use_cache
        }
        
        if timeout:
            params["timeout"] = timeout
        
        result = await self._send_request("execute_query_tool", params)
        
        if result and not result.get('error'):
            return result
        return None
    
    async def validate_query(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Validate a SQL query without executing it.
        
        Args:
            query: SQL query to validate
            
        Returns:
            Validation results
        """
        result = await self._send_request("validate_query_tool", {"query": query})
        
        if result and not result.get('error'):
            return result
        return None
    
    async def get_server_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get server statistics.
        
        Returns:
            Server statistics
        """
        result = await self._send_request("get_server_stats_tool", {})
        
        if result and not result.get('error'):
            return result
        return None
    
    async def clear_cache(self, cache_type: str = "all") -> Optional[Dict[str, Any]]:
        """
        Clear server cache.
        
        Args:
            cache_type: Type of cache to clear
            
        Returns:
            Cache clearing results
        """
        result = await self._send_request("clear_cache_tool", {"cache_type": cache_type})
        
        if result and not result.get('error'):
            return result
        return None
    
    async def health_check(self) -> bool:
        """
        Check if the MCP server is healthy.
        
        Returns:
            True if server is healthy, False otherwise
        """
        try:
            stats = await self.get_server_stats()
            return stats is not None and stats.get('server_status') == 'healthy'
        except Exception:
            return False


# Global MCP client instance
_mcp_client: Optional[TiDBMCPClient] = None


def get_mcp_client() -> TiDBMCPClient:
    """Get the global MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = TiDBMCPClient()
    return _mcp_client


async def close_mcp_client():
    """Close the global MCP client instance."""
    global _mcp_client
    if _mcp_client:
        await _mcp_client.disconnect()
        _mcp_client = None
