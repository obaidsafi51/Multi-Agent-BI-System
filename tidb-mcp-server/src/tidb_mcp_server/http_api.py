"""
FastAPI HTTP wrapper for TiDB MCP Server tools.

This module creates HTTP endpoints for MCP tools to enable communication
between agents and the MCP server via standard HTTP requests.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from tidb_mcp_server.config import ServerConfig
from tidb_mcp_server.mcp_server import TiDBMCPServer
import tidb_mcp_server.mcp_tools as mcp_tools

logger = logging.getLogger(__name__)


# Pydantic models for HTTP requests
class ExecuteQueryRequest(BaseModel):
    query: str
    timeout: Optional[int] = None
    use_cache: bool = True


class ValidateQueryRequest(BaseModel):
    query: str


class GetSampleDataRequest(BaseModel):
    database: str
    table: str
    limit: int = 10
    masked_columns: Optional[List[str]] = None


class GetTableSchemaRequest(BaseModel):
    database: str
    table: str


class DiscoverTablesRequest(BaseModel):
    database: str


class ClearCacheRequest(BaseModel):
    cache_type: str = "all"


# Global MCP server instance
mcp_server: Optional[TiDBMCPServer] = None

# Create FastAPI app
app = FastAPI(
    title="TiDB MCP Server HTTP API",
    description="HTTP API wrapper for TiDB MCP Server tools",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize MCP server on startup"""
    global mcp_server
    
    try:
        logger.info("Starting TiDB MCP Server HTTP API...")
        
        # Load configuration
        config = ServerConfig()
        
        # Initialize MCP server
        mcp_server = TiDBMCPServer(config)
        
        # Start MCP server in background
        asyncio.create_task(start_mcp_server())
        
        logger.info("TiDB MCP Server HTTP API started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start TiDB MCP Server HTTP API: {e}")
        raise


async def start_mcp_server():
    """Start the MCP server in background"""
    global mcp_server
    try:
        if mcp_server:
            await mcp_server.start()
    except Exception as e:
        logger.error(f"MCP server startup failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global mcp_server
    
    if mcp_server:
        await mcp_server.shutdown()
        logger.info("TiDB MCP Server HTTP API stopped")


# HTTP endpoints for MCP tools

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "tidb-mcp-server-http",
        "mcp_server_running": mcp_server is not None,
        "timestamp": asyncio.get_event_loop().time()
    }


@app.post("/tools/discover_databases_tool")
async def discover_databases_endpoint():
    """Discover all accessible databases"""
    try:
        result = mcp_tools.discover_databases()
        return result
    except Exception as e:
        logger.error(f"discover_databases failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/discover_tables_tool")
async def discover_tables_endpoint(request: DiscoverTablesRequest):
    """Discover tables in a specific database"""
    try:
        result = mcp_tools.discover_tables(request.database)
        return result
    except Exception as e:
        logger.error(f"discover_tables failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/get_table_schema_tool")
async def get_table_schema_endpoint(request: GetTableSchemaRequest):
    """Get detailed schema information for a specific table"""
    try:
        result = mcp_tools.get_table_schema(request.database, request.table)
        return result
    except Exception as e:
        logger.error(f"get_table_schema failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/get_sample_data_tool")
async def get_sample_data_endpoint(request: GetSampleDataRequest):
    """Get sample data from a specific table"""
    try:
        result = mcp_tools.get_sample_data(
            database=request.database,
            table=request.table,
            limit=request.limit,
            masked_columns=request.masked_columns
        )
        return result
    except Exception as e:
        logger.error(f"get_sample_data failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/execute_query_tool")
async def execute_query_endpoint(request: ExecuteQueryRequest):
    """Execute a read-only SQL query"""
    try:
        result = mcp_tools.execute_query(
            query=request.query,
            timeout=request.timeout,
            use_cache=request.use_cache
        )
        return result
    except Exception as e:
        logger.error(f"execute_query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/validate_query_tool")
async def validate_query_endpoint(request: ValidateQueryRequest):
    """Validate a SQL query without executing it"""
    try:
        result = mcp_tools.validate_query(request.query)
        return result
    except Exception as e:
        logger.error(f"validate_query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/get_server_stats_tool")
async def get_server_stats_endpoint():
    """Get server statistics and performance metrics"""
    try:
        result = mcp_tools.get_server_stats()
        return result
    except Exception as e:
        logger.error(f"get_server_stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/clear_cache_tool")
async def clear_cache_endpoint(request: ClearCacheRequest):
    """Clear cached data"""
    try:
        result = mcp_tools.clear_cache(request.cache_type)
        return result
    except Exception as e:
        logger.error(f"clear_cache failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Additional endpoints for direct tool access

@app.get("/tools")
async def list_tools():
    """List all available MCP tools"""
    return {
        "tools": [
            "discover_databases_tool",
            "discover_tables_tool",
            "get_table_schema_tool",
            "get_sample_data_tool",
            "execute_query_tool",
            "validate_query_tool",
            "get_server_stats_tool",
            "clear_cache_tool"
        ],
        "description": "Available MCP tools for TiDB operations"
    }


@app.get("/status")
async def get_status():
    """Get detailed server status"""
    return {
        "http_api_status": "running",
        "mcp_server_initialized": mcp_server is not None,
        "mcp_server_running": mcp_server._running if mcp_server else False,
        "tools_available": 8,
        "timestamp": asyncio.get_event_loop().time()
    }


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the HTTP API server
    uvicorn.run(
        "http_api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
