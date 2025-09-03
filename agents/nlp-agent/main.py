"""
NLP Agent with KIMI Integration
Main entry point for the NLP Agent service with HTTP API
"""

import asyncio
import logging
import os
import signal
import sys
import json
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
app = FastAPI(title="NLP Agent API", version="1.0.0")

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
    """Initialize NLP Agent on startup"""
    global nlp_agent
    
    logger.info("Starting NLP Agent...")
    
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
            redis_url=os.getenv('REDIS_URL', 'redis://redis:6379'),
            rabbitmq_url=os.getenv('RABBITMQ_URL', 'amqp://rabbitmq:5672')
        )
        
        await nlp_agent.start()
        logger.info("NLP Agent started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start NLP Agent: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup NLP Agent on shutdown"""
    global nlp_agent
    
    if nlp_agent:
        await nlp_agent.stop()
        logger.info("NLP Agent stopped")

@app.post("/process", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """Process natural language query and return SQL + context"""
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
        
        if not result.success:
            return QueryResponse(
                success=False,
                query_id=request.query_id,
                processing_time_ms=result.processing_time_ms,
                error=result.error_message
            )
        
        # Extract SQL query and context from the processed result
        query_context = result.query_context
        
        if not query_context or not query_context.intent:
            return QueryResponse(
                success=False,
                query_id=request.query_id,
                processing_time_ms=result.processing_time_ms,
                error="Failed to extract intent from query"
            )
        
        # Generate SQL query from intent using the schema knowledge
        sql_query = await generate_sql_from_intent(query_context.intent)
        
        # Build response
        response = QueryResponse(
            success=True,
            query_id=request.query_id,
            sql_query=sql_query,
            query_intent={
                "metric_type": query_context.intent.metric_type,
                "time_period": query_context.intent.time_period,
                "aggregation_level": query_context.intent.aggregation_level,
                "filters": query_context.intent.filters,
                "comparison_periods": query_context.intent.comparison_periods,
                "visualization_hint": query_context.intent.visualization_hint,
                "confidence_score": query_context.intent.confidence_score
            },
            query_context={
                "query_id": query_context.query_id,
                "original_query": query_context.original_query,
                "processed_query": query_context.processed_query,
                "entities": [entity.dict() for entity in query_context.entities] if query_context.entities else [],
                "ambiguities": query_context.ambiguities,
                "clarifications": query_context.clarifications,
                "schema_context": {
                    "tables": ["financial_overview", "cash_flow", "budget_tracking", "investments", "financial_ratios"],
                    "metrics": ["revenue", "profit", "expenses", "cash_flow", "roi"],
                    "time_periods": ["daily", "weekly", "monthly", "quarterly", "yearly"]
                }
            },
            processing_time_ms=result.processing_time_ms
        )
        
        logger.info(f"Successfully processed query {request.query_id} in {result.processing_time_ms}ms")
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

async def generate_sql_from_intent(intent) -> str:
    """Generate SQL query from query intent with schema knowledge"""
    
    # Map metric types to appropriate queries
    if intent.metric_type == "revenue":
        base_query = """
        SELECT 
            DATE_FORMAT(period_date, '%Y-%m') as period,
            SUM(revenue) as revenue
        FROM financial_overview 
        WHERE period_date >= '2025-01-01'
        GROUP BY DATE_FORMAT(period_date, '%Y-%m')
        ORDER BY period
        """
    elif intent.metric_type == "profit":
        base_query = """
        SELECT 
            DATE_FORMAT(period_date, '%Y-%m') as period,
            SUM(net_income) as profit
        FROM financial_overview 
        WHERE period_date >= '2025-01-01'
        GROUP BY DATE_FORMAT(period_date, '%Y-%m')
        ORDER BY period
        """
    elif intent.metric_type == "expenses":
        base_query = """
        SELECT 
            DATE_FORMAT(period_date, '%Y-%m') as period,
            SUM(total_expenses) as expenses
        FROM financial_overview 
        WHERE period_date >= '2025-01-01'
        GROUP BY DATE_FORMAT(period_date, '%Y-%m')
        ORDER BY period
        """
    elif intent.metric_type == "cash_flow":
        base_query = """
        SELECT 
            DATE_FORMAT(period_date, '%Y-%m') as period,
            SUM(operating_cash_flow) as operating_cash_flow,
            SUM(investing_cash_flow) as investing_cash_flow,
            SUM(financing_cash_flow) as financing_cash_flow,
            SUM(net_cash_flow) as net_cash_flow
        FROM cash_flow 
        WHERE period_date >= '2025-01-01'
        GROUP BY DATE_FORMAT(period_date, '%Y-%m')
        ORDER BY period
        """
    else:
        # Default to revenue
        base_query = """
        SELECT 
            DATE_FORMAT(period_date, '%Y-%m') as period,
            SUM(revenue) as revenue
        FROM financial_overview 
        WHERE period_date >= '2025-01-01'
        GROUP BY DATE_FORMAT(period_date, '%Y-%m')
        ORDER BY period
        """
    
    return base_query

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not nlp_agent:
        raise HTTPException(status_code=503, detail="NLP Agent not initialized")
    
    try:
        health_status = await nlp_agent.health_check()
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/status")
async def get_status():
    """Get agent status"""
    return {
        "agent_type": "nlp-agent",
        "status": "running" if nlp_agent and nlp_agent.is_running else "stopped",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )