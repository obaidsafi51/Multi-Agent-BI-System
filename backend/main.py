"""
AI CFO Backend - FastAPI Gateway with WebSocket Support
Main FastAPI application with async endpoints, WebSocket handlers, and authentication.

INTENDED WORKFLOW:
1. System Initialization:
   - Frontend loads and checks for user session
   - If no database selected, call /api/database/list to get available databases
   - User selects database via database selector modal
   - Frontend calls /api/database/select to initialize schema context
   - MCP server stores schema context for subsequent agent operations

2. Query Processing Workflow:
   - User enters natural language query in frontend
   - Frontend sends query to /api/query endpoint
   - Backend routes query through agent workflow:
     a) NLP Agent: processes query, extracts intent, generates SQL
     b) Data Agent: executes SQL via MCP server, validates and processes data  
     c) Viz Agent: generates dashboard visualizations based on processed data
   - Backend returns combined response to frontend
   - Frontend updates dashboard with new visualizations

3. Agent Communication Pattern:
   Frontend → Backend → NLP Agent → Data Agent → Viz Agent → MCP Server
   
4. Error Handling:
   - Each agent has fallback mechanisms
   - MCP server provides direct database access as last resort
   - User receives meaningful error messages and recovery suggestions

5. Caching and Performance:
   - Schema context cached after database selection
   - Query results cached for performance
   - Agent responses cached when appropriate
"""

import os
import logging
import json
import asyncio
import aiohttp
import tracemalloc
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect,
    Request, Response, status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Import orchestration utilities
from orchestration import (
    CircuitBreaker, CircuitBreakerException, RetryConfig, 
    retry_with_backoff, RetryExhaustedException,
    orchestration_metrics, WebSocketProgressReporter
)

# Import WebSocket Agent Manager for Phase 1 parallel implementation
from websocket_agent_manager import websocket_agent_manager, AgentType
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from dotenv import load_dotenv
import redis.asyncio as redis
import httpx

# Import standardized shared models  
from shared.models.workflow import (
    QueryRequest, QueryResponse, QueryIntent, QueryResult, ErrorResponse,
    ProcessingMetadata, PerformanceMetrics, NLPResponse, DataQueryResponse, VisualizationResponse
)
from models.ui import BentoGridLayout, BentoGridCard
from database_context import DatabaseContextManager
from models.user import UserProfile, PersonalizationRecommendation, QueryHistoryEntry

# Import Pydantic for remaining local models
from pydantic import BaseModel, Field

# Import dynamic schema management
try:
    from schema_management.dynamic_schema_manager import get_dynamic_schema_manager
    from schema_management.intelligent_query_builder import get_intelligent_query_builder
    from schema_management.configuration_manager import ConfigurationManager
    DYNAMIC_SCHEMA_AVAILABLE = True
except ImportError as e:
    # Configure logging first so we can use logger in exception handler
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    logger.warning(f"Dynamic schema management not available: {e}")
    DYNAMIC_SCHEMA_AVAILABLE = False

# Load environment variables
load_dotenv()

# Configure logging (if not already configured)
if not logging.getLogger().handlers:
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
database_context_manager: Optional[DatabaseContextManager] = None

# Dynamic schema management globals
dynamic_schema_manager = None
intelligent_query_builder = None
configuration_manager = None

# Circuit breakers for agent protection
nlp_agent_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0,
    timeout=30.0,
    name="NLP_Agent"
)

data_agent_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=120.0,
    timeout=120.0,
    name="Data_Agent"
)

viz_agent_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=45.0,
    timeout=45.0,
    name="Viz_Agent"
)

# Retry configurations
nlp_retry_config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    retry_exceptions=(aiohttp.ClientError, asyncio.TimeoutError)
)

data_retry_config = RetryConfig(
    max_attempts=2,
    base_delay=2.0,
    max_delay=60.0,
    retry_exceptions=(aiohttp.ClientError, asyncio.TimeoutError)
)

viz_retry_config = RetryConfig(
    max_attempts=2,
    base_delay=1.0,
    max_delay=30.0,
    retry_exceptions=(aiohttp.ClientError, asyncio.TimeoutError)
)


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

# Get CORS origins from environment variables
frontend_url = os.getenv("FRONTEND_URL", "http://frontend:3000")
localhost_frontend = os.getenv("LOCALHOST_FRONTEND_URL", "http://localhost:3000")
cors_origins = [frontend_url, localhost_frontend]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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


# Response validation functions
def validate_nlp_response(response_data: Dict[str, Any]) -> Optional[NLPResponse]:
    """Validate and convert NLP agent response to standardized format"""
    try:
        # Try to parse as standardized NLPResponse first
        nlp_response = NLPResponse(**response_data)
        logger.info("NLP response successfully validated as standardized format")
        return nlp_response
    except Exception as e:
        logger.warning(f"NLP response validation failed, attempting conversion: {e}")
        try:
            # Attempt to convert various legacy formats to standardized format
            success = response_data.get("success", True)
            
            # Handle different response structure variations
            agent_metadata = response_data.get("agent_metadata", {})
            if not agent_metadata:
                # Create default metadata
                agent_metadata = {
                    "agent_name": "nlp-agent",
                    "agent_version": "2.2.0",
                    "processing_time_ms": int(response_data.get("execution_time", response_data.get("processing_time_ms", 0)) * 1000) if response_data.get("execution_time", 0) < 100 else int(response_data.get("execution_time", response_data.get("processing_time_ms", 0))),
                    "operation_id": f"nlp_op_{int(datetime.utcnow().timestamp() * 1000)}",
                    "status": "success" if success else "error"
                }
            
            # Extract or create intent
            intent_data = None
            if "intent" in response_data:
                intent_data = response_data["intent"]
            elif "query_intent" in response_data:
                intent_data = response_data["query_intent"]
            
            converted_response = {
                "success": success,
                "agent_metadata": agent_metadata,
                "intent": intent_data,
                "sql_query": response_data.get("sql_query", ""),
                "entities_recognized": response_data.get("entities", response_data.get("entities_recognized", [])),
                "confidence_score": response_data.get("confidence_score", 0.0),
                "processing_path": response_data.get("processing_path", "standard")
            }
            
            if not success:
                error_info = response_data.get("error", {})
                if isinstance(error_info, str):
                    error_info = {"message": error_info}
                
                converted_response["error"] = {
                    "error_type": error_info.get("error_type", "nlp_processing_error"),
                    "message": error_info.get("message", response_data.get("error", "Unknown NLP processing error")),
                    "recovery_action": error_info.get("recovery_action", "retry"),
                    "suggestions": error_info.get("suggestions", ["Try rephrasing your query", "Check query complexity"])
                }
            
            return NLPResponse(**converted_response)
        except Exception as conv_error:
            logger.error(f"Failed to convert NLP response: {conv_error}")
            return None

def validate_data_response(response_data: Dict[str, Any]) -> Optional[DataQueryResponse]:
    """Validate and convert Data agent response to standardized format"""
    try:
        # Try to parse as standardized DataQueryResponse first
        data_response = DataQueryResponse(**response_data)
        logger.info("Data response successfully validated as standardized format")
        return data_response
    except Exception as e:
        logger.warning(f"Data response validation failed, attempting conversion: {e}")
        try:
            # Attempt to convert various legacy formats to standardized format
            success = response_data.get("success", True)
            
            # Handle different response structure variations
            agent_metadata = response_data.get("agent_metadata", {})
            if not agent_metadata:
                # Create default metadata
                agent_metadata = {
                    "agent_name": "data-agent",
                    "agent_version": "1.0.0",
                    "processing_time_ms": response_data.get("processing_time_ms", 0),
                    "operation_id": f"data_op_{int(datetime.utcnow().timestamp() * 1000)}",
                    "status": "success" if success else "error"
                }
            
            converted_response = {
                "success": success,
                "agent_metadata": agent_metadata
            }
            
            if success:
                # Extract result data with multiple fallback formats
                result_data = response_data.get("result", {})
                if not result_data:
                    # Try alternative formats
                    result_data = {
                        "data": response_data.get("data", response_data.get("processed_data", [])),
                        "columns": response_data.get("columns", []),
                        "row_count": response_data.get("row_count", 0),
                        "processing_time_ms": response_data.get("processing_time_ms", 0)
                    }
                
                converted_response["result"] = result_data
                
                # Extract validation data
                validation_data = response_data.get("validation", {})
                if not validation_data:
                    data_quality = response_data.get("data_quality", {})
                    validation_data = {
                        "is_valid": data_quality.get("is_valid", True),
                        "quality_score": data_quality.get("quality_score", 1.0),
                        "issues": data_quality.get("issues", []),
                        "warnings": data_quality.get("warnings", [])
                    }
                
                converted_response["validation"] = validation_data
                converted_response["query_optimization"] = response_data.get("optimization", response_data.get("query_optimization", {}))
                converted_response["cache_metadata"] = response_data.get("cache_metadata", {"cache_hit": False})
            else:
                error_info = response_data.get("error", {})
                if isinstance(error_info, str):
                    error_info = {"message": error_info}
                
                converted_response["error"] = {
                    "error_type": error_info.get("error_type", "data_query_error"),
                    "message": error_info.get("message", response_data.get("error", "Unknown data processing error")),
                    "recovery_action": error_info.get("recovery_action", "retry"),
                    "suggestions": error_info.get("suggestions", ["Check database connectivity", "Verify query syntax"])
                }
            
            return DataQueryResponse(**converted_response)
        except Exception as conv_error:
            logger.error(f"Failed to convert Data response: {conv_error}")
            return None

def validate_viz_response(response_data: Dict[str, Any]) -> Optional[VisualizationResponse]:
    """Validate and convert Visualization agent response to standardized format"""
    try:
        # Try to parse as standardized VisualizationResponse first
        viz_response = VisualizationResponse(**response_data)
        logger.info("Visualization response successfully validated as standardized format")
        return viz_response
    except Exception as e:
        logger.warning(f"Visualization response validation failed, attempting conversion: {e}")
        try:
            # Attempt to convert various legacy formats to standardized format
            success = response_data.get("success", True)
            
            # Handle different response structure variations
            agent_metadata = response_data.get("agent_metadata", {})
            if not agent_metadata:
                # Create default metadata
                agent_metadata = {
                    "agent_name": "viz-agent",
                    "agent_version": "1.0.0",
                    "processing_time_ms": response_data.get("processing_time_ms", 0),
                    "operation_id": f"viz_op_{int(datetime.utcnow().timestamp() * 1000)}",
                    "status": "success" if success else "error"
                }
            
            converted_response = {
                "success": success,
                "agent_metadata": agent_metadata
            }
            
            if success:
                converted_response["chart_config"] = response_data.get("chart_config", {})
                converted_response["chart_data"] = response_data.get("chart_json", response_data.get("chart_data", {}))
                converted_response["dashboard_cards"] = response_data.get("dashboard_cards", [])
                converted_response["export_options"] = response_data.get("export_options", {
                    "formats": ["png", "pdf", "svg"],
                    "sizes": ["small", "medium", "large"]
                })
            else:
                error_info = response_data.get("error", {})
                if isinstance(error_info, str):
                    error_info = {"message": error_info}
                
                converted_response["error"] = {
                    "error_type": error_info.get("error_type", "visualization_error"),
                    "message": error_info.get("message", response_data.get("error", "Unknown visualization error")),
                    "recovery_action": error_info.get("recovery_action", "retry"),
                    "suggestions": error_info.get("suggestions", ["Check data format", "Try different chart type"])
                }
                
                # Still provide empty chart components for consistency
                converted_response["chart_config"] = {"chart_type": "error", "title": "Error", "responsive": True}
                converted_response["chart_data"] = {}
                converted_response["dashboard_cards"] = []
                converted_response["export_options"] = {"formats": [], "sizes": []}
            
            return VisualizationResponse(**converted_response)
        except Exception as conv_error:
            logger.error(f"Failed to convert Visualization response: {conv_error}")
            return None

async def startup_event():
    """Initialize connections, dynamic schema management, and validate environment on startup"""
    global redis_client, dynamic_schema_manager, intelligent_query_builder, configuration_manager, database_context_manager
    
    # Enable tracemalloc for better memory debugging
    if not tracemalloc.is_tracing():
        tracemalloc.start()
        logger.info("Tracemalloc enabled for memory debugging")
    
    # Initialize WebSocket Agent Manager (Phase 1)
    try:
        await websocket_agent_manager.start()
        logger.info("WebSocket Agent Manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket Agent Manager: {e}")
    
    # Initialize Redis connection
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connection established")
        
        # Initialize Database Context Manager
        database_context_manager = DatabaseContextManager(redis_client=redis_client)
        logger.info("Database Context Manager initialized")
        
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        redis_client = None
        database_context_manager = None
    
    # Initialize Dynamic Schema Management
    if DYNAMIC_SCHEMA_AVAILABLE:
        try:
            logger.info("Initializing dynamic schema management...")
            
            # Initialize configuration manager
            configuration_manager = ConfigurationManager()
            await configuration_manager.load_configuration()
            
            # Initialize dynamic schema manager
            dynamic_schema_manager = await get_dynamic_schema_manager()
            
            # Initialize intelligent query builder
            intelligent_query_builder = await get_intelligent_query_builder(dynamic_schema_manager)
            
            logger.info("Dynamic schema management initialized successfully")
            
        except Exception as e:
            logger.warning(f"Failed to initialize dynamic schema management: {e}")
            logger.info("Backend will operate in static configuration mode")
            dynamic_schema_manager = None
            intelligent_query_builder = None
            configuration_manager = None
    else:
        logger.info("Dynamic schema management not available, using static configuration")
    
    # Validate environment variables
    required_vars = ['TIDB_HOST', 'TIDB_USER', 'TIDB_PASSWORD', 'TIDB_DATABASE']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(f"Missing required environment variables: {missing_vars}")
    else:
        logger.info("All required environment variables are present")
    
    logger.info(
        f"Backend started successfully "
        f"(Dynamic Schema: {'enabled' if dynamic_schema_manager else 'disabled'})"
    )


async def shutdown_event():
    """Clean up connections on shutdown"""
    global redis_client
    
    # Shutdown WebSocket Agent Manager
    try:
        await websocket_agent_manager.stop()
        logger.info("WebSocket Agent Manager stopped")
    except Exception as e:
        logger.error(f"Error stopping WebSocket Agent Manager: {e}")
    
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
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = "anonymous"
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    query_id: str
    intent: QueryIntent
    result: Optional[QueryResult] = None
    visualization: Optional[Dict[str, Any]] = None
    error: Optional[ErrorResponse] = None
    agent_performance: Optional[Dict[str, Any]] = None


class DatabaseContextError(BaseModel):
    error_type: str = Field(..., description="Specific database context error type")
    message: str = Field(..., description="Human-readable error message")
    recovery_action: str = Field(..., description="Recommended recovery action")
    suggestions: List[str] = Field(default_factory=list, description="Suggested solutions")
    database_required: bool = Field(default=True, description="Whether database selection is required")
    session_id: Optional[str] = Field(None, description="Session ID if applicable")

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
    """Health check endpoint - Simplified version"""
    try:
        # Use dynamic schema health check if available
        if dynamic_schema_manager:
            try:
                from schema_management.health_check import check_mcp_server_health
                mcp_health = await check_mcp_server_health()
                
                return {
                    "status": "healthy" if mcp_health["status"] == "healthy" else "unhealthy",
                    "service": "backend",
                    "version": "1.0.0",
                    "timestamp": datetime.utcnow().isoformat(),
                    "mcp_status": mcp_health["status"],
                    "dynamic_schema": "enabled"
                }
            except Exception as e:
                logger.warning(f"Dynamic health check failed: {e}, using basic check")
        
        # Basic health check
        return {
            "status": "healthy",
            "service": "backend", 
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "dynamic_schema": "disabled" if not dynamic_schema_manager else "enabled"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/api/health/agents")
async def check_agents_health():
    """Check health status of all agents"""
    try:
        agent_health = await check_all_agents_health()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy" if agent_health["all_healthy"] else "degraded",
            "agents": {
                "nlp_agent": {
                    "status": "healthy" if agent_health["nlp_agent"] else "unhealthy",
                    "url": os.getenv("NLP_AGENT_URL", "http://nlp-agent:8001")
                },
                "data_agent": {
                    "status": "healthy" if agent_health["data_agent"] else "unhealthy", 
                    "url": os.getenv("DATA_AGENT_URL", "http://data-agent:8002")
                },
                "viz_agent": {
                    "status": "healthy" if agent_health["viz_agent"] else "unhealthy",
                    "url": os.getenv("VIZ_AGENT_URL", "http://viz-agent:8003")
                }
            },
            "healthy_count": sum([agent_health["nlp_agent"], agent_health["data_agent"], agent_health["viz_agent"]]),
            "total_count": 3
        }
        
    except Exception as e:
        logger.error(f"Agent health check failed: {e}")
        raise HTTPException(status_code=503, detail="Agent health check failed")


@app.get("/api/orchestration/metrics")
@limiter.limit("30/minute")
async def get_orchestration_metrics(request: Request):
    """Get comprehensive orchestration and circuit breaker metrics"""
    try:
        # Get base orchestration metrics
        metrics = await orchestration_metrics.get_metrics()
        
        # Add circuit breaker statistics
        circuit_breaker_stats = {
            "nlp_agent": nlp_agent_circuit_breaker.get_stats(),
            "data_agent": data_agent_circuit_breaker.get_stats(),
            "viz_agent": viz_agent_circuit_breaker.get_stats()
        }
        
        # Calculate system health score
        total_calls = sum(cb["stats"]["total_calls"] for cb in circuit_breaker_stats.values())
        total_successes = sum(cb["stats"]["successful_calls"] for cb in circuit_breaker_stats.values())
        system_health_score = (total_successes / max(total_calls, 1)) * 100
        
        # Count open circuit breakers
        open_circuits = sum(1 for cb in circuit_breaker_stats.values() if cb["state"] == "open")
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "orchestration_metrics": metrics,
            "circuit_breakers": circuit_breaker_stats,
            "system_health": {
                "score": round(system_health_score, 2),
                "open_circuits": open_circuits,
                "total_circuit_breakers": len(circuit_breaker_stats),
                "status": "healthy" if open_circuits == 0 else "degraded" if open_circuits < 2 else "critical"
            },
            "websocket_connections": len(websocket_connections)
        }
        
    except Exception as e:
        logger.error(f"Failed to get orchestration metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@app.get("/api/orchestration/circuit-breakers/reset")
@limiter.limit("10/minute")
async def reset_circuit_breakers(request: Request):
    """Reset all circuit breakers (admin function)"""
    try:
        # Reset all circuit breakers to closed state
        for breaker in [nlp_agent_circuit_breaker, data_agent_circuit_breaker, viz_agent_circuit_breaker]:
            async with breaker._lock:
                breaker.state = breaker.state.__class__.CLOSED
                breaker.stats.consecutive_failures = 0
                breaker._half_open_successes = 0
                breaker.stats.state_changes += 1
        
        logger.info("All circuit breakers have been reset")
        
        return {
            "message": "All circuit breakers have been reset",
            "timestamp": datetime.utcnow().isoformat(),
            "reset_breakers": ["NLP_Agent", "Data_Agent", "Viz_Agent"]
        }
        
    except Exception as e:
        logger.error(f"Failed to reset circuit breakers: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset circuit breakers")



@app.post("/api/query", response_model=QueryResponse)
@limiter.limit("30/minute")
async def process_query(
    request: Request,
    query_request: QueryRequest
):
    """Process natural language query through multi-agent workflow"""
    try:
        query_id = f"q_{datetime.utcnow().timestamp()}"
        user_id = query_request.user_id or "anonymous"
        
        # Use provided session_id or generate a new one
        if query_request.session_id:
            session_id = query_request.session_id
        else:
            session_id = f"session_{int(datetime.utcnow().timestamp())}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=12))}"
        
        logger.info(f"Starting multi-agent workflow for query: {query_request.query} (session: {session_id})")
        
        # Validate database context - always check if a session_id is provided
        database_context = None
        if session_id:
            database_context = await get_database_context(session_id)
            if not database_context:
                logger.warning(f"No database context found for session {session_id}")
                # Return error suggesting database selection
                return QueryResponse(
                    query_id=query_id,
                    intent=QueryIntent(metric_type="unknown", time_period="unknown"),
                    error=ErrorResponse(
                        error_type="database_context_missing",
                        message="Please select a database first before running queries.",
                        recovery_action="select_database",
                        suggestions=[
                            "Use the database selector to choose a database",
                            "Ensure you have selected a database from the available options",
                            "Check if your session has expired and select a database again"
                        ]
                    )
                )
        
        # Step 1: Send query to NLP Agent with dynamic schema context and database context
        if dynamic_schema_manager:
            # Use enhanced version with dynamic schema context and database context
            nlp_result = await send_to_nlp_agent_with_dynamic_context(
                query_request.query, 
                user_id, 
                session_id,
                database_context=database_context  # Pass database context to NLP agent
            )
        else:
            # Use standard NLP agent with database context
            nlp_result = await send_to_nlp_agent(query_request.query, query_id, session_id, database_context=database_context)
        
        logger.info(f"NLP processing completed for query: {query_request.query}")
        
        # Check if NLP processing was successful
        if not nlp_result or nlp_result.get("error"):
            error_msg = nlp_result.get("error", "NLP processing failed") if nlp_result else "No response from NLP agent"
            logger.error(f"NLP processing failed: {error_msg}")
            return QueryResponse(
                query_id=query_id,
                intent=QueryIntent(metric_type="unknown", time_period="unknown"),
                error=ErrorResponse(
                    error_type="nlp_error",
                    message=f"Failed to understand query: {error_msg}",
                    recovery_action="retry",
                    suggestions=["Try rephrasing your question", "Use more specific financial terms"]
                )
            )
        
        # Extract SQL query and intent from NLP result
        sql_query = nlp_result.get("sql_query", "")
        query_intent = nlp_result.get("intent", {})
        
        if not sql_query:
            logger.error("No SQL query generated by NLP agent")
            return QueryResponse(
                query_id=query_id,
                intent=QueryIntent(
                    metric_type=query_intent.get("metric_type", "unknown"),
                    time_period=query_intent.get("time_period", "unknown")
                ),
                error=ErrorResponse(
                    error_type="sql_generation_error",
                    message="Unable to generate SQL query from your request",
                    recovery_action="rephrase",
                    suggestions=["Try being more specific about what data you want", "Use standard business terms like 'revenue', 'profit', 'expenses'"]
                )
            )
        
        logger.info(f"Generated SQL query: {sql_query}")
        
        # Step 2: Send SQL query to Data Agent for execution
        logger.info(f"🔧 Sending SQL query to Data Agent: {sql_query[:100]}...")
        
        try:
            data_result = await send_to_data_agent(sql_query, query_intent, query_id, session_id)
            logger.info(f"📊 Data Agent response received: {data_result.get('success', False)}")
        except Exception as e:
            logger.error(f"❌ Data Agent communication error: {e}")
            data_result = await fallback_data_processing(sql_query, query_intent, query_id)
            logger.info(f"🔄 Using fallback data processing result")
        
        if not data_result or not data_result.get("success"):
            error_msg = data_result.get("error", "Data processing failed") if data_result else "No response from Data agent"
            logger.error(f"❌ Data processing failed: {error_msg}")
            
            # Try fallback data processing before failing
            logger.info("🔄 Attempting fallback data processing...")
            try:
                data_result = await fallback_data_processing(sql_query, query_intent, query_id)
                if data_result and data_result.get("success"):
                    logger.info("✅ Fallback data processing succeeded")
                else:
                    raise Exception("Fallback also failed")
            except Exception as fallback_error:
                logger.error(f"❌ Fallback data processing also failed: {fallback_error}")
                return QueryResponse(
                    query_id=query_id,
                    intent=QueryIntent(
                        metric_type=query_intent.get("metric_type", "unknown"),
                        time_period=query_intent.get("time_period", "unknown")
                    ),
                    error=ErrorResponse(
                        error_type="data_error",
                        message=f"Failed to execute query: {error_msg}",
                        recovery_action="retry",
                        suggestions=["Check if the database is accessible", "Try a simpler query"]
                    )
                )
        
        logger.info(f"✅ Data processing completed, retrieved {data_result.get('row_count', 0)} rows")
        
        # Extract data from data agent result
        query_data = data_result.get("processed_data", [])
        columns = data_result.get("columns", [])
        
        # Step 3: Send data to Visualization Agent for chart generation
        logger.info(f"🎨 Sending data to Viz Agent: {len(query_data)} rows")
        
        try:
            viz_result = await send_to_viz_agent(query_data, query_intent, query_id, session_id)
            logger.info(f"📈 Viz Agent response received: {viz_result.get('success', False)}")
        except Exception as e:
            logger.warning(f"⚠️ Viz Agent communication error: {e}")
            viz_result = create_default_visualization(query_data)
            logger.info(f"🔄 Using default visualization")
        
        if not viz_result or not viz_result.get("success"):
            error_msg = viz_result.get("error", "Visualization failed") if viz_result else "No response from Viz agent"
            logger.warning(f"⚠️ Visualization processing failed: {error_msg}")
            # Don't fail the entire query for visualization issues - provide default
            viz_result = create_default_visualization(query_data)
            logger.info(f"🔄 Using fallback visualization")
        
        logger.info(f"✅ Visualization processing completed")
        
        # Build the complete response
        return QueryResponse(
            query_id=query_id,
            intent=QueryIntent(
                metric_type=query_intent.get("metric_type", "unknown"),
                time_period=query_intent.get("time_period", "unknown")
            ),
            result=QueryResult(
                data=query_data,
                columns=columns,
                row_count=len(query_data),
                sql_query=sql_query,
                processing_time_ms=data_result.get("processing_time_ms", 0)
            ),
            visualization={
                "chart_type": viz_result.get("chart_config", {}).get("chart_type", "table"),
                "chart_config": viz_result.get("chart_config", {}),
                "chart_data": viz_result.get("chart_data", {}),
                "chart_html": viz_result.get("chart_html"),
                "chart_json": viz_result.get("chart_json")
            },
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return QueryResponse(
            query_id=query_id,
            intent=QueryIntent(metric_type="unknown", time_period="unknown"),
            error=ErrorResponse(
                error_type="processing_error",
                message=f"Error processing query: {str(e)}",
                recovery_action="retry",
                suggestions=["Please try again or rephrase your question"]
            )
        )


async def get_database_list(request: Request):
    """Get list of available databases from TiDB Cloud (cached)"""
    try:
        # Check cache first
        cache_key = "database_list_cache"
        if redis_client:
            try:
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    logger.info("Serving database list from cache")
                    return json.loads(cached_data)
            except Exception as cache_error:
                logger.warning(f"Cache read error: {cache_error}")
        
        # Get MCP client and discover databases
        from mcp_client import get_backend_mcp_client
        mcp_client = get_backend_mcp_client()
        
        # Make request to MCP server to discover databases
        databases_result = await mcp_client.discover_databases()
        
        if databases_result and not (isinstance(databases_result, dict) and databases_result.get("error")):
            # Handle both list and dict responses from MCP server
            if isinstance(databases_result, list):
                databases = databases_result
            else:
                databases = databases_result.get("databases", []) if isinstance(databases_result, dict) else []
            
            # Filter out system databases and only include accessible ones
            filtered_databases = []
            for db in databases:
                if (db.get("accessible", True) and 
                    db.get("name", "").lower() not in ['information_schema', 'performance_schema', 'mysql', 'sys']):
                    filtered_databases.append({
                        "name": db["name"],
                        "charset": db.get("charset", "utf8mb4"),
                        "collation": db.get("collation", "utf8mb4_general_ci"),
                        "accessible": db.get("accessible", True)
                    })
            
            result = {
                "success": True,
                "databases": filtered_databases,
                "total_count": len(filtered_databases)
            }
            
            # Cache the successful result for 10 minutes
            if redis_client:
                try:
                    await redis_client.setex(
                        cache_key,
                        600,  # 10 minute cache
                        json.dumps(result, default=str)
                    )
                    logger.info("Database list cached for 10 minutes")
                except Exception as cache_error:
                    logger.warning(f"Cache write error: {cache_error}")
            
            return result
        else:
            error_message = databases_result.get("error", "Unknown error") if databases_result and isinstance(databases_result, dict) else "MCP client returned invalid response"
            raise HTTPException(
                status_code=500,
                detail=f"MCP server error: {error_message}"
            )
                
    except asyncio.TimeoutError:
        logger.error("Database list API timed out")
        raise HTTPException(
            status_code=504,
            detail="Database list request timed out"
        )
    except Exception as e:
        logger.error(f"Database list API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch database list: {str(e)}"
        )


@app.get("/api/database/list")
@limiter.limit("30/minute")
async def get_database_list_endpoint(request: Request):
    """Get list of available databases"""
    return await get_database_list(request)


@app.post("/api/database/select")
@limiter.limit("10/minute")
async def select_database_and_fetch_schema(request: Request, body: dict):
    """Select a database and fetch its schema information with context management"""
    try:
        database_name = body.get("database_name")
        session_id = body.get("session_id")
        
        # Generate session_id if not provided
        if not session_id:
            session_id = f"session_{int(datetime.utcnow().timestamp())}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=12))}"

        if not database_name:
            raise HTTPException(
                status_code=400,
                detail="Database name is required"
            )
        
        # Validate session_id format
        if not session_id or len(session_id.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Valid session_id is required"
            )
        
        # Use database context manager for enhanced validation and session management
        if database_context_manager:
            try:
                # Create and validate database context
                context = await database_context_manager.select_database(
                    session_id=session_id,
                    database_name=database_name
                )
                
                # Get MCP client and discover tables for the selected database
                from mcp_client import get_backend_mcp_client
                mcp_client = get_backend_mcp_client()
                
                # Make request to MCP server to discover tables for the selected database
                tables_result = await mcp_client.discover_tables(database_name)
                
                if tables_result and not (isinstance(tables_result, dict) and tables_result.get("error")):
                    # Handle both list and dict responses from MCP server
                    if isinstance(tables_result, list):
                        tables = tables_result
                    else:
                        tables = tables_result.get("tables", []) if isinstance(tables_result, dict) else []
                    
                    # ✅ ENHANCED: Pre-fetch and cache full schema context for better performance
                    logger.info(f"🔄 Pre-caching schema context for {database_name}...")
                    
                    try:
                        # Fetch full schema context from MCP server and cache it
                        schema_context = await mcp_client.build_schema_context(database_name=database_name)
                        
                        # Cache schema context in Redis for faster access
                        if redis_client:
                            cache_key = f"schema_context:{database_name}"
                            await redis_client.setex(
                                cache_key,
                                3600,  # 1 hour cache
                                json.dumps(schema_context)
                            )
                            logger.info(f"✅ Schema context cached for {database_name}")
                        
                        # Update database context to mark schema as cached
                        if context:
                            context.schema_cached = True
                            context.table_count = len(tables)
                            await database_context_manager.update_context(session_id, context)
                            
                    except Exception as schema_error:
                        logger.warning(f"Schema pre-caching failed for {database_name}: {schema_error}")
                        # Don't fail the database selection if schema caching fails
                    
                    logger.info(f"✅ Database {database_name} selected successfully for session {session_id}, {len(tables)} tables available")
                    
                    return {
                        "success": True,
                        "database_name": database_name,
                        "session_id": session_id,
                        "tables": tables,
                        "total_tables": len(tables),
                        "schema_initialized": True,
                        "schema_cached": True,
                        "context_created": context is not None,
                        "database_validated": True,
                        "cache_duration": "1 hour",
                        "message": f"Database selected and schema cached successfully"
                    }
                else:
                    error_message = tables_result.get("error", "Unknown error") if tables_result and isinstance(tables_result, dict) else "MCP client returned invalid response"
                    raise HTTPException(
                        status_code=500,
                        detail=f"MCP server error: {error_message}"
                    )
                    
            except ValueError as e:
                # Database validation failed
                raise HTTPException(
                    status_code=400,
                    detail=f"Database validation failed: {str(e)}"
                )
            except Exception as e:
                logger.error(f"Database context management error: {e}")
                # Fall back to basic functionality if context management fails
                raise HTTPException(
                    status_code=500,
                    detail=f"Context management failed: {str(e)}"
                )
        else:
            # Fallback when database context manager is not available
            logger.warning("Database context manager not available, using basic functionality")
            
            # Get MCP client and discover tables for the selected database
            from mcp_client import get_backend_mcp_client
            mcp_client = get_backend_mcp_client()
            
            # Make request to MCP server to discover tables for the selected database
            tables_result = await mcp_client.discover_tables(database_name)
            
            if tables_result and not (isinstance(tables_result, dict) and tables_result.get("error")):
                # Handle both list and dict responses from MCP server
                if isinstance(tables_result, list):
                    tables = tables_result
                else:
                    tables = tables_result.get("tables", []) if isinstance(tables_result, dict) else []
                
                # Create database context for session storage
                database_context = {
                    "database_name": database_name,
                    "schema_initialized": True,
                    "total_tables": len(tables),
                    "table_names": [table.get("name", "") for table in tables],
                    "selected_at": datetime.utcnow().isoformat(),
                    "session_id": session_id
                }
                
                # Store database context in Redis session
                context_stored = await set_database_context(session_id, database_context)
                
                # Database selection successful - schema will be fetched on-demand during queries
                logger.info(f"Database {database_name} selected successfully (fallback mode)")
                
                # Note: Schema fetching will be done on-demand during query processing
                if DYNAMIC_SCHEMA_AVAILABLE:
                    try:
                        # Just log that schema manager is available, don't trigger schema fetch
                        logger.info("Dynamic schema manager available for on-demand schema fetching")
                    except Exception as e:
                        logger.warning(f"Failed to refresh dynamic schema for {database_name}: {e}")
                
                return {
                    "success": True,
                    "database_name": database_name,
                    "session_id": session_id,
                    "tables": tables,
                    "total_tables": len(tables),
                    "schema_initialized": True,
                    "context_stored": context_stored,
                    "context_created": False,
                    "database_validated": False
                }
            else:
                error_message = tables_result.get("error", "Unknown error") if tables_result and isinstance(tables_result, dict) else "MCP client returned invalid response"
                raise HTTPException(
                    status_code=500,
                    detail=f"MCP server error: {error_message}"
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database selection API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to select database: {str(e)}"
        )


@app.get("/api/database/context/{session_id}")
@limiter.limit("30/minute")
async def get_database_context_status(request: Request, session_id: str):
    """Get current database context for a session"""
    try:
        database_context = await get_database_context(session_id)
        
        if database_context:
            return {
                "success": True,
                "session_id": session_id,
                "database_context": database_context,
                "context_available": True
            }
        else:
            return {
                "success": True,
                "session_id": session_id,
                "database_context": None,
                "context_available": False,
                "message": "No database context found for this session"
            }
            
    except Exception as e:
        logger.error(f"Failed to retrieve database context for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve database context: {str(e)}"
        )


@app.post("/api/database/validate")
@limiter.limit("30/minute")
async def validate_database_context(request: Request, body: dict):
    """Validate database context for a session before query processing"""
    try:
        session_id = body.get("session_id")
        if not session_id:
            raise HTTPException(
                status_code=400,
                detail="Session ID is required for database context validation"
            )
        
        database_context = await get_database_context(session_id)
        
        if not database_context:
            return {
                "valid": False,
                "error": DatabaseContextError(
                    error_type="database_context_missing",
                    message="No database has been selected for this session.",
                    recovery_action="select_database",
                    suggestions=[
                        "Use the database selector to choose a database",
                        "Ensure you have access to at least one database",
                        "Check if your session has expired and refresh if needed"
                    ],
                    database_required=True,
                    session_id=session_id
                ).dict(),
                "session_id": session_id
            }
        
        # Validate database accessibility
        try:
            # Quick validation query
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://tidb-mcp-server:8000/tools/execute_query_tool",
                    json={
                        "database": database_context.get("database_name"),
                        "query": "SELECT 1 as test"
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    return {
                        "valid": False,
                        "error": DatabaseContextError(
                            error_type="database_connection_error",
                            message=f"Cannot connect to database '{database_context.get('database_name')}'",
                            recovery_action="retry_or_select_different",
                            suggestions=[
                                "Try selecting the database again",
                                "Check if the database server is running",
                                "Select a different database if this one is unavailable"
                            ],
                            database_required=True,
                            session_id=session_id
                        ).dict(),
                        "session_id": session_id
                    }
        except Exception as validation_error:
            logger.warning(f"Database validation failed for session {session_id}: {validation_error}")
            return {
                "valid": False,
                "error": DatabaseContextError(
                    error_type="database_validation_failed",
                    message="Unable to validate database connection",
                    recovery_action="retry",
                    suggestions=[
                        "Check your network connection",
                        "Try selecting the database again",
                        "Contact support if the issue persists"
                    ],
                    database_required=True,
                    session_id=session_id
                ).dict(),
                "session_id": session_id
            }
        
        # Valid database context
        return {
            "valid": True,
            "database_context": database_context,
            "session_id": session_id,
            "message": f"Database context is valid for '{database_context.get('database_name')}'"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database context validation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate database context: {str(e)}"
        )


@app.get("/api/database/test")
@limiter.limit("30/minute")
async def test_database(request: Request):
    """Test database connectivity via MCP and get detailed information"""
@limiter.limit("30/minute") 
async def get_database_context(request: Request, session_id: str):
    """Get the current database context for a session"""
    try:
        if not database_context_manager:
            raise HTTPException(
                status_code=503,
                detail="Database context manager not available"
            )
        
        context = await database_context_manager.get_context(session_id)
        if not context:
            raise HTTPException(
                status_code=404,
                detail=f"No database context found for session {session_id}"
            )
        
        return {
            "success": True,
            "session_id": session_id,
            "context": {
                "database_name": context.database_name,
                "selected_at": context.selected_at.isoformat(),
                "last_activity": context.last_activity.isoformat(),
                "table_count": len(context.tables) if context.tables else 0,
                "tables": context.tables[:10] if context.tables else [],  # Limit for response size
                "is_validated": context.is_validated
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get context error for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get context: {str(e)}"
        )


@app.delete("/api/database/context/{session_id}")
@limiter.limit("10/minute")
async def clear_database_context(request: Request, session_id: str):
    """Clear the database context for a session"""
    try:
        if not database_context_manager:
            raise HTTPException(
                status_code=503,
                detail="Database context manager not available"
            )
        
        success = await database_context_manager.clear_context(session_id)
        
        return {
            "success": success,
            "session_id": session_id,
            "message": "Context cleared successfully" if success else "Context not found or already cleared"
        }
        
    except Exception as e:
        logger.error(f"Clear context error for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear context: {str(e)}"
        )


@app.get("/api/database/contexts")
@limiter.limit("10/minute")
async def list_active_contexts(request: Request):
    """List all active database contexts (for debugging/admin)"""
    try:
        if not database_context_manager:
            raise HTTPException(
                status_code=503,
                detail="Database context manager not available"
            )
        
        contexts = await database_context_manager.list_active_sessions()
        
        return {
            "success": True,
            "active_sessions": len(contexts),
            "contexts": [
                {
                    "session_id": ctx.session_id,
                    "database_name": ctx.database_name,
                    "selected_at": ctx.selected_at.isoformat(),
                    "last_activity": ctx.last_activity.isoformat(),
                    "table_count": len(ctx.tables) if ctx.tables else 0,
                    "is_validated": ctx.is_validated
                }
                for ctx in contexts
            ]
        }
        
    except Exception as e:
        logger.error(f"List contexts error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list contexts: {str(e)}"
        )


@app.get("/api/database/test")
@limiter.limit("30/minute")
async def test_database(request: Request):
    """Test database connectivity via MCP and get detailed information"""
    try:
        from mcp_client import get_backend_mcp_client
        
        mcp_client = get_backend_mcp_client()
        
        # Test basic connection
        connection_healthy = await mcp_client.health_check()
        
        test_results = {
            "connection_status": "healthy" if connection_healthy else "unhealthy",
            "database_info": {
                "name": "Agentic_BI",
                "type": "TiDB Cloud via MCP Server",
                "mcp_server_url": mcp_client.server_url
            },
            "test_queries": {}
        }
        
        if not connection_healthy:
            test_results["test_queries"]["connection_error"] = {
                "status": "error",
                "error": "MCP Server connection failed"
            }
            return test_results
        
        # Test basic SELECT query
        try:
            version_result = await mcp_client.execute_query("SELECT VERSION() as version")
            if version_result and version_result.get("success"):
                test_results["test_queries"]["version_query"] = {
                    "status": "success",
                    "result": version_result.get("data", [])
                }
            else:
                test_results["test_queries"]["version_query"] = {
                    "status": "error",
                    "error": version_result.get("error", "Unknown error") if version_result else "No response"
                }
        except Exception as e:
            test_results["test_queries"]["version_query"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Test SHOW DATABASES
        try:
            databases_result = await mcp_client.execute_query("SHOW DATABASES")
            if databases_result and databases_result.get("success"):
                test_results["test_queries"]["show_databases"] = {
                    "status": "success",
                    "result": databases_result.get("data", []),
                    "count": len(databases_result.get("data", []))
                }
            else:
                test_results["test_queries"]["show_databases"] = {
                    "status": "error",
                    "error": databases_result.get("error", "Unknown error") if databases_result else "No response"
                }
        except Exception as e:
            test_results["test_queries"]["show_databases"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Test current database and tables
        try:
            current_db_result = await mcp_client.execute_query("SELECT DATABASE() as current_db")
            if current_db_result and current_db_result.get("success"):
                test_results["test_queries"]["current_database"] = {
                    "status": "success",
                    "result": current_db_result.get("data", [])
                }
                
                # Show tables
                tables_result = await mcp_client.execute_query("SHOW TABLES")
                if tables_result and tables_result.get("success"):
                    test_results["test_queries"]["show_tables"] = {
                        "status": "success",
                        "result": tables_result.get("data", []),
                        "count": len(tables_result.get("data", []))
                    }
                else:
                    test_results["test_queries"]["show_tables"] = {
                        "status": "error",
                        "error": tables_result.get("error", "Unknown error") if tables_result else "No response"
                    }
            else:
                test_results["test_queries"]["current_database"] = {
                    "status": "error",
                    "error": current_db_result.get("error", "Unknown error") if current_db_result else "No response"
                }
        except Exception as e:
            test_results["test_queries"]["current_database"] = {
                "status": "error",
                "error": str(e)
            }
        
        return test_results
        
    except Exception as e:
        logger.error(f"MCP database test failed: {e}")
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


# Dynamic Schema Management API Endpoints

@app.get("/api/schema/discovery")
async def get_schema_discovery():
    """
    API endpoint for MCP-driven schema discovery using schema intelligence.
    Returns discovered tables, columns, and business term mappings from MCP server.
    """
    try:
        from mcp_client import get_backend_mcp_client
        
        mcp_client = get_backend_mcp_client()
        
        # Use MCP server's business mapping discovery
        mappings_result = await mcp_client.call_tool(
            "discover_business_mappings_tool",
            {
                "business_terms": ["revenue", "profit", "expenses", "cash_flow", "assets"],
                "confidence_threshold": 0.6
            }
        )
        
        # Also get basic database structure
        databases_result = await mcp_client.discover_databases()
        
        if mappings_result and mappings_result.get("success"):
            return {
                "success": True,
                "discovery_method": "mcp_server_driven",
                "business_mappings": mappings_result.get("mappings", {}),
                "databases": databases_result if isinstance(databases_result, list) else [],
                "statistics": mappings_result.get("statistics", {}),
                "discovery_timestamp": datetime.now().isoformat()
            }
        else:
            # Fallback to basic discovery
            return {
                "success": True,
                "discovery_method": "basic_fallback",
                "databases": databases_result if isinstance(databases_result, list) else [],
                "business_mappings": {},
                "discovery_timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"MCP-driven schema discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Schema discovery failed: {str(e)}")


@app.get("/api/schema/mappings/{business_term}")
async def get_business_term_mappings(business_term: str):
    """
    Get mappings for a specific business term using MCP server intelligence.
    """
    try:
        from mcp_client import get_backend_mcp_client
        
        mcp_client = get_backend_mcp_client()
        
        # Use MCP server's business mapping discovery for specific term
        result = await mcp_client.call_tool(
            "discover_business_mappings_tool",
            {
                "business_terms": [business_term],
                "confidence_threshold": 0.5
            }
        )
        
        if result and result.get("success"):
            term_mappings = result.get("mappings", {}).get(business_term, [])
            
            return {
                "success": True,
                "business_term": business_term,
                "mappings": term_mappings,
                "total_mappings": len(term_mappings),
                "source": "mcp_server_intelligence"
            }
        else:
            return {
                "success": False,
                "business_term": business_term,
                "error": result.get("error", "Failed to discover mappings"),
                "mappings": []
            }
        
    except Exception as e:
        logger.error(f"Business term mapping failed for '{business_term}': {e}")
        raise HTTPException(status_code=500, detail=f"Mapping discovery failed: {str(e)}")


@app.post("/api/schema/analyze-query")
async def analyze_query_intent_endpoint(request: dict):
    """
    Analyze natural language query using MCP server intelligence.
    """
    try:
        query = request.get("query")
        context = request.get("context", {})
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        from mcp_client import get_backend_mcp_client
        
        mcp_client = get_backend_mcp_client()
        
        # Use MCP server's query intent analysis
        result = await mcp_client.call_tool(
            "analyze_query_intent_tool",
            {
                "natural_language_query": query,
                "context": context
            }
        )
        
        if result and result.get("success"):
            return {
                "success": True,
                "query": query,
                "intent": result.get("intent", {}),
                "suggested_sql": result.get("suggested_sql"),
                "confidence_score": result.get("confidence_score", 0.0),
                "source": "mcp_server_intelligence"
            }
        else:
            return {
                "success": False,
                "query": query,
                "error": result.get("error", "Failed to analyze query intent")
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query intent analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query analysis failed: {str(e)}")


@app.get("/api/schema/optimizations/{database}")
async def get_schema_optimizations(database: str):
    """
    Get schema optimization suggestions from MCP server intelligence.
    """
    try:
        from mcp_client import get_backend_mcp_client
        
        mcp_client = get_backend_mcp_client()
        
        # Use MCP server's optimization suggestions
        result = await mcp_client.call_tool(
            "suggest_schema_optimizations_tool",
            {
                "database": database,
                "performance_threshold": 0.5
            }
        )
        
        if result and result.get("success"):
            return {
                "success": True,
                "database": database,
                "optimizations": result.get("optimizations", {}),
                "source": "mcp_server_intelligence",
                "analysis_timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "database": database,
                "error": result.get("error", "Failed to analyze optimizations"),
                "optimizations": {}
            }
        
    except Exception as e:
        logger.error(f"Schema optimization analysis failed for '{database}': {e}")
        raise HTTPException(status_code=500, detail=f"Optimization analysis failed: {str(e)}")


@app.post("/api/schema/learn-mapping")
async def learn_from_mapping_success(request: dict):
    """
    Report successful mapping usage to improve MCP server intelligence.
    """
    try:
        business_term = request.get("business_term")
        database_name = request.get("database_name")
        table_name = request.get("table_name")
        column_name = request.get("column_name")
        success_score = request.get("success_score", 1.0)
        
        if not all([business_term, database_name, table_name]):
            raise HTTPException(
                status_code=400, 
                detail="business_term, database_name, and table_name are required"
            )
        
        from mcp_client import get_backend_mcp_client
        
        mcp_client = get_backend_mcp_client()
        
        # Use MCP server's learning capability
        result = await mcp_client.call_tool(
            "learn_from_successful_mapping_tool",
            {
                "business_term": business_term,
                "database_name": database_name,
                "table_name": table_name,
                "column_name": column_name,
                "success_score": success_score
            }
        )
        
        if result and result.get("success"):
            return {
                "success": True,
                "message": result.get("message", "Mapping learned successfully"),
                "confidence_boost": result.get("confidence_boost", 0.0)
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to learn from mapping")
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Learning from mapping failed: {e}")
        raise HTTPException(status_code=500, detail=f"Learning failed: {str(e)}")


@app.get("/api/schema/intelligence-stats")
async def get_schema_intelligence_stats():
    """
    Get statistics about MCP server schema intelligence operations.
    """
    try:
        from mcp_client import get_backend_mcp_client
        
        mcp_client = get_backend_mcp_client()
        
        # Use MCP server's statistics
        result = await mcp_client.call_tool(
            "get_schema_intelligence_stats_tool",
            {}
        )
        
        if result and result.get("success"):
            return {
                "success": True,
                "statistics": result.get("statistics", {}),
                "source": "mcp_server_intelligence",
                "timestamp": result.get("timestamp", datetime.now().isoformat())
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to get statistics"),
                "statistics": {}
            }
        
    except Exception as e:
        logger.error(f"Schema intelligence stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")


@app.get("/api/schema/discovery/fast")
async def get_fast_schema_discovery():
    """
    API endpoint for lightweight schema metadata only (no table schema fetching).
    Returns database and table lists without detailed schema information.
    Schemas are fetched on-demand during query processing.
    """
    # Define cache key and TTL
    cache_key = "schema:discovery:fast:metadata_only"
    cache_ttl = 1800  # 30 minutes cache for metadata
    
    try:
        # Try to get from cache first
        cached_result = None
        if redis_client:
            try:
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    cached_result = json.loads(cached_data)
                    logger.info("Schema metadata served from cache")
                    cached_result["cache_hit"] = True
                    return cached_result
            except Exception as cache_error:
                logger.warning(f"Cache read error: {cache_error}")
        
        # Cache miss - fetch lightweight metadata from MCP server
        logger.info("Cache miss - fetching schema metadata from MCP server")
        
        # Get MCP client
        from mcp_client import get_backend_mcp_client
        mcp_client = get_backend_mcp_client()
        
        # Discover databases (lightweight operation)
        databases_result = await asyncio.wait_for(
            mcp_client.discover_databases(),
            timeout=15.0
        )
        
        if not databases_result or (isinstance(databases_result, dict) and databases_result.get("error")):
            raise HTTPException(status_code=500, detail="Failed to fetch database list")
        
        # Process databases
        databases = databases_result if isinstance(databases_result, list) else databases_result.get("databases", [])
        
        # Filter out system databases
        system_databases = {'INFORMATION_SCHEMA', 'PERFORMANCE_SCHEMA', 'mysql', 'sys', 'information_schema', 'performance_schema'}
        filtered_databases = [
            db for db in databases 
            if db.get("accessible", True) and db.get("name", "").upper() not in system_databases
        ]
        
        # For each database, get table list (lightweight operation) but NOT schemas
        database_metadata = []
        for db in filtered_databases:
            try:
                tables_result = await asyncio.wait_for(
                    mcp_client.discover_tables(db["name"]),
                    timeout=10.0
                )
                
                if tables_result and not (isinstance(tables_result, dict) and tables_result.get("error")):
                    tables = tables_result if isinstance(tables_result, list) else tables_result.get("tables", [])
                    database_metadata.append({
                        "name": db["name"],
                        "accessible": db.get("accessible", True),
                        "table_count": len(tables),
                        "table_names": [table.get("name", "") for table in tables[:50]]  # Limit to first 50 table names
                    })
                else:
                    logger.warning(f"Failed to get tables for database {db['name']}")
                    database_metadata.append({
                        "name": db["name"],
                        "accessible": db.get("accessible", True),
                        "table_count": 0,
                        "table_names": []
                    })
            except Exception as e:
                logger.warning(f"Error fetching tables for database {db['name']}: {e}")
                database_metadata.append({
                    "name": db["name"],
                    "accessible": db.get("accessible", True),
                    "table_count": 0,
                    "table_names": []
                })
        
        # Calculate basic metrics without fetching schemas
        total_tables = sum(db.get("table_count", 0) for db in database_metadata)
        available_databases = len([db for db in database_metadata if db.get("accessible", True)])
        
        # Build lightweight response with metadata only
        response_data = {
            "success": True,
            "mode": "fast_metadata_only",
            "metadata": {
                "total_databases": len(database_metadata),
                "available_databases": available_databases,
                "total_tables": total_tables,
                "databases": database_metadata
            },
            "note": "This is metadata-only response. Table schemas will be fetched on-demand during query processing.",
            "discovery_timestamp": datetime.now().isoformat(),
            "cache_hit": False
        }
        
        # Cache the result for future requests
        if redis_client:
            try:
                await redis_client.setex(
                    cache_key, 
                    cache_ttl, 
                    json.dumps(response_data, default=str)
                )
                logger.info(f"Schema discovery result cached for {cache_ttl} seconds")
            except Exception as cache_error:
                logger.warning(f"Cache write error: {cache_error}")
        
        return response_data
        
    except asyncio.TimeoutError:
        logger.error("Fast schema discovery timed out")
        raise HTTPException(status_code=504, detail="Fast schema discovery timed out")
    except Exception as e:
        logger.error(f"Fast schema discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Fast schema discovery failed: {str(e)}")


@app.get("/api/schema/cached")
async def get_cached_schema():
    """
    API endpoint to get schema from cache only (for fast access by agents).
    Returns cached schema if available, otherwise returns minimal fallback.
    """
    cache_key = "schema:discovery:fast"
    
    if not redis_client:
        # No Redis - return minimal fallback
        return {
            "success": True,
            "source": "fallback",
            "schema": {
                "tables_count": 0,
                "tables": []
            },
            "cache_available": False
        }
    
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            cached_result = json.loads(cached_data)
            logger.info("Cached schema served to agent")
            return {
                "success": True,
                "source": "cache",
                "schema": cached_result.get("schema", {}),
                "cache_available": True,
                "cached_at": cached_result.get("discovery_timestamp")
            }
        else:
            # Cache miss - return minimal fallback and suggest refresh
            logger.info("No cached schema available")
            return {
                "success": True,
                "source": "fallback",
                "schema": {
                    "tables_count": 0,
                    "tables": []
                },
                "cache_available": False,
                "suggestion": "Call /api/schema/discovery/fast to populate cache"
            }
    except Exception as e:
        logger.error(f"Error reading cached schema: {e}")
        return {
            "success": False,
            "source": "error",
            "error": str(e),
            "cache_available": False
        }


@app.get("/api/schema/discovery/{database_name}")
async def get_database_schema_discovery(database_name: str):
    """
    API endpoint for database-specific schema discovery.
    Returns discovered tables from a specific database only.
    """
    if not dynamic_schema_manager:
        raise HTTPException(
            status_code=503, 
            detail="Dynamic schema management not available"
        )
    
    try:
        # Add timeout to prevent hanging
        import asyncio
        
        # Get specific database schema
        schema_manager = dynamic_schema_manager.schema_manager
        
        # Check if database exists
        databases = await schema_manager.discover_databases()
        target_db = None
        for db in databases:
            if db.name == database_name:
                target_db = db
                break
        
        if not target_db:
            raise HTTPException(status_code=404, detail=f"Database '{database_name}' not found")
        
        # Get tables for the specific database
        tables = await asyncio.wait_for(
            schema_manager.get_tables(database_name),
            timeout=30.0
        )
        
        # Get table schemas in parallel
        semaphore = asyncio.Semaphore(8)
        
        async def get_table_schema_safe(table):
            async with semaphore:
                try:
                    return await schema_manager.get_table_schema(database_name, table.name)
                except Exception as e:
                    logger.warning(f"Failed to get schema for {database_name}.{table.name}: {e}")
                    return None
        
        table_schemas = await asyncio.wait_for(
            asyncio.gather(*[get_table_schema_safe(table) for table in tables], return_exceptions=True),
            timeout=120.0  # 2 minute timeout for database-specific discovery
        )
        
        # Filter out None results and exceptions
        valid_schemas = [schema for schema in table_schemas 
                       if schema is not None and not isinstance(schema, Exception)]
        
        return {
            "success": True,
            "database": database_name,
            "schema": {
                "tables_count": len(valid_schemas),
                "tables": [
                    {
                        "name": table.table if hasattr(table, 'table') else table.name,
                        "columns": [col.name for col in table.columns] if hasattr(table, 'columns') else []
                    }
                    for table in valid_schemas
                ]
            },
            "discovery_timestamp": datetime.now().isoformat()
        }
        
    except asyncio.TimeoutError:
        logger.error(f"Database schema discovery for '{database_name}' timed out")
        raise HTTPException(status_code=504, detail=f"Database schema discovery for '{database_name}' timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database schema discovery for '{database_name}' failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database schema discovery failed: {str(e)}")


@app.get("/api/schema/mappings/{business_term}")
async def get_business_term_mappings(business_term: str):
    """
    Get table and column mappings for a specific business metric using MCP server.
    Enhanced version that uses MCP server's schema intelligence capabilities.
    """
    try:
        # Use MCP client to get business mappings
        from mcp_client import get_backend_mcp_client
        mcp_client = get_backend_mcp_client()
        
        # Use MCP server's business mapping discovery for specific term
        result = await mcp_client.call_tool(
            "discover_business_mappings_tool",
            {
                "business_terms": [business_term],
                "confidence_threshold": 0.5
            }
        )
        
        if result and result.get("success"):
            term_mappings = result.get("mappings", {}).get(business_term, [])
            return term_mappings
        else:
            logger.warning(f"MCP mapping discovery failed for '{business_term}': {result.get('error') if result else 'No response'}")
            return []
        
        # Call the new MCP business mappings tool
        business_mappings_result = await mcp_client.call_tool(
            "discover_business_mappings_tool", 
            {
                "business_terms": [business_term],
                "confidence_threshold": 0.6
            }
        )
        
        if business_mappings_result and not business_mappings_result.get("error"):
            mappings = business_mappings_result.get("mappings", [])
            
            # Filter mappings for the specific business term
            term_mappings = [
                mapping for mapping in mappings 
                if mapping.get("business_term", "").lower() == business_term.lower()
            ]
            
            return {
                "success": True,
                "business_term": business_term,
                "mappings": term_mappings,
                "total_mappings": len(term_mappings),
                "confidence_threshold": 0.6,
                "source": "mcp_schema_intelligence"
            }
        else:
            error_msg = business_mappings_result.get("error", "Unknown error") if business_mappings_result else "No response from MCP server"
            logger.error(f"MCP business mappings failed: {error_msg}")
            # Fall back to dynamic schema manager
            return await get_metric_mappings(business_term)
            
    except Exception as e:
        logger.error(f"Error getting business term mappings via MCP: {e}")
        # Return empty list as fallback
        return []


@app.get("/api/schema/relationships")
async def get_schema_relationships():
    """
    Get table relationships and foreign key information using MCP server intelligence.
    """
    try:
        # Use MCP client to discover relationships
        from mcp_client import get_backend_mcp_client
        mcp_client = get_backend_mcp_client()
        
        # First get all databases
        databases_result = await mcp_client.call_tool("discover_databases_tool", {})
        
        if not databases_result or databases_result.get("error"):
            raise HTTPException(status_code=500, detail="Failed to discover databases")
        
        relationships = []
        relationship_stats = {
            "total_tables": 0,
            "tables_with_fks": 0,
            "total_relationships": 0,
            "databases_analyzed": 0
        }
        
        # Analyze each database for relationships
        for database in databases_result:
            if not database.get("accessible", True):
                continue
            
            db_name = database["name"]
            
            try:
                # Get tables in the database
                tables_result = await mcp_client.call_tool(
                    "discover_tables_tool", 
                    {"database": db_name}
                )
                
                if not tables_result or isinstance(tables_result, dict) and tables_result.get("error"):
                    continue
                
                relationship_stats["databases_analyzed"] += 1
                relationship_stats["total_tables"] += len(tables_result)
                
                # Analyze each table for foreign key relationships
                for table in tables_result:
                    table_name = table["name"]
                    
                    try:
                        # Get table schema including foreign keys
                        schema_result = await mcp_client.call_tool(
                            "get_table_schema_tool",
                            {"database": db_name, "table": table_name}
                        )
                        
                        if schema_result and not schema_result.get("error"):
                            foreign_keys = schema_result.get("foreign_keys", [])
                            
                            if foreign_keys:
                                relationship_stats["tables_with_fks"] += 1
                                relationship_stats["total_relationships"] += len(foreign_keys)
                                
                                # Add relationship information
                                for fk in foreign_keys:
                                    relationships.append({
                                        "source_database": db_name,
                                        "source_table": table_name,
                                        "source_column": fk.get("column"),
                                        "target_database": fk.get("referenced_database", db_name),
                                        "target_table": fk.get("referenced_table"),
                                        "target_column": fk.get("referenced_column"),
                                        "constraint_name": fk.get("constraint_name"),
                                        "relationship_type": "foreign_key"
                                    })
                    
                    except Exception as table_error:
                        logger.debug(f"Error analyzing table {db_name}.{table_name}: {table_error}")
                        continue
                        
            except Exception as db_error:
                logger.error(f"Error analyzing database {db_name}: {db_error}")
                continue
        
        return {
            "success": True,
            "relationships": relationships,
            "statistics": relationship_stats,
            "discovery_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Schema relationships discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to discover schema relationships: {str(e)}")


@app.post("/api/schema/optimize")
async def get_schema_optimizations(body: dict = None):
    """
    Get schema optimization suggestions using MCP server intelligence.
    """
    database = body.get("database") if body else None
    performance_threshold = body.get("performance_threshold", 0.5) if body else 0.5
    
    try:
        # Use MCP client to get optimization suggestions
        from mcp_client import get_backend_mcp_client
        mcp_client = get_backend_mcp_client()
        
        # Call the MCP schema optimization tool
        optimization_result = await mcp_client.call_tool(
            "suggest_schema_optimizations_tool", 
            {
                "database": database,
                "performance_threshold": performance_threshold
            }
        )
        
        if optimization_result and not optimization_result.get("error"):
            return {
                "success": True,
                "optimizations": optimization_result.get("optimizations", []),
                "total_suggestions": optimization_result.get("total_suggestions", 0),
                "performance_threshold": performance_threshold,
                "target_database": database or "all_databases",
                "source": "mcp_schema_intelligence"
            }
        else:
            error_msg = optimization_result.get("error", "Unknown error") if optimization_result else "No response from MCP server"
            raise HTTPException(status_code=500, detail=f"MCP optimization analysis failed: {error_msg}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Schema optimization analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze schema optimizations: {str(e)}")


@app.post("/api/schema/analyze-intent")
async def analyze_query_intent_endpoint(body: dict):
    """
    Analyze natural language query intent using MCP server intelligence.
    """
    query = body.get("query")
    context = body.get("context", {})
    
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query is required")
    
    try:
        # Use MCP client to analyze query intent
        from mcp_client import get_backend_mcp_client
        mcp_client = get_backend_mcp_client()
        
        # Call the MCP query intent analysis tool
        intent_result = await mcp_client.call_tool(
            "analyze_query_intent_tool", 
            {
                "natural_language_query": query,
                "context": context
            }
        )
        
        if intent_result and not intent_result.get("error"):
            return {
                "success": True,
                "query_intent": intent_result,
                "source": "mcp_schema_intelligence"
            }
        else:
            error_msg = intent_result.get("error", "Unknown error") if intent_result else "No response from MCP server"
            raise HTTPException(status_code=500, detail=f"MCP intent analysis failed: {error_msg}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query intent analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze query intent: {str(e)}")


@app.post("/api/schema/learn-mapping")
async def learn_successful_mapping(body: dict):
    """
    Learn from successful business term mappings using MCP server intelligence.
    """
    business_term = body.get("business_term")
    database_name = body.get("database_name")
    table_name = body.get("table_name")
    column_name = body.get("column_name")
    success_score = body.get("success_score", 1.0)
    
    if not all([business_term, database_name, table_name]):
        raise HTTPException(
            status_code=400, 
            detail="business_term, database_name, and table_name are required"
        )
    
    try:
        # Use MCP client to learn from successful mapping
        from mcp_client import get_backend_mcp_client
        mcp_client = get_backend_mcp_client()
        
        # Call the MCP learning tool
        learning_result = await mcp_client.call_tool(
            "learn_from_successful_mapping_tool", 
            {
                "business_term": business_term,
                "database_name": database_name,
                "table_name": table_name,
                "column_name": column_name,
                "success_score": success_score
            }
        )
        
        if learning_result and not learning_result.get("error"):
            return {
                "success": True,
                "learning_result": learning_result,
                "source": "mcp_schema_intelligence"
            }
        else:
            error_msg = learning_result.get("error", "Unknown error") if learning_result else "No response from MCP server"
            raise HTTPException(status_code=500, detail=f"MCP learning failed: {error_msg}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Learning from successful mapping failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to learn from mapping: {str(e)}")


@app.get("/api/schema/intelligence/stats")
async def get_schema_intelligence_statistics():
    """
    Get schema intelligence statistics using MCP server.
    """
    try:
        # Use MCP client to get schema intelligence stats
        from mcp_client import get_backend_mcp_client
        mcp_client = get_backend_mcp_client()
        
        # Call the MCP stats tool
        stats_result = await mcp_client.call_tool("get_schema_intelligence_stats_tool", {})
        
        if stats_result and not stats_result.get("error"):
            return {
                "success": True,
                "intelligence_stats": stats_result,
                "source": "mcp_schema_intelligence",
                "timestamp": datetime.now().isoformat()
            }
        else:
            error_msg = stats_result.get("error", "Unknown error") if stats_result else "No response from MCP server"
            raise HTTPException(status_code=500, detail=f"MCP stats retrieval failed: {error_msg}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Schema intelligence stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get intelligence stats: {str(e)}")


# Note: This endpoint is now replaced by /api/schema/mappings/{business_term} with MCP-driven approach


@app.get("/api/configuration/status")
async def get_configuration_status():
    """
    Get current configuration management status and settings.
    """
    try:
        status_info = {
            "dynamic_schema_available": DYNAMIC_SCHEMA_AVAILABLE,
            "components": {
                "dynamic_schema_manager": "available" if dynamic_schema_manager else "unavailable",
                "intelligent_query_builder": "available" if intelligent_query_builder else "unavailable",
                "configuration_manager": "available" if configuration_manager else "unavailable"
            },
            "mode": "dynamic" if dynamic_schema_manager else "static"
        }
        
        # Add component metrics if available
        if dynamic_schema_manager:
            status_info["schema_metrics"] = dynamic_schema_manager.get_metrics()
        
        if intelligent_query_builder:
            status_info["query_builder_metrics"] = intelligent_query_builder.get_metrics()
        
        return {
            "success": True,
            "configuration": status_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get configuration status: {e}")
        raise HTTPException(status_code=500, detail=f"Configuration status error: {str(e)}")


@app.post("/api/schema/invalidate")
async def invalidate_schema_cache(scope: str = "all"):
    """
    Invalidate schema cache to force fresh discovery.
    """
    if not dynamic_schema_manager:
        raise HTTPException(
            status_code=503,
            detail="Dynamic schema management not available"
        )
    
    try:
        await dynamic_schema_manager.invalidate_schema_cache(scope)
        
        return {
            "success": True,
            "message": f"Schema cache invalidated with scope: {scope}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Schema cache invalidation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cache invalidation failed: {str(e)}")


@app.get("/api/health/dynamic-schema")
async def get_dynamic_schema_health():
    """
    Health check specifically for dynamic schema management components.
    """
    health_status = {
        "dynamic_schema_available": DYNAMIC_SCHEMA_AVAILABLE,
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    # Check dynamic schema manager
    if dynamic_schema_manager:
        try:
            metrics = dynamic_schema_manager.get_metrics()
            health_status["components"]["schema_manager"] = {
                "status": "healthy",
                "metrics": metrics
            }
        except Exception as e:
            health_status["components"]["schema_manager"] = {
                "status": "unhealthy",
                "error": str(e)
            }
    else:
        health_status["components"]["schema_manager"] = {
            "status": "unavailable"
        }
    
    # Check intelligent query builder
    if intelligent_query_builder:
        try:
            metrics = intelligent_query_builder.get_metrics()
            health_status["components"]["query_builder"] = {
                "status": "healthy",
                "metrics": metrics
            }
        except Exception as e:
            health_status["components"]["query_builder"] = {
                "status": "unhealthy",
                "error": str(e)
            }
    else:
        health_status["components"]["query_builder"] = {
            "status": "unavailable"
        }
    
    # Overall health assessment
    component_statuses = [comp.get("status") for comp in health_status["components"].values()]
    if "unhealthy" in component_statuses:
        overall_status = "unhealthy"
    elif "unavailable" in component_statuses and DYNAMIC_SCHEMA_AVAILABLE:
        overall_status = "degraded"
    else:
        overall_status = "healthy"
    
    health_status["overall_status"] = overall_status
    
    return health_status


# Enhanced Agent Communication Functions with Circuit Breaker Protection

async def send_to_nlp_agent_protected(query: str, query_id: str) -> Dict[str, Any]:
    """Protected NLP agent call with retry logic"""
    return await retry_with_backoff(
        send_to_nlp_agent,
        nlp_retry_config,
        query,
        query_id
    )


async def send_to_nlp_agent_with_dynamic_context_protected(query: str, user_id: str, session_id: str) -> Dict[str, Any]:
    """Protected dynamic context NLP agent call with retry logic"""
    return await retry_with_backoff(
        send_to_nlp_agent_with_dynamic_context,
        nlp_retry_config,
        query,
        user_id,
        session_id
    )


async def send_to_data_agent_protected(sql_query: str, query_context: dict, query_id: str) -> Dict[str, Any]:
    """Protected data agent call with retry logic"""
    return await retry_with_backoff(
        send_to_data_agent,
        data_retry_config,
        sql_query,
        query_context,
        query_id
    )


async def send_to_viz_agent_protected(data: list, query_context: dict, query_id: str) -> Dict[str, Any]:
    """Protected viz agent call with retry logic"""
    return await retry_with_backoff(
        send_to_viz_agent,
        viz_retry_config,
        data,
        query_context,
        query_id
    )


# Update the existing send_to_nlp_agent function to include dynamic schema context
async def send_to_nlp_agent_with_dynamic_context(query: str, user_id: str, session_id: str, database_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Enhanced version of send_to_nlp_agent that includes dynamic schema context and database context.
    """
    nlp_agent_url = os.getenv("NLP_AGENT_URL", "http://nlp-agent:8001")
    
    try:
        # Generate query_id for this request
        query_id = f"q_{int(datetime.now().timestamp())}"
        
        # Prepare request with dynamic schema context and required fields
        request_data = {
            "query": query,
            "query_id": query_id,
            "user_id": user_id,
            "session_id": session_id,
            "context": {
                "source": "backend_gateway",
                "dynamic_schema_available": dynamic_schema_manager is not None,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Add database context if provided
        if database_context:
            request_data["database_context"] = database_context
            logger.info(f"Passing database context to NLP agent: {database_context.get('database_name', 'unknown')}")
        
        # Add schema context if available
        if dynamic_schema_manager:
            try:
                # Get relevant schema context based on query terms
                schema_context = {
                    "schema_version": None,
                    "available_metrics": list(dynamic_schema_manager.business_mappings.keys()) if hasattr(dynamic_schema_manager, 'business_mappings') else []
                }
                
                # Handle schema version carefully to avoid datetime serialization issues
                if hasattr(dynamic_schema_manager, 'metrics'):
                    schema_version = dynamic_schema_manager.metrics.get('last_schema_update')
                    if schema_version:
                        # Convert datetime to ISO string if needed
                        if hasattr(schema_version, 'isoformat'):
                            schema_context["schema_version"] = schema_version.isoformat()
                        else:
                            schema_context["schema_version"] = str(schema_version)
                
                request_data["context"]["schema_context"] = schema_context
            except Exception as e:
                logger.warning(f"Failed to add schema context: {e}")
        
        # Use aiohttp instead of httpx for consistency
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{nlp_agent_url}/process", json=request_data) as response:
                if response.status == 200:
                    return await response.json()  # Return NLP agent response as-is
                else:
                    error_text = await response.text()
                    logger.error(f"NLP agent returned status {response.status}: {error_text}")
                    return {
                        "error": f"NLP service error: {response.status}"
                    }
                
    except Exception as e:
        logger.error(f"Failed to communicate with NLP agent: {e}")
        return {
            "error": f"NLP communication failed: {str(e)}"
        }


# WebSocket endpoint for testing and general connections
@app.websocket("/ws")
async def websocket_test_endpoint(websocket: WebSocket):
    """WebSocket endpoint for testing and general communication"""
    await websocket.accept()
    
    try:
        logger.info("WebSocket test connection established")
        
        # Send connection established message
        await websocket.send_json({
            "type": "connection_established",
            "message": "WebSocket connection established",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type", "unknown")
            
            logger.info(f"Received WebSocket message: {message_type}")
            
            # Handle different message types
            if message_type.lower() in ["heartbeat", "ping"]:
                # Respond to heartbeat/ping
                await websocket.send_json({
                    "type": "heartbeat_response",
                    "timestamp": datetime.utcnow().isoformat(),
                    "correlation_id": data.get("correlation_id")
                })
            
            elif message_type == "test_agent_communication":
                # Handle test communication request
                await websocket.send_json({
                    "type": "test_response", 
                    "message": "Test agent communication received",
                    "correlation_id": data.get("correlation_id")
                })
            
            else:
                # Echo other messages
                await websocket.send_json({
                    "type": "echo",
                    "original_type": message_type,
                    "message": f"Received {message_type}",
                    "correlation_id": data.get("correlation_id")
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket test connection disconnected")
    except Exception as e:
        logger.error(f"WebSocket test error: {e}")


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
            
            elif message_type == "get_metrics":
                # Send orchestration metrics
                metrics = await orchestration_metrics.get_metrics()
                await websocket.send_json({
                    "type": "metrics",
                    "data": metrics,
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
# Helper functions for database context management
async def get_database_context(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve database context from Redis session"""
    if not redis_client:
        logger.warning("Redis not available, database context unavailable")
        return None
    
    try:
        context_key = f"db_context:{session_id}"  # Fixed prefix to match DatabaseContextManager
        logger.info(f"🔍 Looking for database context with key: {context_key}")
        
        # List all session keys for debugging
        all_keys = await redis_client.keys("db_context:*")
        logger.info(f"🔍 Available database context keys: {[key.decode() if isinstance(key, bytes) else key for key in all_keys]}")
        
        context_data = await redis_client.get(context_key)
        
        if context_data:
            database_context = json.loads(context_data)
            logger.info(f"✅ Retrieved database context for session {session_id}: {database_context.get('database_name', 'unknown')}")
            return database_context
        else:
            logger.warning(f"❌ No database context found for session {session_id}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to retrieve database context for session {session_id}: {e}")
        return None


async def set_database_context(session_id: str, database_context: Dict[str, Any]) -> bool:
    """Store database context in Redis session"""
    if not redis_client:
        logger.warning("Redis not available, cannot store database context")
        return False
    
    try:
        context_key = f"db_context:{session_id}"  # Fixed prefix to match DatabaseContextManager
        # Set with 1 hour expiration
        await redis_client.setex(
            context_key,
            3600,
            json.dumps(database_context, default=str)
        )
        logger.info(f"Stored database context for session {session_id}: {database_context.get('database_name', 'unknown')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store database context for session {session_id}: {e}")
        return False

# NOTE: This function is deprecated - use send_to_data_agent instead
# Direct SQL execution via MCP (replaces data-agent)
async def execute_sql_via_mcp(sql_query: str, query_context: dict, query_id: str) -> dict:
    """
    DEPRECATED: Execute SQL query directly via MCP server, bypassing data-agent
    This function is kept for backward compatibility but should not be used in the main workflow.
    Use send_to_data_agent() instead to follow the proper agent workflow.
    """
    logger.warning("DEPRECATED: Direct MCP execution bypasses data agent. Use send_to_data_agent() instead.")
    try:
        logger.info(f"Executing SQL via MCP for query {query_id}: {sql_query[:100]}...")
        
        from mcp_client import execute_mcp_query
        
        # Execute query through MCP server
        result = await execute_mcp_query(sql_query)
        
        if result.get("success"):
            processed_data = result.get("data", [])
            columns = result.get("columns", [])
            
            return {
                "success": True,
                "processed_data": processed_data,
                "columns": columns,
                "row_count": len(processed_data),
                "processing_time_ms": 200,
                "processing_method": "mcp_direct",
                "data_quality": {
                    "is_valid": len(processed_data) > 0,
                    "completeness": 1.0 if processed_data else 0.0,
                    "consistency": 1.0
                }
            }
        else:
            logger.error(f"MCP SQL execution failed: {result.get('error')}")
            return {
                "success": False,
                "error": result.get('error', 'Unknown MCP error'),
                "processed_data": [],
                "columns": [],
                "row_count": 0
            }
        
    except Exception as e:
        logger.error(f"Direct SQL execution via MCP failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "processed_data": [],
            "columns": [],
            "row_count": 0
        }


# NOTE: This function is deprecated - proper workflow should generate SQL through NLP agent
async def generate_mock_data_result(query_context: dict, query_id: str) -> dict:
    """
    DEPRECATED: Generate mock data when no SQL query is available
    This function is kept for backward compatibility but should not be used in the main workflow.
    The proper workflow should always generate SQL through the NLP agent.
    """
    logger.warning("DEPRECATED: Mock data generation indicates workflow failure. NLP agent should generate SQL.")
    try:
        intent = query_context.get("intent", {})
        metric_type = intent.get("metric_type", "revenue")
        
        # Generate appropriate mock data based on metric type
        if metric_type == "revenue":
            mock_data = [
                {"period": "2025-01", "revenue": 1200000},
                {"period": "2025-02", "revenue": 1350000},
                {"period": "2025-03", "revenue": 1180000},
                {"period": "2025-04", "revenue": 1420000},
                {"period": "2025-05", "revenue": 1380000}
            ]
            columns = ["period", "revenue"]
        elif metric_type == "cash_flow":
            mock_data = [
                {"period": "2025-01", "cash_flow": 450000},
                {"period": "2025-02", "cash_flow": 520000},
                {"period": "2025-03", "cash_flow": 480000}
            ]
            columns = ["period", "cash_flow"]
        else:
            mock_data = [
                {"category": "Sample Data", "value": 100},
                {"category": "Demo Results", "value": 150}
            ]
            columns = ["category", "value"]
        
        return {
            "success": True,
            "processed_data": mock_data,
            "columns": columns,
            "row_count": len(mock_data),
            "processing_time_ms": 50,
            "processing_method": "mock_fallback",
            "data_quality": {
                "is_valid": True,
                "completeness": 1.0,
                "consistency": 1.0
            },
            "warning": "Using sample data - no SQL query generated"
        }
        
    except Exception as e:
        logger.error(f"Mock data generation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "processed_data": [],
            "columns": [],
            "row_count": 0
        }


# NOTE: This function should only be used as fallback when viz agent is unavailable
def generate_visualization_config(data: list, query_context: dict) -> dict:
    """
    FALLBACK ONLY: Generate visualization configuration, replacing viz-agent
    This function should only be used as a fallback when the viz agent is unavailable.
    The proper workflow should route through send_to_viz_agent().
    """
    try:
        intent = query_context.get("intent", {})
        metric_type = intent.get("metric_type", "unknown")
        columns = [key for key in data[0].keys()] if data and len(data) > 0 else []
        
        # Determine appropriate chart type based on data structure
        chart_type = "table"  # default
        chart_title = "Query Results"
        
        if len(columns) == 2:
            # Two columns - likely time series or category data
            if any(col.lower() in ["period", "date", "time", "month", "year"] for col in columns):
                chart_type = "line_chart"
                chart_title = f"{metric_type.replace('_', ' ').title()} Trends"
            else:
                chart_type = "bar_chart"
                chart_title = f"{metric_type.replace('_', ' ').title()} by Category"
        elif len(columns) > 2:
            # Multiple columns - use table
            chart_type = "table"
            chart_title = f"{metric_type.replace('_', ' ').title()} Details"
        
        # Override with hint from intent if available
        visualization_hint = intent.get("visualization_hint")
        if visualization_hint and visualization_hint in ["line_chart", "bar_chart", "pie_chart", "table"]:
            chart_type = visualization_hint
        
        return {
            "success": True,
            "chart_config": {
                "chart_type": chart_type,
                "title": chart_title,
                "config": {
                    "responsive": True,
                    "maintainAspectRatio": False,
                    "data_columns": columns
                }
            },
            "processing_time_ms": 10,
            "processing_method": "direct_generation"
        }
        
    except Exception as e:
        logger.error(f"Visualization config generation failed: {e}")
        return {
            "success": True,  # Don't fail the entire query for viz issues
            "chart_config": {
                "chart_type": "table",
                "title": "Results",
                "config": {"responsive": True}
            },
            "processing_time_ms": 5,
            "processing_method": "fallback"
        }

# Agent Health Check Functions
async def check_agent_health(agent_url: str, agent_name: str) -> bool:
    """Check if an agent is healthy and responding"""
    try:
        timeout = aiohttp.ClientTimeout(total=5)  # Short timeout for health checks
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{agent_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    logger.debug(f"{agent_name} health check passed: {health_data.get('status', 'unknown')}")
                    return True
                else:
                    logger.warning(f"{agent_name} health check failed: HTTP {response.status}")
                    return False
    except Exception as e:
        logger.warning(f"{agent_name} health check failed: {e}")
        return False

async def check_all_agents_health() -> dict:
    """Check health of all agents before workflow execution"""
    nlp_agent_url = os.getenv("NLP_AGENT_URL", "http://nlp-agent:8001")
    data_agent_url = os.getenv("DATA_AGENT_URL", "http://data-agent:8002")  
    viz_agent_url = os.getenv("VIZ_AGENT_URL", "http://viz-agent:8003")
    
    # Check all agents concurrently
    nlp_healthy, data_healthy, viz_healthy = await asyncio.gather(
        check_agent_health(nlp_agent_url, "NLP Agent"),
        check_agent_health(data_agent_url, "Data Agent"),
        check_agent_health(viz_agent_url, "Viz Agent"),
        return_exceptions=True
    )
    
    # Handle any exceptions from health checks
    nlp_healthy = nlp_healthy if isinstance(nlp_healthy, bool) else False
    data_healthy = data_healthy if isinstance(data_healthy, bool) else False  
    viz_healthy = viz_healthy if isinstance(viz_healthy, bool) else False
    
    return {
        "nlp_agent": nlp_healthy,
        "data_agent": data_healthy,
        "viz_agent": viz_healthy,
        "all_healthy": nlp_healthy and data_healthy and viz_healthy
    }


# Agent Communication Functions
async def send_to_nlp_agent(query: str, query_id: str, session_id: Optional[str] = None, database_context: Optional[Dict[str, Any]] = None) -> dict:
    """Send query to NLP Agent for processing"""
    try:
        nlp_agent_url = os.getenv("NLP_AGENT_URL", "http://nlp-agent:8001")
        
        # Use provided database context or get it from session
        if not database_context and session_id:
            database_context = await get_database_context(session_id)
        
        payload = {
            "query": query,
            "query_id": query_id,
            "user_id": "anonymous",
            "session_id": session_id or f"session_{query_id}",
            "context": {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "backend_api"
            }
        }
        
        # Add database context if available
        if database_context:
            payload["database_context"] = database_context
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{nlp_agent_url}/process", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Validate and standardize the response
                    validated_response = validate_nlp_response(result)
                    if validated_response:
                        logger.info(f"NLP Agent processed query {query_id} successfully (validated)")
                        # Convert back to dict for backward compatibility
                        return validated_response.dict()
                    else:
                        logger.error(f"NLP Agent response validation failed for query {query_id}")
                        return {"error": "Invalid response format from NLP Agent"}
                else:
                    error_text = await response.text()
                    logger.error(f"NLP Agent error {response.status}: {error_text}")
                    return {"error": f"NLP Agent returned {response.status}: {error_text}"}
                    
    except asyncio.TimeoutError:
        logger.error(f"NLP Agent timeout for query {query_id}")
        return {"error": "NLP Agent timeout"}
    except Exception as e:
        logger.error(f"NLP Agent communication failed: {e}")
        # Fallback to simple query processing
        return await fallback_nlp_processing(query, query_id)


async def send_to_data_agent(sql_query: str, query_context: dict, query_id: str, session_id: Optional[str] = None) -> dict:
    """Send SQL query to Data Agent for execution"""
    try:
        data_agent_url = os.getenv("DATA_AGENT_URL", "http://data-agent:8002")
        
        # Get database context if session_id is provided
        database_context = None
        if session_id:
            database_context = await get_database_context(session_id)
        
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
        
        # Add database context if available
        if database_context:
            payload["database_context"] = database_context
        
        # Increase timeout to handle database connection issues
        timeout = aiohttp.ClientTimeout(total=120)  # Increased from 60 to 120 seconds
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{data_agent_url}/execute", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Validate and standardize the response
                    validated_response = validate_data_response(result)
                    if validated_response:
                        logger.info(f"Data Agent processed query {query_id} successfully (validated)")
                        # Convert back to dict for backward compatibility
                        return validated_response.dict()
                    else:
                        logger.error(f"Data Agent response validation failed for query {query_id}")
                        return {"success": False, "error": "Invalid response format from Data Agent"}
                else:
                    error_text = await response.text()
                    logger.error(f"Data Agent error {response.status}: {error_text}")
                    return {"success": False, "error": f"Data Agent returned {response.status}: {error_text}"}
                    
    except asyncio.TimeoutError:
        logger.error(f"Data Agent timeout for query {query_id}")
        return {"success": False, "error": "Data Agent timeout"}
    except Exception as e:
        logger.error(f"Data Agent communication failed: {e}")
        # Fallback to direct database query via MCP if data agent is unavailable
        return await fallback_data_processing(sql_query, query_context, query_id)


async def send_to_viz_agent(data: list, query_context: dict, query_id: str, session_id: Optional[str] = None) -> dict:
    """Send data to Visualization Agent for chart generation"""
    try:
        viz_agent_url = os.getenv("VIZ_AGENT_URL", "http://viz-agent:8003")
        
        # Get database context if session_id is provided
        database_context = None
        if session_id:
            database_context = await get_database_context(session_id)
        
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
        
        # Add database context if available
        if database_context:
            payload["database_context"] = database_context
        
        timeout = aiohttp.ClientTimeout(total=45)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{viz_agent_url}/visualize", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Validate and standardize the response
                    validated_response = validate_viz_response(result)
                    if validated_response:
                        logger.info(f"Viz Agent processed query {query_id} successfully (validated)")
                        # Convert back to dict for backward compatibility
                        return validated_response.dict()
                    else:
                        logger.error(f"Viz Agent response validation failed for query {query_id}")
                        return {"success": False, "error": "Invalid response format from Viz Agent"}
                else:
                    error_text = await response.text()
                    logger.error(f"Viz Agent error {response.status}: {error_text}")
                    return {"success": False, "error": f"Viz Agent returned {response.status}: {error_text}"}
                    
    except asyncio.TimeoutError:
        logger.error(f"Viz Agent timeout for query {query_id}")
        return {"success": False, "error": "Viz Agent timeout"}
    except Exception as e:
        logger.error(f"Viz Agent communication failed: {e}")
        # Don't fail the entire query for visualization issues, but return failure status
        return {"success": False, "error": f"Viz Agent communication failed: {str(e)}"}


# Enhanced Agent Communication Functions with WebSocket Support (Phase 1)
async def send_to_agent_enhanced(
    agent_type: AgentType, 
    message: Dict[str, Any], 
    timeout: float = 30.0
) -> Dict[str, Any]:
    """
    Enhanced agent communication using WebSocket manager with HTTP fallback
    
    Args:
        agent_type: Target agent type (NLP, DATA, VIZ)
        message: Message payload to send
        timeout: Request timeout in seconds
        
    Returns:
        Agent response dictionary
    """
    try:
        # Add metadata
        message.update({
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": f"{agent_type.value}_{int(datetime.utcnow().timestamp() * 1000)}",
            "source": "backend_enhanced"
        })
        
        # Use WebSocket manager for communication
        response = await websocket_agent_manager.send_message(
            agent_type=agent_type,
            message=message,
            timeout=timeout
        )
        
        logger.info(f"Enhanced communication with {agent_type.value} agent successful")
        return response
        
    except Exception as e:
        logger.error(f"Enhanced communication with {agent_type.value} agent failed: {e}")
        # Return structured error response
        return {
            "success": False,
            "error": {
                "type": "communication_error",
                "message": str(e),
                "agent": agent_type.value,
                "timestamp": datetime.utcnow().isoformat()
            }
        }


async def send_to_nlp_agent_enhanced(query: str, query_id: str, context: Optional[Dict] = None) -> Dict[str, Any]:
    """Enhanced NLP agent communication with WebSocket support"""
    
    message = {
        "type": "nlp_query",
        "query": query,
        "query_id": query_id,
        "context": context or {}
    }
    
    return await send_to_agent_enhanced(AgentType.NLP, message)


async def send_to_data_agent_enhanced(
    sql_query: str, 
    query_context: Dict, 
    query_id: str
) -> Dict[str, Any]:
    """Enhanced Data agent communication with WebSocket support"""
    
    message = {
        "type": "data_query",
        "sql_query": sql_query,
        "query_context": query_context,
        "query_id": query_id
    }
    
    return await send_to_agent_enhanced(AgentType.DATA, message)


async def send_to_viz_agent_enhanced(
    data: List[Dict], 
    query_context: Dict, 
    query_id: str
) -> Dict[str, Any]:
    """Enhanced Viz agent communication with WebSocket support"""
    
    message = {
        "type": "visualization_request",
        "data": data,
        "query_context": query_context,
        "query_id": query_id
    }
    
    return await send_to_agent_enhanced(AgentType.VIZ, message)


# Phase 2 Migration Functions
async def migrate_agent_to_websocket(agent_type: AgentType) -> Dict[str, Any]:
    """Enable WebSocket for specific agent (Phase 2 migration)"""
    try:
        websocket_agent_manager.enable_websocket_for_agent(agent_type)
        
        # Wait a moment for connection to establish
        await asyncio.sleep(2)
        
        # Test the connection
        test_message = {
            "type": "health_check",
            "test": True
        }
        
        response = await websocket_agent_manager.send_message(
            agent_type=agent_type,
            message=test_message,
            timeout=5.0
        )
        
        logger.info(f"Successfully migrated {agent_type.value} agent to WebSocket")
        
        return {
            "success": True,
            "agent": agent_type.value,
            "status": "migrated_to_websocket",
            "connection_test": response
        }
        
    except Exception as e:
        logger.error(f"Failed to migrate {agent_type.value} agent to WebSocket: {e}")
        
        # Rollback on failure
        websocket_agent_manager.disable_websocket_for_agent(agent_type)
        
        return {
            "success": False,
            "agent": agent_type.value,
            "error": str(e),
            "status": "migration_failed"
        }


async def rollback_agent_to_http(agent_type: AgentType) -> Dict[str, Any]:
    """Rollback agent from WebSocket to HTTP"""
    try:
        websocket_agent_manager.disable_websocket_for_agent(agent_type)
        
        logger.info(f"Successfully rolled back {agent_type.value} agent to HTTP")
        
        return {
            "success": True,
            "agent": agent_type.value,
            "status": "rolled_back_to_http"
        }
        
    except Exception as e:
        logger.error(f"Failed to rollback {agent_type.value} agent to HTTP: {e}")
        
        return {
            "success": False,
            "agent": agent_type.value,
            "error": str(e),
            "status": "rollback_failed"
        }


# Agent Management Endpoints for Phase 2
@app.get("/api/agent/stats")
@limiter.limit("30/minute")
async def get_agent_stats(request: Request):
    """Get WebSocket connection statistics for all agents"""
    try:
        stats = websocket_agent_manager.get_agent_stats()
        
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get agent stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/{agent_name}/migrate-websocket")
@limiter.limit("5/minute")
async def migrate_agent_websocket(request: Request, agent_name: str):
    """Migrate specific agent to WebSocket (Phase 2)"""
    try:
        # Map agent name to AgentType
        agent_mapping = {
            "nlp": AgentType.NLP,
            "data": AgentType.DATA,
            "viz": AgentType.VIZ
        }
        
        if agent_name.lower() not in agent_mapping:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid agent name: {agent_name}"
            )
        
        agent_type = agent_mapping[agent_name.lower()]
        result = await migrate_agent_to_websocket(agent_type)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to migrate agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/{agent_name}/rollback-http")
@limiter.limit("5/minute")
async def rollback_agent_http(request: Request, agent_name: str):
    """Rollback specific agent from WebSocket to HTTP"""
    try:
        # Map agent name to AgentType
        agent_mapping = {
            "nlp": AgentType.NLP,
            "data": AgentType.DATA,
            "viz": AgentType.VIZ
        }
        
        if agent_name.lower() not in agent_mapping:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid agent name: {agent_name}"
            )
        
        agent_type = agent_mapping[agent_name.lower()]
        result = await rollback_agent_to_http(agent_type)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rollback agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    """Fallback data processing using MCP server when data agent is unavailable"""
    logger.warning(f"Using fallback data processing via MCP for query {query_id}")
    
    try:
        from mcp_client import execute_mcp_query
        
        # Execute query through MCP server
        result = await execute_mcp_query(sql_query)
        
        if result.get("success"):
            processed_data = result.get("data", [])
            columns = result.get("columns", [])
            
            return {
                "success": True,
                "processed_data": processed_data,
                "columns": columns,
                "row_count": len(processed_data),
                "processing_time_ms": 200,
                "processing_method": "mcp_fallback",
                "data_quality": {
                    "is_valid": len(processed_data) > 0,
                    "completeness": 1.0 if processed_data else 0.0,
                    "consistency": 1.0
                }
            }
        else:
            logger.error(f"MCP fallback processing failed: {result.get('error')}")
            
            # Return mock data as last resort to keep the UI functional
            mock_data = [
                {"period": "2025-01", "revenue": 1200000},
                {"period": "2025-02", "revenue": 1350000},
                {"period": "2025-03", "revenue": 1180000},
                {"period": "2025-04", "revenue": 1420000},
                {"period": "2025-05", "revenue": 1380000}
            ]
            
            return {
                "success": True,
                "processed_data": mock_data,
                "columns": ["period", "revenue"],
                "row_count": len(mock_data),
                "processing_time_ms": 50,
                "processing_method": "mock_fallback",
                "data_quality": {
                    "is_valid": True,
                    "completeness": 1.0,
                    "consistency": 1.0
                },
                "warning": "Using sample data due to MCP server connectivity issues"
            }
        
    except Exception as e:
        logger.error(f"MCP fallback data processing failed: {e}")
        
        # Return mock data as last resort to keep the UI functional
        mock_data = [
            {"period": "2025-01", "revenue": 1200000},
            {"period": "2025-02", "revenue": 1350000},
            {"period": "2025-03", "revenue": 1180000},
            {"period": "2025-04", "revenue": 1420000},
            {"period": "2025-05", "revenue": 1380000}
        ]
        
        return {
            "success": True,
            "processed_data": mock_data,
            "columns": ["period", "revenue"],
            "row_count": len(mock_data),
            "processing_time_ms": 50,
            "processing_method": "mock_fallback",
            "data_quality": {
                "is_valid": True,
                "completeness": 1.0,
                "consistency": 1.0
            },
            "warning": "Using sample data due to database connectivity issues"
        }


def create_default_visualization(data: list) -> dict:
    """Create default visualization when viz agent fails"""
    # Determine appropriate chart type based on data structure
    if not data or len(data) == 0:
        chart_type = "table"
        title = "No Data Available"
    else:
        first_row = data[0]
        if isinstance(first_row, dict):
            columns = list(first_row.keys())
            # If we have time series data (period, date, etc.)
            time_columns = [col for col in columns if any(time_word in col.lower() for time_word in ['period', 'date', 'time', 'month', 'year'])]
            numeric_columns = [col for col in columns if not time_columns or col != time_columns[0]]
            
            if time_columns and numeric_columns:
                chart_type = "line"
                title = "Time Series Data"
            elif len(columns) <= 2:
                chart_type = "bar"
                title = "Comparison Chart"
            else:
                chart_type = "table"
                title = "Data Table"
        else:
            chart_type = "table"
            title = "Query Results"
    
    return {
        "success": True,
        "chart_config": {
            "chart_type": chart_type,
            "title": title,
            "responsive": True,
            "maintainAspectRatio": False
        },
        "chart_data": {
            "datasets": [{"data": data}] if data else [],
            "labels": []
        },
        "chart_html": None,
        "chart_json": {"type": chart_type, "data": data},
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


async def generate_sql_from_intent_dynamic(intent: QueryIntent) -> tuple[str, tuple]:
    """
    Generate SQL query from query intent using dynamic schema management.
    Falls back to static generation if dynamic schema is not available.
    """
    global dynamic_schema_manager, intelligent_query_builder
    
    # Try dynamic schema management first
    if intelligent_query_builder and dynamic_schema_manager:
        try:
            logger.info(f"Using dynamic schema management for SQL generation: {intent.metric_type}")
            
            # Convert QueryIntent to dict for intelligent query builder
            intent_dict = {
                'metric_type': intent.metric_type,
                'time_period': intent.time_period,
                'aggregation_level': intent.aggregation_level,
                'filters': getattr(intent, 'filters', {}),
                'comparison_periods': getattr(intent, 'comparison_periods', []),
                'limit': 1000
            }
            
            # Build query using intelligent query builder
            query_result = await intelligent_query_builder.build_query(intent_dict)
            
            logger.info(
                f"Dynamic SQL generated with confidence: {query_result.confidence_score:.2f}"
            )
            
            # Return SQL and empty parameters (as dynamic builder handles parameters differently)
            return query_result.sql, ()
            
        except Exception as e:
            logger.warning(f"Dynamic SQL generation failed: {e}, falling back to static")
    
    # Fallback to static SQL generation
    logger.info(f"Using static SQL generation for metric: {intent.metric_type}")
    return generate_sql_from_intent_static(intent)


def generate_sql_from_intent_static(intent: QueryIntent) -> tuple[str, tuple]:
    """Static SQL generation for fallback compatibility."""
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


# Legacy wrapper for backward compatibility
def generate_sql_from_intent(intent: QueryIntent) -> tuple[str, tuple]:
    """Legacy wrapper - redirects to static version for synchronous calls."""
    return generate_sql_from_intent_static(intent)


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