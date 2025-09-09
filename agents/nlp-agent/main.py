"""
NLP Agent with KIMI Integration and Dynamic Schema Management
Main entry point for the NLP Agent service with HTTP API
"""

import asyncio
import logging
import os
import signal
import sys
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from src.nlp_agent import NLPAgent

# Import dynamic schema management components
# Backend modules are now copied into container
try:
    from schema_management.dynamic_schema_manager import get_dynamic_schema_manager
    from schema_management.intelligent_query_builder import get_intelligent_query_builder
    SCHEMA_MANAGEMENT_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Schema management modules not available: {e}")
    SCHEMA_MANAGEMENT_AVAILABLE = False
    
    # Create dummy functions for fallback
    async def get_dynamic_schema_manager():
        return None
    
    async def get_intelligent_query_builder(manager):
        return None

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
dynamic_schema_manager = None
intelligent_query_builder = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown"""
    global nlp_agent, dynamic_schema_manager, intelligent_query_builder
    
    # Startup
    logger.info("Starting NLP Agent with Dynamic Schema Management...")
    
    # Validate environment variables
    required_env_vars = ['KIMI_API_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        raise RuntimeError(f"Missing environment variables: {missing_vars}")
    
    try:
        # Initialize Dynamic Schema Management
        try:
            dynamic_schema_manager = await get_dynamic_schema_manager()
            intelligent_query_builder = await get_intelligent_query_builder(dynamic_schema_manager)
            logger.info("Dynamic Schema Management initialized successfully")
        except Exception as schema_error:
            logger.warning(f"Failed to initialize dynamic schema management: {schema_error}")
            logger.info("Will use fallback mode for SQL generation")
        
        # Initialize NLP Agent
        nlp_agent = NLPAgent(
            kimi_api_key=os.getenv('KIMI_API_KEY'),
            redis_url=os.getenv('REDIS_URL', 'redis://redis:6379'),
            # rabbitmq_url=os.getenv("RABBITMQ_URL", "amqp://rabbitmq:5672")')
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

app = FastAPI(title="NLP Agent API", version="1.0.0", lifespan=lifespan)

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
        
        # Generate SQL query from intent using dynamic schema management
        sql_query = await generate_sql_from_intent_dynamic(query_context.intent)
        
        # Get dynamic schema context
        schema_context = await get_dynamic_schema_context()
        
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
                "schema_context": schema_context
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

async def get_dynamic_schema_context() -> Dict[str, Any]:
    """
    Get dynamic schema context from the schema manager.
    
    Returns:
        Dictionary containing tables, metrics, and time periods discovered from schema
    """
    global dynamic_schema_manager
    
    try:
        if dynamic_schema_manager:
            # Get current schema information using fast mode for quicker response
            schema_info = await dynamic_schema_manager.discover_schema(fast_mode=True)
            
            if schema_info and schema_info.databases:
                # Extract table names and metrics
                tables = []
                metrics = set()
                time_periods = ["daily", "weekly", "monthly", "quarterly", "yearly"]  # Standard periods
                
                for db_name, db_info in schema_info.databases.items():
                    for table_name, table_info in db_info.tables.items():
                        tables.append(table_name)
                        
                        # Extract potential metrics from column names
                        for column in table_info.columns:
                            column_name = column.name.lower()
                            # Common financial metrics
                            if any(metric in column_name for metric in [
                                'revenue', 'profit', 'income', 'expense', 'cost', 'cash', 'flow',
                                'roi', 'margin', 'sales', 'amount', 'value', 'total', 'balance'
                            ]):
                                metrics.add(column_name)
                
                logger.info(f"Dynamic schema context discovered: {len(tables)} tables, {len(metrics)} metrics")
                return {
                    "tables": sorted(tables),
                    "metrics": sorted(list(metrics)),
                    "time_periods": time_periods,
                    "schema_source": "dynamic_discovery",
                    "last_updated": datetime.now().isoformat()
                }
        
        # Fallback to static schema context
        logger.warning("Using fallback static schema context")
        return {
            "tables": ["financial_overview", "cash_flow", "budget_tracking", "investments", "financial_ratios"],
            "metrics": ["revenue", "profit", "expenses", "cash_flow", "roi"],
            "time_periods": ["daily", "weekly", "monthly", "quarterly", "yearly"],
            "schema_source": "static_fallback",
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dynamic schema context: {e}")
        # Return minimal fallback context
        return {
            "tables": [],
            "metrics": [],
            "time_periods": ["daily", "weekly", "monthly", "quarterly", "yearly"],
            "schema_source": "error_fallback",
            "error": str(e),
            "last_updated": datetime.now().isoformat()
        }

async def generate_sql_from_intent_dynamic(intent) -> str:
    """
    Generate SQL query from query intent using dynamic schema management.
    
    This function replaces hardcoded SQL templates with dynamic query generation
    based on real-time schema discovery and semantic mappings.
    """
    global dynamic_schema_manager, intelligent_query_builder
    
    try:
        # Convert intent to dict format if needed
        intent_dict = {
            'metric_type': getattr(intent, 'metric_type', 'revenue'),
            'time_period': getattr(intent, 'time_period', 'this_year'),
            'aggregation_level': getattr(intent, 'aggregation_level', 'monthly'),
            'filters': getattr(intent, 'filters', {}),
            'comparison_periods': getattr(intent, 'comparison_periods', []),
            'limit': getattr(intent, 'limit', 1000)
        }
        
        # Use dynamic schema management if available
        if intelligent_query_builder and dynamic_schema_manager:
            logger.info(f"Using dynamic schema management for metric: {intent_dict['metric_type']}")
            
            # Check if we have schema mappings for this metric
            table_mappings = await dynamic_schema_manager.find_tables_for_metric(intent_dict['metric_type'])
            
            if table_mappings:
                # Generate query using intelligent query builder
                query_result = await intelligent_query_builder.build_query(intent_dict)
                
                logger.info(
                    f"Dynamic query generated successfully for {intent_dict['metric_type']} "
                    f"with confidence: {query_result.confidence_score:.2f}"
                )
                
                return query_result.sql
            else:
                # No mappings found, suggest alternatives
                alternatives = await dynamic_schema_manager.suggest_alternatives(intent_dict['metric_type'])
                logger.warning(
                    f"No schema mappings found for '{intent_dict['metric_type']}'. "
                    f"Suggested alternatives: {alternatives}"
                )
                
                # Fall back to static generation with the first alternative
                if alternatives:
                    intent_dict['metric_type'] = alternatives[0]
                    return await generate_sql_from_intent_fallback(intent_dict)
        
        # Fallback to static SQL generation
        logger.info(f"Using fallback SQL generation for metric: {intent_dict['metric_type']}")
        return await generate_sql_from_intent_fallback(intent_dict)
        
    except Exception as e:
        logger.error(f"Error in dynamic SQL generation: {e}")
        # Final fallback to basic static query
        return await generate_sql_from_intent_fallback(intent_dict)


async def generate_sql_from_intent_fallback(intent_dict: Dict[str, Any]) -> str:
    """
    Fallback SQL generation using static templates.
    
    This provides backward compatibility when dynamic schema management fails.
    """
    metric_type = intent_dict.get('metric_type', 'revenue')
    
    # Static SQL templates for fallback
    if metric_type == "revenue":
        base_query = """
        SELECT 
            DATE_FORMAT(period_date, '%Y-%m') as period,
            SUM(revenue) as revenue
        FROM financial_overview 
        WHERE period_date >= '2025-01-01'
        GROUP BY DATE_FORMAT(period_date, '%Y-%m')
        ORDER BY period
        """
    elif metric_type == "profit":
        base_query = """
        SELECT 
            DATE_FORMAT(period_date, '%Y-%m') as period,
            SUM(net_income) as profit
        FROM financial_overview 
        WHERE period_date >= '2025-01-01'
        GROUP BY DATE_FORMAT(period_date, '%Y-%m')
        ORDER BY period
        """
    elif metric_type == "expenses":
        base_query = """
        SELECT 
            DATE_FORMAT(period_date, '%Y-%m') as period,
            SUM(total_expenses) as expenses
        FROM financial_overview 
        WHERE period_date >= '2025-01-01'
        GROUP BY DATE_FORMAT(period_date, '%Y-%m')
        ORDER BY period
        """
    elif metric_type == "cash_flow":
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


async def generate_sql_from_intent(intent) -> str:
    """Legacy function for backward compatibility - redirects to dynamic version."""
    return await generate_sql_from_intent_dynamic(intent)

@app.get("/health")
async def health_check():
    """Health check endpoint with dynamic schema management status"""
    global nlp_agent, dynamic_schema_manager, intelligent_query_builder
    
    if not nlp_agent:
        raise HTTPException(status_code=503, detail="NLP Agent not initialized")
    
    try:
        # Check NLP agent health
        health_status = await nlp_agent.health_check()
        
        # Add dynamic schema management status
        schema_status = {
            "dynamic_schema_manager": "available" if dynamic_schema_manager else "unavailable",
            "intelligent_query_builder": "available" if intelligent_query_builder else "unavailable",
            "fallback_mode": not (dynamic_schema_manager and intelligent_query_builder)
        }
        
        # Get schema manager metrics if available
        if dynamic_schema_manager:
            try:
                schema_metrics = dynamic_schema_manager.get_metrics()
                schema_status["schema_metrics"] = schema_metrics
            except Exception as e:
                schema_status["schema_metrics_error"] = str(e)
        
        # Get query builder metrics if available
        if intelligent_query_builder:
            try:
                builder_metrics = intelligent_query_builder.get_metrics()
                schema_status["query_builder_metrics"] = builder_metrics
            except Exception as e:
                schema_status["query_builder_metrics_error"] = str(e)
        
        # Test dynamic schema context function
        try:
            test_schema_context = await get_dynamic_schema_context()
            schema_status["schema_context_test"] = {
                "success": True,
                "source": test_schema_context.get("schema_source", "unknown"),
                "tables_count": len(test_schema_context.get("tables", [])),
                "metrics_count": len(test_schema_context.get("metrics", [])),
                "sample_tables": test_schema_context.get("tables", [])[:3],  # First 3 tables
                "sample_metrics": test_schema_context.get("metrics", [])[:3]  # First 3 metrics
            }
        except Exception as e:
            schema_status["schema_context_test"] = {
                "success": False,
                "error": str(e)
            }
        
        health_status["dynamic_schema_management"] = schema_status
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/test-schema-context")
async def test_schema_context():
    """Test endpoint to verify dynamic schema context works"""
    try:
        schema_context = await get_dynamic_schema_context()
        return {
            "success": True,
            "schema_context": schema_context,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

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