"""
NLP Agent with MCP Server Integration
Main entry point for the NLP Agent service with HTTP API
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from src.nlp_agent import NLPAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic models
class QueryRequest(BaseModel):
    query: str
    query_id: str
    user_id: str
    session_id: str
    context: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    success: bool
    query_id: str
    sql_query: Optional[str] = None
    query_intent: Optional[Dict[str, Any]] = None
    query_context: Optional[Dict[str, Any]] = None
    processing_time_ms: int
    error: Optional[str] = None

# Global references
nlp_agent: Optional[NLPAgent] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown"""
    global nlp_agent
    
    # Startup
    logger.info("Starting NLP Agent with MCP Integration...")
    
    # Validate environment variables
    required_env_vars = ['KIMI_API_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        raise RuntimeError(f"Missing environment variables: {missing_vars}")
    
    try:
        # Initialize NLP Agent
        nlp_agent = NLPAgent(
            kimi_api_key=os.getenv('KIMI_API_KEY'),
            mcp_server_url=os.getenv('MCP_SERVER_URL', 'http://tidb-mcp-server:8000')
        )
        
        await nlp_agent.start()
        logger.info("NLP Agent started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start NLP Agent: {e}")
        raise
    
    yield
    
    # Shutdown
    if nlp_agent:
        await nlp_agent.stop()
        logger.info("NLP Agent stopped")

app = FastAPI(
    title="NLP Agent API", 
    version="2.0.0", 
    description="NLP Agent with MCP integration",
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

@app.post("/process", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """
    Process natural language query with MCP integration
    """
    if not nlp_agent:
        raise HTTPException(status_code=503, detail="NLP Agent not initialized")
    
    start_time = datetime.now()
    
    try:
        logger.info(f"Processing query {request.query_id}: {request.query}")
        
        # Process the query through the NLP agent
        result = await nlp_agent.process_query(
            query=request.query,
            user_id=request.user_id,
            session_id=request.session_id,
            context=request.context
        )
        
        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        result.processing_time_ms = processing_time
        
        if not result.success:
            return QueryResponse(
                success=False,
                query_id=request.query_id,
                processing_time_ms=processing_time,
                error=result.error
            )
        
        # Build response
        response = QueryResponse(
            success=True,
            query_id=request.query_id,
            sql_query=result.sql_query,
            query_intent={
                "metric_type": result.intent.metric_type if result.intent else "unknown",
                "time_period": result.intent.time_period if result.intent else "unknown",
                "aggregation_level": result.intent.aggregation_level if result.intent else "monthly",
                "filters": result.intent.filters if result.intent else {},
                "comparison_periods": result.intent.comparison_periods if result.intent else [],
                "visualization_hint": result.intent.visualization_hint if result.intent else "bar",
                "confidence_score": result.intent.confidence_score if result.intent else 0.5
            },
            query_context=result.query_context,
            processing_time_ms=processing_time
        )
        
        logger.info(f"Successfully processed query {request.query_id} in {processing_time}ms")
        return response
        
    except Exception as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.error(f"Query processing failed for {request.query_id}: {e}")
        
        return QueryResponse(
            success=False,
            query_id=request.query_id,
            processing_time_ms=processing_time,
            error=str(e)
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global nlp_agent
    
    if not nlp_agent:
        raise HTTPException(status_code=503, detail="NLP Agent not initialized")
    
    try:
        # Get health status from NLP agent
        health_status = await nlp_agent.health_check()
        
        return {
            "agent_type": "nlp-agent",
            "version": "2.0.0",
            "architecture": "mcp-integrated",
            "health_status": health_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/status")
async def get_status():
    """Get agent status"""
    return {
        "agent_type": "nlp-agent",
        "status": "running" if nlp_agent and nlp_agent.is_running else "stopped",
        "architecture": "mcp-integrated",
        "capabilities": [
            "Natural language parsing with KIMI",
            "Intent extraction and entity recognition", 
            "Context building for other agents",
            "MCP server communication"
        ],
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("\n🎯 NLP Agent with MCP Integration")
    print("=" * 40)
    print("Starting NLP Agent server...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
