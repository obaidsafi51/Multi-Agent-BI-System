"""
FastAPI HTTP wrapper for Universal MCP Server tools.

This module creates HTTP endpoints for MCP tools to enable communication
between agents and the MCP server via standard HTTP requests.
Supports both database operations and LLM services.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from tidb_mcp_server.config import ServerConfig
from tidb_mcp_server.mcp_server import UniversalMCPServer
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


# LLM request models
class GenerateTextRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    use_cache: bool = True


class AnalyzeDataRequest(BaseModel):
    data: str
    analysis_type: str = "general"
    context: Optional[str] = None


class GenerateSQLRequest(BaseModel):
    natural_language_query: str
    schema_info: Optional[str] = None
    examples: Optional[List[str]] = None


class ExplainResultsRequest(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    context: Optional[str] = None


# Global MCP server instance
mcp_server: Optional[UniversalMCPServer] = None
websocket_manager = None

async def initialize_mcp_server_background(config):
    """Initialize MCP server in background to avoid blocking FastAPI startup"""
    global mcp_server
    try:
        logger.info("Starting MCP server background initialization...")
        mcp_server = UniversalMCPServer(config)
        await mcp_server.start()
        logger.info("MCP server auto-initialized and started successfully")
    except Exception as e:
        logger.error(f"Background MCP server initialization failed: {e}")
        mcp_server = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown"""
    global mcp_server
    
    # Startup
    try:
        logger.info("Starting TiDB MCP Server HTTP API...")
        
        # Auto-initialize MCP server for development
        auto_init = os.getenv("AUTO_INITIALIZE_MCP", "true").lower() == "true"
        
        if auto_init and mcp_server is None:
            logger.info("Auto-initializing MCP server for development...")
            try:
                # Load configuration
                from tidb_mcp_server.config import load_config
                config = load_config()
                
                # Initialize and start MCP server in background task
                asyncio.create_task(initialize_mcp_server_background(config))
                
                logger.info("MCP server background initialization started")
                
            except Exception as e:
                logger.error(f"Auto-initialization failed: {e}")
                logger.info("MCP server will need to be initialized manually via /admin/initialize")
        
        logger.info("TiDB MCP Server HTTP API started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start TiDB MCP Server HTTP API: {e}")
        raise
    
    yield
    
    # Shutdown
    if mcp_server:
        await mcp_server.shutdown()
        logger.info("TiDB MCP Server HTTP API stopped")


# Create FastAPI app
app = FastAPI(
    title="TiDB MCP Server HTTP API",
    description="HTTP API wrapper for TiDB MCP Server tools",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/admin/initialize")
async def initialize_mcp_tools():
    """Initialize MCP tools manually"""
    global mcp_server
    
    try:
        if mcp_server is None:
            # Load configuration
            config = ServerConfig()
            
            # Initialize MCP server
            mcp_server = UniversalMCPServer(config)
            
            # Initialize just the MCP server components without starting the full server
            await mcp_server._initialize_database_connection()
            await mcp_server._initialize_cache_manager()
            await mcp_server._initialize_rate_limiter()
            await mcp_server._initialize_database_components()
            await mcp_server._initialize_mcp_server()
            
            return {"status": "success", "message": "MCP tools initialized successfully"}
        else:
            return {"status": "already_initialized", "message": "MCP server already initialized"}
            
    except Exception as e:
        logger.error(f"Failed to initialize MCP tools: {e}")
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")


@app.get("/admin/status")
async def get_mcp_status():
    """Get MCP initialization status"""
    global mcp_server
    
    import tidb_mcp_server.mcp_tools as mcp_tools
    
    status = {
        "mcp_server_instance": mcp_server is not None,
        "mcp_tools_initialized": {
            "query_executor": getattr(mcp_tools, '_query_executor', None) is not None,
            "schema_inspector": getattr(mcp_tools, '_schema_inspector', None) is not None,
            "cache_manager": getattr(mcp_tools, '_cache_manager', None) is not None,
            "mcp_server": getattr(mcp_tools, '_mcp_server', None) is not None,
        }
    }
    
    return status


async def start_mcp_server():
    """Start the MCP server in background"""
    global mcp_server
    try:
        if mcp_server:
            await mcp_server.start()
    except Exception as e:
        logger.error(f"MCP server startup failed: {e}")


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


# LLM tool endpoints
@app.post("/tools/llm_generate_text_tool")
async def llm_generate_text_endpoint(request: GenerateTextRequest):
    """Generate text using LLM"""
    try:
        from . import llm_tools
        result = await llm_tools.generate_text_tool(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            use_cache=request.use_cache
        )
        return result
    except Exception as e:
        logger.error(f"llm_generate_text failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/llm_analyze_data_tool")
async def llm_analyze_data_endpoint(request: AnalyzeDataRequest):
    """Analyze data using LLM"""
    try:
        from . import llm_tools
        result = await llm_tools.analyze_data_tool(
            data=request.data,
            analysis_type=request.analysis_type,
            context=request.context
        )
        return result
    except Exception as e:
        logger.error(f"llm_analyze_data failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/llm_generate_sql_tool")
async def llm_generate_sql_endpoint(request: GenerateSQLRequest):
    """Generate SQL query from natural language"""
    try:
        from . import llm_tools
        result = await llm_tools.generate_sql_tool(
            natural_language_query=request.natural_language_query,
            schema_info=request.schema_info,
            examples=request.examples
        )
        return result
    except Exception as e:
        logger.error(f"llm_generate_sql failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/llm_explain_results_tool")
async def llm_explain_results_endpoint(request: ExplainResultsRequest):
    """Explain query results in natural language"""
    try:
        from . import llm_tools
        result = await llm_tools.explain_results_tool(
            query=request.query,
            results=request.results,
            context=request.context
        )
        return result
    except Exception as e:
        logger.error(f"llm_explain_results failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Additional endpoints for direct tool access

@app.get("/tools")
async def list_tools():
    """List all available MCP tools"""
    return {
        "database_tools": [
            "discover_databases_tool",
            "discover_tables_tool",
            "get_table_schema_tool",
            "get_sample_data_tool",
            "execute_query_tool",
            "validate_query_tool",
            "get_server_stats_tool",
            "clear_cache_tool"
        ],
        "llm_tools": [
            "llm_generate_text_tool",
            "llm_analyze_data_tool", 
            "llm_generate_sql_tool",
            "llm_explain_results_tool"
        ],
        "description": "Available MCP tools for database operations and LLM services"
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


# Additional API endpoints for frontend integration
@app.get("/api/suggestions")
async def get_query_suggestions():
    """Get query suggestions for the frontend"""
    try:
        # Return sample query suggestions
        suggestions = [
            {
                "id": "revenue_trend",
                "text": "Show me monthly revenue trends",
                "description": "Display revenue trends over the last 12 months",
                "category": "financial"
            },
            {
                "id": "top_customers",
                "text": "Who are our top 10 customers?",
                "description": "List customers by total revenue contribution",
                "category": "customer"
            },
            {
                "id": "profit_margin", 
                "text": "What's our current profit margin?",
                "description": "Calculate current profit margins by product/service",
                "category": "financial"
            },
            {
                "id": "sales_performance",
                "text": "Compare this quarter vs last quarter sales",
                "description": "Quarterly sales performance comparison",
                "category": "sales"
            }
        ]
        return {"suggestions": suggestions, "status": "success"}
    except Exception as e:
        logger.error(f"get_suggestions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/database/sample-data")
async def get_sample_data_api():
    """Get sample data for dashboard preview"""
    try:
        # Return sample financial data for dashboard
        sample_data = {
            "revenue_trends": [
                {"period": "2025-01", "revenue": 1200000, "profit": 240000},
                {"period": "2025-02", "revenue": 1350000, "profit": 280000},
                {"period": "2025-03", "revenue": 1180000, "profit": 220000},
                {"period": "2025-04", "revenue": 1420000, "profit": 310000},
                {"period": "2025-05", "revenue": 1380000, "profit": 295000}
            ],
            "top_customers": [
                {"name": "Enterprise Corp", "revenue": 450000, "contracts": 12},
                {"name": "Global Solutions", "revenue": 380000, "contracts": 8},
                {"name": "Tech Innovations", "revenue": 320000, "contracts": 15},
                {"name": "Digital Partners", "revenue": 280000, "contracts": 6}
            ],
            "metrics": {
                "total_revenue": 6530000,
                "total_profit": 1345000,
                "profit_margin": 20.6,
                "customer_count": 156,
                "avg_contract_value": 41860
            }
        }
        return {"data": sample_data, "status": "success"}
    except Exception as e:
        logger.error(f"get_sample_data_api failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
async def execute_query_api(request: ExecuteQueryRequest):
    """Execute query via API endpoint"""
    try:
        result = mcp_tools.execute_query(
            query=request.query,
            timeout=request.timeout,
            use_cache=request.use_cache
        )
        return result
    except Exception as e:
        logger.error(f"execute_query_api failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
