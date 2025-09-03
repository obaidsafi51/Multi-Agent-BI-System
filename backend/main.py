"""
AI CFO Backend - FastAPI Gateway with WebSocket Support
Main FastAPI application with async endpoints, WebSocket handlers, and authentication.
"""

import os
import logging
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect,
    Request, Response, status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from dotenv import load_dotenv
import redis.asyncio as redis
import httpx

from models.core import QueryIntent, QueryResult, ErrorResponse
from models.ui import BentoGridLayout, BentoGridCard
from models.user import UserProfile, PersonalizationRecommendation, QueryHistoryEntry

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Global connections
redis_client: Optional[redis.Redis] = None
websocket_connections: Dict[str, WebSocket] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown"""
    # Startup
    await startup_event()
    yield
    # Shutdown
    await shutdown_event()


app = FastAPI(
    title="AI CFO Backend",
    description="FastAPI Gateway for AI CFO BI Agent with WebSocket Support",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "frontend", "backend", "testserver"]
)

# Rate limit exceeded handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


async def startup_event():
    """Initialize connections and validate environment on startup"""
    global redis_client
    
    # Initialize Redis connection
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        redis_client = None
    
    # Validate environment variables
    required_vars = ['TIDB_HOST', 'TIDB_USER', 'TIDB_PASSWORD', 'TIDB_DATABASE']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(f"Missing required environment variables: {missing_vars}")
    else:
        logger.info("All required environment variables are present")
    
    logger.info("Backend started successfully")


async def shutdown_event():
    """Clean up connections on shutdown"""
    global redis_client
    
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")
    
    # Close all WebSocket connections
    for connection in websocket_connections.values():
        try:
            await connection.close()
        except Exception:
            pass
    
    logger.info("Backend shutdown complete")


# Pydantic models for API requests/responses
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    query_id: str
    intent: QueryIntent
    result: Optional[QueryResult] = None
    visualization: Optional[Dict[str, Any]] = None
    error: Optional[ErrorResponse] = None
    agent_performance: Optional[Dict[str, Any]] = None

class FeedbackRequest(BaseModel):
    query_id: str
    rating: int  # 1-5
    feedback_text: Optional[str] = None

class QueryHistoryEntry(BaseModel):
    query_id: str
    user_id: str
    query_text: str
    query_intent: Dict[str, Any]
    response_data: Dict[str, Any]
    processing_time_ms: int
    agent_workflow: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI CFO Backend API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "api_docs": "/docs",
            "websocket": "/ws/chat/{user_id}"
        }
    }


@app.get("/favicon.ico")
async def favicon():
    """Favicon endpoint"""
    return Response(
        content="",
        status_code=204,
        media_type="image/x-icon"
    )


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        health_status = {
            "status": "healthy",
            "service": "backend",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "redis": "unknown",
                "database": "unknown"
            }
        }
        
        # Check Redis
        if redis_client:
            try:
                await redis_client.ping()
                health_status["services"]["redis"] = "healthy"
            except Exception:
                health_status["services"]["redis"] = "unhealthy"
        
        # Check Database
        try:
            from database.connection import get_database
            db = get_database()
            if db.health_check():
                health_status["services"]["database"] = "healthy"
            else:
                health_status["services"]["database"] = "unhealthy"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_status["services"]["database"] = "unhealthy"
        
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.post("/api/query", response_model=QueryResponse)
@limiter.limit("30/minute")
async def process_query(
    request: Request,
    query_request: QueryRequest
):
    """Process natural language query through multi-agent workflow"""
    try:
        query_id = f"q_{datetime.utcnow().timestamp()}"
        logger.info(f"Starting multi-agent workflow for query: {query_request.query}")
        
        # Step 1: Send query to NLP Agent
        nlp_result = await send_to_nlp_agent(query_request.query, query_id)
        if not nlp_result.get("success", False):
            raise HTTPException(status_code=400, detail=f"NLP processing failed: {nlp_result.get('error', 'Unknown error')}")
        
        # Step 2: Send SQL context to Data Agent
        data_result = await send_to_data_agent(nlp_result["sql_query"], nlp_result["query_context"], query_id)
        if not data_result.get("success", False):
            raise HTTPException(status_code=500, detail=f"Data processing failed: {data_result.get('error', 'Unknown error')}")
        
        # Step 3: Send data and context to Viz Agent
        viz_result = await send_to_viz_agent(data_result["processed_data"], nlp_result["query_context"], query_id)
        if not viz_result.get("success", False):
            logger.warning(f"Visualization failed, using default: {viz_result.get('error')}")
            # Continue with basic visualization
            viz_result = create_default_visualization(data_result["processed_data"])
        
        # Step 4: Combine results
        query_intent = QueryIntent(**nlp_result["query_intent"])
        query_result = QueryResult(
            data=data_result["processed_data"],
            columns=data_result["columns"],
            row_count=len(data_result["processed_data"]),
            processing_time_ms=data_result.get("processing_time_ms", 250)
        )
        
        # Store query in history (Redis)
        if redis_client:
            query_history = QueryHistoryEntry(
                query_id=query_id,
                user_id="anonymous",
                query_text=query_request.query,
                query_intent=query_intent.dict(),
                response_data=query_result.dict(),
                processing_time_ms=query_result.processing_time_ms,
                agent_workflow={
                    "nlp_agent": nlp_result.get("processing_time_ms", 0),
                    "data_agent": data_result.get("processing_time_ms", 0),
                    "viz_agent": viz_result.get("processing_time_ms", 0)
                }
            )
            await redis_client.setex(
                f"query_history:{query_id}",
                3600,
                json.dumps(query_history.dict(), default=str)
            )
        
        # Create response with visualization
        response = QueryResponse(
            query_id=query_id,
            intent=query_intent,
            result=query_result,
            visualization=viz_result.get("chart_config", {
                "chart_type": "table",
                "title": "Financial Data",
                "config": {"responsive": True}
            }),
            agent_performance={
                "nlp_processing_ms": nlp_result.get("processing_time_ms", 0),
                "data_processing_ms": data_result.get("processing_time_ms", 0),
                "viz_processing_ms": viz_result.get("processing_time_ms", 0),
                "total_processing_ms": (
                    nlp_result.get("processing_time_ms", 0) +
                    data_result.get("processing_time_ms", 0) +
                    viz_result.get("processing_time_ms", 0)
                )
            }
        )
        
        logger.info(f"Multi-agent workflow completed for query {query_id}")
        return response
        
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        return QueryResponse(
            query_id=query_id,
            intent=QueryIntent(metric_type="unknown", time_period="unknown"),
            error=ErrorResponse(
                error_type="processing_error",
                message="Failed to process query",
                recovery_action="retry",
                suggestions=["Try rephrasing your query", "Check your connection"]
            )
        )


@app.get("/api/database/sample-data")
@limiter.limit("30/minute")
async def get_sample_database_data(request: Request):
    """Get sample data from different tables to verify database functionality"""
    try:
        from database.connection import get_database
        db = get_database()
        
        sample_data = {
            "connection_status": "healthy" if db.health_check() else "unhealthy",
            "database_info": {
                "name": "Agentic_BI",
                "type": "TiDB Cloud"
            },
            "tables": {}
        }
        
        # Get sample data from each table
        tables_to_sample = [
            ("financial_overview", "SELECT * FROM financial_overview LIMIT 2"),
            ("departments", "SELECT * FROM departments LIMIT 5"),
            ("investments", "SELECT * FROM investments WHERE status = 'active' LIMIT 2"),
            ("cash_flow", "SELECT * FROM cash_flow ORDER BY period_date DESC LIMIT 2"),
            ("budget_tracking", "SELECT * FROM budget_tracking LIMIT 2")
        ]
        
        for table_name, query in tables_to_sample:
            try:
                # Get sample data
                data = db.execute_query(query)
                
                # Get record count
                count_result = db.execute_query(f"SELECT COUNT(*) as count FROM {table_name}", fetch_one=True)
                total_count = count_result['count'] if count_result else 0
                
                sample_data["tables"][table_name] = {
                    "total_records": total_count,
                    "sample_data": data if data else [],
                    "sample_count": len(data) if data else 0
                }
                
            except Exception as e:
                sample_data["tables"][table_name] = {
                    "error": str(e),
                    "total_records": 0,
                    "sample_data": [],
                    "sample_count": 0
                }
        
        return sample_data
        
    except Exception as e:
        logger.error(f"Database sample data query failed: {e}")
        return {
            "connection_status": "error",
            "error": str(e),
            "database_info": {},
            "tables": {}
        }


@app.get("/api/database/test")
@limiter.limit("30/minute")
async def test_database(request: Request):
    """Test database connectivity and get detailed information"""
    try:
        from database.connection import get_database
        db = get_database()
        
        # Get database information
        db_info = db.get_database_info()
        
        # Test basic queries
        test_results = {
            "connection_status": "healthy" if db.health_check() else "unhealthy",
            "database_info": db_info,
            "test_queries": {}
        }
        
        # Test basic SELECT query
        try:
            version_result = db.execute_query("SELECT VERSION() as version", fetch_one=True)
            test_results["test_queries"]["version_query"] = {
                "status": "success",
                "result": version_result
            }
        except Exception as e:
            test_results["test_queries"]["version_query"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Test SHOW DATABASES
        try:
            databases_result = db.execute_query("SHOW DATABASES")
            test_results["test_queries"]["show_databases"] = {
                "status": "success",
                "result": databases_result,
                "count": len(databases_result) if databases_result else 0
            }
        except Exception as e:
            test_results["test_queries"]["show_databases"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Test current database and tables
        try:
            current_db = db.execute_query("SELECT DATABASE() as current_db", fetch_one=True)
            test_results["test_queries"]["current_database"] = {
                "status": "success",
                "result": current_db
            }
            
            # If we have a current database, show tables
            if current_db and current_db.get("current_db"):
                tables_result = db.execute_query("SHOW TABLES")
                test_results["test_queries"]["show_tables"] = {
                    "status": "success",
                    "result": tables_result,
                    "count": len(tables_result) if tables_result else 0
                }
        except Exception as e:
            test_results["test_queries"]["current_database"] = {
                "status": "error",
                "error": str(e)
            }
        
        return test_results
        
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return {
            "connection_status": "error",
            "error": str(e),
            "database_info": {},
            "test_queries": {}
        }


@app.get("/api/suggestions", response_model=List[str])
@limiter.limit("60/minute")
async def get_suggestions(request: Request):
    """Get personalized query suggestions for user"""
    try:
        # TODO: Integrate with Personalization Agent
        # For now, return mock suggestions
        suggestions = [
            "Show me quarterly revenue comparison",
            "What's our current cash flow status?",
            "Display budget variance for this month",
            "How are our investments performing?",
            "Show profit margins by department"
        ]
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}")
        return []


@app.get("/api/dashboard/{layout_id}", response_model=BentoGridLayout)
@limiter.limit("60/minute")
async def get_dashboard_layout(
    request: Request,
    layout_id: str
):
    """Get dashboard layout configuration"""
    try:
        # TODO: Retrieve from database
        # For now, return mock layout
        mock_layout = BentoGridLayout(
            layout_id=layout_id,
            user_id="anonymous",
            layout_name="Executive Dashboard",
            grid_columns=6,
            cards=[
                BentoGridCard(
                    id="revenue_kpi",
                    card_type="kpi",
                    size="1x1",
                    position={"row": 0, "col": 0},
                    title="Monthly Revenue",
                    content={
                        "value": 1250000,
                        "currency": "USD",
                        "change_percent": 12.5,
                        "trend": "up"
                    }
                )
            ]
        )
        
        return mock_layout
        
    except Exception as e:
        logger.error(f"Failed to get dashboard layout: {e}")
        raise HTTPException(status_code=404, detail="Dashboard layout not found")


@app.post("/api/dashboard/{layout_id}")
@limiter.limit("30/minute")
async def save_dashboard_layout(
    request: Request,
    layout_id: str,
    layout: BentoGridLayout
):
    """Save dashboard layout configuration"""
    try:
        # Set user_id to anonymous since no authentication
        layout.user_id = "anonymous"
        
        # TODO: Save to database
        # For now, store in Redis
        if redis_client:
            await redis_client.setex(
                f"dashboard_layout:{layout_id}",
                86400,  # 24 hours
                json.dumps(layout.dict(), default=str)
            )
        
        return {"message": "Dashboard layout saved successfully"}
        
    except Exception as e:
        logger.error(f"Failed to save dashboard layout: {e}")
        raise HTTPException(status_code=500, detail="Failed to save layout")


@app.post("/api/feedback")
@limiter.limit("60/minute")
async def submit_feedback(
    request: Request,
    feedback: FeedbackRequest
):
    """Submit user feedback for query results"""
    try:
        # TODO: Store feedback for machine learning
        # For now, store in Redis
        if redis_client:
            feedback_data = {
                "query_id": feedback.query_id,
                "user_id": "anonymous",
                "rating": feedback.rating,
                "feedback_text": feedback.feedback_text,
                "timestamp": datetime.utcnow().isoformat()
            }
            await redis_client.setex(
                f"feedback:{feedback.query_id}",
                86400,  # 24 hours
                json.dumps(feedback_data)
            )
        
        return {"message": "Feedback submitted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


@app.get("/api/profile", response_model=UserProfile)
@limiter.limit("60/minute")
async def get_user_profile(request: Request):
    """Get user profile and preferences"""
    try:
        # TODO: Retrieve from database
        # For now, return mock profile
        mock_profile = UserProfile(
            user_id="anonymous",
            chart_preferences={
                "revenue": "line_chart",
                "expenses": "bar_chart",
                "ratios": "gauge_chart"
            },
            color_scheme="corporate",
            expertise_level="advanced"
        )
        
        return mock_profile
        
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to get profile")


# WebSocket endpoint for real-time chat
@app.websocket("/ws/chat/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time chat communication"""
    await websocket.accept()
    websocket_connections[user_id] = websocket
    
    try:
        logger.info(f"WebSocket connection established for user: {user_id}")
        
        # Send welcome message
        await websocket.send_json({
            "type": "system",
            "message": "Connected to AI CFO Assistant",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type", "query")
            
            if message_type == "query":
                # Process query and send response
                query_text = data.get("message", "")
                
                # TODO: Integrate with agent system for actual processing
                # For now, send mock response
                response = {
                    "type": "response",
                    "query_id": f"ws_{datetime.utcnow().timestamp()}",
                    "message": f"Processing query: {query_text}",
                    "data": {
                        "chart_type": "line_chart",
                        "values": [100, 120, 110, 130, 125]
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await websocket.send_json(response)
                
            elif message_type == "ping":
                # Respond to ping with pong
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user: {user_id}")
        if user_id in websocket_connections:
            del websocket_connections[user_id]
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        if user_id in websocket_connections:
            del websocket_connections[user_id]


# Error handlers


# Helper functions for query processing
# Agent Communication Functions
async def send_to_nlp_agent(query: str, query_id: str) -> dict:
    """Send query to NLP Agent for processing"""
    try:
        # For now, we'll make HTTP requests to the agent services
        # In production, this would use MCP/A2A protocols
        
        nlp_agent_url = os.getenv("NLP_AGENT_URL", "http://nlp-agent:8001")
        
        payload = {
            "query": query,
            "query_id": query_id,
            "user_id": "anonymous",
            "session_id": f"session_{query_id}",
            "context": {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "backend_api"
            }
        }
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{nlp_agent_url}/process", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"NLP Agent processed query {query_id} successfully")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"NLP Agent error {response.status}: {error_text}")
                    return {"success": False, "error": f"NLP Agent returned {response.status}: {error_text}"}
                    
    except asyncio.TimeoutError:
        logger.error(f"NLP Agent timeout for query {query_id}")
        return {"success": False, "error": "NLP Agent timeout"}
    except Exception as e:
        logger.error(f"NLP Agent communication failed: {e}")
        # Fallback to simple query processing
        return await fallback_nlp_processing(query, query_id)


async def send_to_data_agent(sql_query: str, query_context: dict, query_id: str) -> dict:
    """Send SQL query to Data Agent for execution"""
    try:
        data_agent_url = os.getenv("DATA_AGENT_URL", "http://data-agent:8002")
        
        payload = {
            "sql_query": sql_query,
            "query_context": query_context,
            "query_id": query_id,
            "execution_config": {
                "use_cache": True,
                "validate_result": True,
                "optimize_query": True
            }
        }
        
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{data_agent_url}/execute", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Data Agent processed query {query_id} successfully")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Data Agent error {response.status}: {error_text}")
                    return {"success": False, "error": f"Data Agent returned {response.status}: {error_text}"}
                    
    except asyncio.TimeoutError:
        logger.error(f"Data Agent timeout for query {query_id}")
        return {"success": False, "error": "Data Agent timeout"}
    except Exception as e:
        logger.error(f"Data Agent communication failed: {e}")
        # Fallback to direct database query
        return await fallback_data_processing(sql_query, query_context, query_id)


async def send_to_viz_agent(data: list, query_context: dict, query_id: str) -> dict:
    """Send data to Visualization Agent for chart generation"""
    try:
        viz_agent_url = os.getenv("VIZ_AGENT_URL", "http://viz-agent:8003")
        
        payload = {
            "data": data,
            "query_context": query_context,
            "query_id": query_id,
            "visualization_config": {
                "auto_select_chart_type": True,
                "enable_interactions": True,
                "color_scheme": "corporate",
                "responsive": True
            }
        }
        
        timeout = aiohttp.ClientTimeout(total=45)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{viz_agent_url}/visualize", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Viz Agent processed query {query_id} successfully")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Viz Agent error {response.status}: {error_text}")
                    return {"success": False, "error": f"Viz Agent returned {response.status}: {error_text}"}
                    
    except asyncio.TimeoutError:
        logger.error(f"Viz Agent timeout for query {query_id}")
        return {"success": False, "error": "Viz Agent timeout"}
    except Exception as e:
        logger.error(f"Viz Agent communication failed: {e}")
        return {"success": False, "error": f"Viz Agent communication failed: {str(e)}"}


# Fallback Functions for Agent Communication Failures
async def fallback_nlp_processing(query: str, query_id: str) -> dict:
    """Fallback NLP processing when agent is unavailable"""
    logger.warning(f"Using fallback NLP processing for query {query_id}")
    
    # Simple intent extraction
    query_lower = query.lower()
    
    # Determine metric type
    if any(word in query_lower for word in ["revenue", "sales", "income"]):
        metric_type = "revenue"
    elif any(word in query_lower for word in ["profit", "earnings", "net"]):
        metric_type = "profit"
    elif any(word in query_lower for word in ["expense", "cost", "spending"]):
        metric_type = "expenses"
    elif any(word in query_lower for word in ["cash", "flow"]):
        metric_type = "cash_flow"
    else:
        metric_type = "revenue"  # default
    
    # Determine time period
    if any(word in query_lower for word in ["month", "monthly"]):
        aggregation = "monthly"
        time_period = "monthly"
    elif any(word in query_lower for word in ["quarter", "quarterly", "q1", "q2", "q3", "q4"]):
        aggregation = "quarterly"
        time_period = "quarterly"
    elif any(word in query_lower for word in ["year", "yearly", "annual"]):
        aggregation = "yearly"
        time_period = "yearly"
    else:
        aggregation = "monthly"
        time_period = "monthly"
    
    # Generate simple SQL query
    sql_query = f"""
    SELECT 
        DATE_FORMAT(period_date, '%Y-%m') as period,
        SUM({metric_type}) as {metric_type}
    FROM financial_overview 
    WHERE period_date >= '2025-01-01'
    GROUP BY DATE_FORMAT(period_date, '%Y-%m')
    ORDER BY period
    """
    
    return {
        "success": True,
        "sql_query": sql_query,
        "query_intent": {
            "metric_type": metric_type,
            "time_period": time_period,
            "aggregation_level": aggregation,
            "visualization_hint": "line_chart"
        },
        "query_context": {
            "query_id": query_id,
            "original_query": query,
            "intent_confidence": 0.6,
            "processing_method": "fallback",
            "schema_context": {
                "tables": ["financial_overview"],
                "columns": ["period_date", metric_type]
            }
        },
        "processing_time_ms": 50
    }


async def fallback_data_processing(sql_query: str, query_context: dict, query_id: str) -> dict:
    """Fallback data processing when data agent is unavailable"""
    logger.warning(f"Using fallback data processing for query {query_id}")
    
    try:
        from database.connection import get_database
        db = get_database()
        
        # Execute query directly
        raw_data = db.execute_query(sql_query, [], fetch_all=True)
        
        # Transform to expected format
        processed_data = []
        columns = []
        
        if raw_data:
            columns = list(raw_data[0].keys()) if raw_data else []
            for row in raw_data:
                processed_data.append(dict(row))
        
        return {
            "success": True,
            "processed_data": processed_data,
            "columns": columns,
            "row_count": len(processed_data),
            "processing_time_ms": 200,
            "processing_method": "fallback",
            "data_quality": {
                "is_valid": len(processed_data) > 0,
                "completeness": 1.0 if processed_data else 0.0,
                "consistency": 1.0
            }
        }
        
    except Exception as e:
        logger.error(f"Fallback data processing failed: {e}")
        return {
            "success": False,
            "error": f"Database query failed: {str(e)}",
            "processed_data": [],
            "columns": [],
            "row_count": 0
        }


def create_default_visualization(data: list) -> dict:
    """Create default visualization when viz agent fails"""
    return {
        "success": True,
        "chart_type": "table",
        "chart_config": {
            "title": "Financial Data",
            "type": "table",
            "responsive": True
        },
        "processing_time_ms": 10,
        "processing_method": "fallback"
    }


    """Parse natural language query and extract intent"""
    query_lower = query.lower()
    
    # Simple rule-based intent extraction
    # In production, this would call the NLP agent
    
    # Determine metric type
    metric_type = "revenue"  # default
    if "cash flow" in query_lower or "cash" in query_lower:
        metric_type = "cash_flow"
    elif "budget" in query_lower or "expense" in query_lower:
        metric_type = "budget_variance" 
    elif "investment" in query_lower or "roi" in query_lower:
        metric_type = "investment_performance"
    elif "profit" in query_lower or "margin" in query_lower:
        metric_type = "profit_margin"
    
    # Determine time period
    time_period = "this_year"  # default
    if "month" in query_lower:
        time_period = "this_month"
    elif "quarter" in query_lower or "q1" in query_lower or "q2" in query_lower:
        time_period = "this_quarter"
    elif "year" in query_lower:
        time_period = "this_year"
    
    # Determine aggregation
    aggregation_level = "monthly"
    if "daily" in query_lower or "day" in query_lower:
        aggregation_level = "daily"
    elif "weekly" in query_lower or "week" in query_lower:
        aggregation_level = "weekly"
    elif "quarterly" in query_lower or "quarter" in query_lower:
        aggregation_level = "quarterly"
    elif "yearly" in query_lower or "annual" in query_lower:
        aggregation_level = "yearly"
    
    return QueryIntent(
        metric_type=metric_type,
        time_period=time_period,
        aggregation_level=aggregation_level,
        visualization_hint="line_chart",
        confidence_score=0.8
    )


def generate_sql_from_intent(intent: QueryIntent) -> tuple[str, tuple]:
    """Generate SQL query from query intent"""
    
    # Map metric types to tables and columns
    if intent.metric_type == "revenue":
        base_query = """
        SELECT 
            DATE_FORMAT(period_date, %s) as period,
            SUM(revenue) as revenue
        FROM financial_overview 
        WHERE period_date >= %s
        GROUP BY DATE_FORMAT(period_date, %s)
        ORDER BY period
        """
        
        # Determine date format and filter based on aggregation
        if intent.aggregation_level == "daily":
            date_format = "%Y-%m-%d"
            date_filter = "2025-01-01"  # Use fixed date within our data range
        elif intent.aggregation_level == "weekly":
            date_format = "%Y-W%u"
            date_filter = "2025-01-01"
        elif intent.aggregation_level == "monthly":
            date_format = "%Y-%m"
            date_filter = "2025-01-01"
        elif intent.aggregation_level == "quarterly":
            date_format = "%Y-Q%q"
            date_filter = "2024-01-01"
        else:  # yearly
            date_format = "%Y"
            date_filter = "2022-01-01"
        
        return base_query, (date_format, date_filter, date_format)
    
    elif intent.metric_type == "cash_flow":
        base_query = """
        SELECT 
            DATE_FORMAT(period_date, %s) as period,
            SUM(operating_cash_flow) as operating_cash_flow,
            SUM(investing_cash_flow) as investing_cash_flow,
            SUM(financing_cash_flow) as financing_cash_flow,
            SUM(net_cash_flow) as net_cash_flow
        FROM cash_flow 
        WHERE period_date >= %s
        GROUP BY DATE_FORMAT(period_date, %s)
        ORDER BY period
        """
        
        date_format = "%Y-%m" if intent.aggregation_level == "monthly" else "%Y-Q%q"
        date_filter = "DATE_SUB(CURDATE(), INTERVAL 12 MONTH)"
        
        return base_query, (date_format, date_filter, date_format)
    
    elif intent.metric_type == "investment_performance":
        base_query = """
        SELECT 
            investment_name,
            roi_percentage,
            status,
            initial_amount,
            current_value
        FROM investments 
        WHERE status = 'active'
        ORDER BY roi_percentage DESC
        LIMIT 10
        """
        return base_query, ()
    
    else:  # Default to revenue
        base_query = """
        SELECT 
            DATE_FORMAT(period_date, '%Y-%m') as period,
            SUM(revenue) as revenue
        FROM financial_overview 
        WHERE period_date >= '2025-01-01'
        GROUP BY DATE_FORMAT(period_date, '%Y-%m')
        ORDER BY period
        """
        return base_query, ()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)