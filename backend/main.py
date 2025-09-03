"""
AI CFO Backend - FastAPI Gateway with WebSocket Support
Main FastAPI application with async endpoints, WebSocket handlers, and authentication.
"""

import os
import logging
import json
import asyncio
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

class FeedbackRequest(BaseModel):
    query_id: str
    rating: int  # 1-5
    feedback_text: Optional[str] = None


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
    """Process natural language query and return structured response"""
    try:
        query_id = f"q_{datetime.utcnow().timestamp()}"
        
        # TODO: Integrate with NLP Agent for actual query processing
        # For now, return mock response
        mock_intent = QueryIntent(
            metric_type="revenue",
            time_period="Q1 2024",
            aggregation_level="monthly",
            visualization_hint="line_chart"
        )
        
        mock_result = QueryResult(
            data=[
                {"period": "2024-01", "revenue": 1000000},
                {"period": "2024-02", "revenue": 1200000},
                {"period": "2024-03", "revenue": 1100000}
            ],
            columns=["period", "revenue"],
            row_count=3,
            processing_time_ms=250
        )
        
        # Store query in history (Redis)
        if redis_client:
            query_history = QueryHistoryEntry(
                query_id=query_id,
                user_id="anonymous",  # No authentication needed
                query_text=query_request.query,
                query_intent=mock_intent.dict(),
                response_data=mock_result.dict(),
                processing_time_ms=250
            )
            await redis_client.setex(
                f"query_history:{query_id}",
                3600,  # 1 hour expiry
                json.dumps(query_history.dict(), default=str)
            )
        
        return QueryResponse(
            query_id=query_id,
            intent=mock_intent,
            result=mock_result,
            visualization={
                "chart_type": "line_chart",
                "title": "Revenue Trend",
                "config": {"show_trend": True}
            }
        )
        
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