"""
Data Agent with TiDB Integration
Main entry point for the Data Agent service with HTTP API
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

import structlog
from src.agent import get_data_agent, close_data_agent
from src.mcp_agent import get_mcp_data_agent, close_mcp_data_agent

# Load environment variables
load_dotenv()

# Check if MCP mode is enabled
USE_MCP = os.getenv('USE_MCP_CLIENT', 'true').lower() == 'true'

# Load environment variables
load_dotenv()

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = logging.getLogger(__name__)

# Pydantic models
class QueryExecuteRequest(BaseModel):
    sql_query: str
    query_context: Dict[str, Any]
    query_id: str
    execution_config: Optional[Dict[str, Any]] = None

class QueryExecuteResponse(BaseModel):
    success: bool
    query_id: str
    processed_data: list
    columns: list
    row_count: int
    processing_time_ms: int
    error: Optional[str] = None
    data_quality: Optional[Dict[str, Any]] = None

# Global references
data_agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    global data_agent
    
    # Startup
    logger.info(f"Starting Data Agent (MCP mode: {USE_MCP})...")
    
    try:
        # Initialize Data Agent (MCP or direct mode)
        if USE_MCP:
            data_agent = await get_mcp_data_agent()
            logger.info("Data Agent started successfully with MCP integration")
        else:
            data_agent = await get_data_agent()
            logger.info("Data Agent started successfully with direct database integration")
        
    except Exception as e:
        logger.error(f"Failed to start Data Agent: {e}")
        raise
    
    yield
    
    # Shutdown
    if data_agent:
        if USE_MCP:
            await close_mcp_data_agent()
        else:
            await close_data_agent()
        logger.info("Data Agent stopped")

app = FastAPI(title="Data Agent API", version="1.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/execute", response_model=QueryExecuteResponse)
async def execute_query(request: QueryExecuteRequest) -> QueryExecuteResponse:
    """Execute SQL query and return processed data"""
    if not data_agent:
        raise HTTPException(status_code=503, detail="Data Agent not initialized")
    
    start_time = datetime.now()
    
    try:
        logger.info(f"Executing query {request.query_id}")
        
        # Convert query context to intent format expected by data agent
        query_intent = {
            "metric_type": request.query_context.get("metric_type", "revenue"),
            "time_period": request.query_context.get("time_period", "monthly"),
            "aggregation_level": request.query_context.get("aggregation_level", "monthly"),
            "filters": request.query_context.get("filters", {}),
            "comparison_periods": request.query_context.get("comparison_periods", [])
        }
        
        # Process query through the data agent
        result = await data_agent.process_query(query_intent, user_context={
            "query_id": request.query_id,
            "sql_query": request.sql_query
        })
        
        if not result.get("success", False):
            return QueryExecuteResponse(
                success=False,
                query_id=request.query_id,
                processed_data=[],
                columns=[],
                row_count=0,
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=result.get("error", {}).get("message", "Unknown error")
            )
        
        # Build response
        response = QueryExecuteResponse(
            success=True,
            query_id=request.query_id,
            processed_data=result.get("data", []),
            columns=result.get("columns", []),
            row_count=result.get("row_count", 0),
            processing_time_ms=result.get("metadata", {}).get("processing_time_ms", 0),
            data_quality=result.get("metadata", {}).get("data_quality", {})
        )
        
        logger.info(f"Successfully executed query {request.query_id} in {response.processing_time_ms}ms")
        return response
        
    except Exception as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.error(f"Query execution failed for {request.query_id}: {e}")
        
        return QueryExecuteResponse(
            success=False,
            query_id=request.query_id,
            processed_data=[],
            columns=[],
            row_count=0,
            processing_time_ms=processing_time,
            error=str(e)
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not data_agent:
        raise HTTPException(status_code=503, detail="Data Agent not initialized")
    
    try:
        health_status = await data_agent.health_check()
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/status")
async def get_status():
    """Get agent status"""
    return {
        "agent_type": "data-agent",
        "status": "running" if data_agent and data_agent.is_initialized else "stopped",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/metrics")
async def get_metrics():
    """Get agent metrics"""
    if not data_agent:
        raise HTTPException(status_code=503, detail="Data Agent not initialized")
    
    try:
        metrics = await data_agent.get_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_level="info"
    )