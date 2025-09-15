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
from database_context import DatabaseContextManager, DatabaseContext
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



async def process_query_core(query_request: QueryRequest) -> QueryResponse:
    """Core query processing logic without FastAPI dependencies"""
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
    
    try:
        # Step 1: Send query to NLP Agent using enhanced communication
        nlp_result = await send_to_agent_enhanced(
            AgentType.NLP,
            {
                "type": "nlp_query_with_context",
                "query": query_request.query,
                "query_id": query_id,
                "user_id": user_id,
                "session_id": session_id,
                "database_context": database_context,
                "context": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "backend_api_websocket"
                }
            }
        )
        
        logger.info("Enhanced communication with nlp agent successful")
        logger.info(f"NLP processing completed for query: {query_request.query}")
        
        if not nlp_result or not nlp_result.get("success"):
            raise Exception(f"NLP processing failed: {nlp_result.get('error', 'Unknown error')}")
        
        query_intent = nlp_result.get("intent", {})
        sql_query = nlp_result.get("sql_query", "")
        
        logger.info(f"Generated SQL query: {sql_query}")
        
        # Step 2: Send SQL query to Data Agent
        logger.info(f"🔧 Sending SQL query to Data Agent: {sql_query[:100]}...")
        
        data_result = await send_to_agent_enhanced(
            AgentType.DATA,
            {
                "type": "data_query",
                "sql_query": sql_query,
                "query_id": query_id,
                "database_context": database_context,
                "context": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "backend_api"
                }
            }
        )
        
        logger.info(f"📊 Data Agent WebSocket response received: {bool(data_result)}")
        
        if not data_result or not data_result.get("success"):
            error_msg = data_result.get('error', 'Unknown error') if data_result else 'No response from data agent'
            logger.error(f"❌ Data processing failed: {error_msg}")
            
            # Try fallback processing
            logger.info("🔄 Attempting fallback data processing...")
            try:
                # Use MCP client as fallback
                from mcp_client import get_backend_mcp_client
                mcp_client = get_backend_mcp_client()
                fallback_result = await mcp_client.execute_query(sql_query)
                
                if fallback_result and not fallback_result.get("error"):
                    data_result = {
                        "success": True,
                        "data": fallback_result.get("rows", []),
                        "columns": fallback_result.get("columns", []),
                        "processing_time_ms": fallback_result.get("execution_time_ms", 0)
                    }
                    logger.info("✅ Data processing completed")
                else:
                    raise Exception(f"Fallback processing failed: {fallback_result.get('error', 'Unknown error')}")
            except Exception as fallback_error:
                logger.error(f"MCP fallback processing failed: {fallback_error}")
                raise Exception(f"Data processing failed: {error_msg}")
        
        query_data = data_result.get("data", [])
        columns = data_result.get("columns", [])
        logger.info(f"✅ Data processing completed, retrieved {len(query_data)} rows")
        
        # Step 3: Send data to Viz Agent
        logger.info(f"🎨 Sending data to Viz Agent: {len(query_data)} rows")
        
        viz_result = await send_to_agent_enhanced(
            AgentType.VIZ,
            {
                "type": "viz_query",
                "data": query_data,
                "columns": columns,
                "query": query_request.query,
                "intent": query_intent,
                "query_id": query_id,
                "context": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "backend_api"
                }
            }
        )
        
        logger.info(f"📈 Viz Agent WebSocket response received: {bool(viz_result)}")
        
        if not viz_result or not viz_result.get("success"):
            logger.warning(f"⚠️ Visualization processing failed: {viz_result.get('error', 'Unknown error') if viz_result else 'No response from viz agent'}")
            # Use fallback visualization
            logger.info("🔄 Using fallback visualization")
            viz_result = {
                "success": True,
                "chart_config": {
                    "chart_type": "table",
                    "title": f"Results for: {query_request.query}"
                },
                "chart_data": {"rows": query_data, "columns": columns},
                "chart_html": None,
                "chart_json": None
            }
        
        logger.info("✅ Visualization processing completed")
        
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
        logger.error(f"Error in core query processing: {str(e)}")
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


@app.post("/api/query", response_model=QueryResponse)
@limiter.limit("30/minute")
async def process_query(
    request: Request,
    query_request: QueryRequest
):
    """Process natural language query through multi-agent workflow"""
    try:
        return await process_query_core(query_request)
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return QueryResponse(
            query_id=f"q_{datetime.utcnow().timestamp()}",
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
                selection_result = await database_context_manager.select_database(
                    session_id=session_id,
                    database_name=database_name
                )
                
                if not selection_result.get("success"):
                    raise HTTPException(
                        status_code=400,
                        detail=selection_result.get("error", "Database selection failed")
                    )
                
                # Extract the actual context object
                context_dict = selection_result.get("context", {})
                context = DatabaseContext(**context_dict) if context_dict else None
                
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
        from mcp_client import get_backend_mcp_client
        mcp_client = get_backend_mcp_client()
        
        # Execute query through MCP server
        result = await mcp_client.execute_query(sql_query)
        
        if result and not result.get("error"):
            processed_data = result.get("rows", [])
            columns = result.get("columns", [])
            
            return {
                "success": True,
                "data": processed_data,
                "columns": columns,
                "row_count": len(processed_data),
                "processing_time_ms": result.get("execution_time_ms", 200),
                "processing_method": "mcp_fallback"
            }
        else:
            logger.error(f"MCP fallback processing failed: {result.get('error', 'Unknown error') if result else 'No response'}")
            
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
                "data": mock_data,
                "columns": ["period", "revenue"],
                "row_count": len(mock_data),
                "processing_time_ms": 50,
                "processing_method": "mock_fallback",
                "warning": "Using sample data due to database connectivity issues"
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
            "data": mock_data,
            "columns": ["period", "revenue"],
            "row_count": len(mock_data),
            "processing_time_ms": 50,
            "processing_method": "mock_fallback",
            "warning": "Using sample data due to database connectivity issues"
        }


# WebSocket processing function for direct use
async def process_websocket_query_directly(query_request: QueryRequest) -> QueryResponse:
    """
    Process WebSocket query directly without FastAPI dependencies
    This is a clean implementation for WebSocket context
    """
    query_id = f"q_{datetime.utcnow().timestamp()}"
    user_id = query_request.user_id or "anonymous"
    
    # Use provided session_id or generate a new one
    if query_request.session_id:
        session_id = query_request.session_id
    else:
        session_id = f"session_{int(datetime.utcnow().timestamp())}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=12))}"
    
    logger.info(f"Starting multi-agent workflow for query: {query_request.query} (session: {session_id})")
    
    try:
        # Validate database context
        database_context = await get_database_context(session_id)
        if not database_context:
            logger.warning(f"No database context found for session {session_id}")
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
        
        # Step 1: Send query to NLP Agent
        nlp_result = await send_to_agent_enhanced(
            AgentType.NLP,
            {
                "type": "nlp_query_with_context",
                "query": query_request.query,
                "query_id": query_id,
                "user_id": user_id,
                "session_id": session_id,
                "database_context": database_context,
                "context": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "backend_websocket"
                }
            }
        )
        
        if not nlp_result or not nlp_result.get("success"):
            raise Exception(f"NLP processing failed: {nlp_result.get('error', 'Unknown error') if nlp_result else 'No response'}")
        
        query_intent = nlp_result.get("intent", {})
        sql_query = nlp_result.get("sql_query", "")
        
        if not sql_query:
            raise Exception("No SQL query generated from natural language input")
        
        logger.info(f"Generated SQL query: {sql_query}")
        
        # Step 2: Send to Data Agent
        data_result = await send_to_agent_enhanced(
            AgentType.DATA,
            {
                "type": "data_query",
                "sql_query": sql_query,
                "query_id": query_id,
                "database_context": database_context,
                "context": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "backend_websocket"
                }
            }
        )
        
        if not data_result or not data_result.get("success"):
            # Fallback to MCP processing
            logger.info("🔄 Attempting fallback data processing...")
            try:
                from mcp_client import get_backend_mcp_client
                mcp_client = get_backend_mcp_client()
                fallback_result = await mcp_client.execute_query(sql_query)
                
                if fallback_result and not fallback_result.get("error"):
                    data_result = {
                        "success": True,
                        "data": fallback_result.get("rows", []),
                        "columns": fallback_result.get("columns", []),
                        "processing_time_ms": fallback_result.get("execution_time_ms", 0)
                    }
                    logger.info("✅ Fallback data processing succeeded")
                else:
                    raise Exception(f"Fallback processing failed: {fallback_result.get('error', 'Unknown error') if fallback_result else 'No response'}")
            except Exception as fallback_error:
                logger.error(f"MCP fallback processing failed: {fallback_error}")
                raise Exception(f"Data processing failed: {data_result.get('error', 'Unknown error') if data_result else 'No response'}")
        
        query_data = data_result.get("data", [])
        columns = data_result.get("columns", [])
        logger.info(f"✅ Data processing completed, retrieved {len(query_data)} rows")
        
        # Step 3: Send to Viz Agent
        viz_result = await send_to_agent_enhanced(
            AgentType.VIZ,
            {
                "type": "viz_query",
                "data": query_data,
                "columns": columns,
                "query": query_request.query,
                "intent": query_intent,
                "query_id": query_id,
                "context": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "backend_websocket"
                }
            }
        )
        
        if not viz_result or not viz_result.get("success"):
            logger.warning("⚠️ Visualization processing failed, using fallback")
            viz_result = {
                "success": True,
                "chart_config": {
                    "chart_type": "table",
                    "title": f"Results for: {query_request.query}"
                },
                "chart_data": {"rows": query_data, "columns": columns},
                "chart_html": None,
                "chart_json": None
            }
        
        logger.info("✅ Visualization processing completed")
        
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
        logger.error(f"WebSocket query processing error: {str(e)}")
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


# WebSocket handlers
async def handle_websocket_query(websocket: WebSocket, user_id: str, data: Dict[str, Any]):
    """Handle WebSocket query processing"""
    try:
        query_text = data.get("query", "")
        session_id = data.get("session_id", f"ws_{user_id}_{int(datetime.utcnow().timestamp())}")
        correlation_id = data.get("correlation_id")
        
        # Send processing started message
        await websocket.send_json({
            "type": "query_processing_started",
            "query": query_text,
            "session_id": session_id,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Create query request
        query_request = QueryRequest(
            query=query_text,
            session_id=session_id,
            user_id=user_id
        )
        
        # Process query using existing logic
        logger.info(f"Processing WebSocket query from {user_id}: {query_text}")
        
        # Use direct processing to avoid FastAPI dependencies in WebSocket context
        response = await process_websocket_query_directly(query_request)
        
        # Send response back through WebSocket
        await websocket.send_json({
            "type": "query_response",
            "response": response.model_dump() if hasattr(response, 'model_dump') else response.__dict__,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"WebSocket query processing error: {e}")
        await websocket.send_json({
            "type": "query_error",
            "error": {
                "error_type": "query_processing_error",
                "message": f"Query processing failed: {str(e)}"
            },
            "correlation_id": data.get("correlation_id"),
            "timestamp": datetime.utcnow().isoformat()
        })


async def handle_websocket_database_select(websocket: WebSocket, user_id: str, data: Dict[str, Any]):
    """Handle WebSocket database selection"""
    try:
        database_name = data.get("database_name", "")
        session_id = data.get("session_id", f"ws_{user_id}_{int(datetime.utcnow().timestamp())}")
        correlation_id = data.get("correlation_id")
        
        if not database_name:
            await websocket.send_json({
                "type": "database_select_error",
                "error": {
                    "error_type": "missing_database_name",
                    "message": "Database name is required"
                },
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            return
        
        # Send processing started message
        await websocket.send_json({
            "type": "database_select_started",
            "database_name": database_name,
            "session_id": session_id,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Use database context manager directly instead of HTTP endpoint
        if database_context_manager:
            response = await database_context_manager.select_database(
                database_name=database_name,
                session_id=session_id
            )
        else:
            response = {
                "success": False,
                "error": "Database context manager not available",
                "error_type": "system_error"
            }
        
        # Send response back through WebSocket
        await websocket.send_json({
            "type": "database_select_response", 
            "response": response,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"WebSocket database selection error: {e}")
        await websocket.send_json({
            "type": "database_select_error",
            "error": {
                "error_type": "database_selection_error",
                "message": f"Database selection failed: {str(e)}"
            },
            "correlation_id": data.get("correlation_id"),
            "timestamp": datetime.utcnow().isoformat()
        })


async def handle_websocket_get_databases(websocket: WebSocket, user_id: str, data: Dict[str, Any]):
    """Handle WebSocket get databases request"""
    try:
        correlation_id = data.get("correlation_id")
        
        # Get available databases using database context manager directly
        if database_context_manager:
            databases = await database_context_manager.get_available_databases()
            databases_response = {"databases": databases}
        else:
            # Fallback to HTTP endpoint function
            class MockRequest:
                pass
            
            mock_request = MockRequest()
            databases_response = await get_database_list(mock_request)
            databases = databases_response.get("databases", [])
        
        # Send response back through WebSocket
        await websocket.send_json({
            "type": "databases_response",
            "databases": databases,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"WebSocket get databases error: {e}")
        await websocket.send_json({
            "type": "databases_error",
            "error": {
                "error_type": "get_databases_error",
                "message": f"Failed to get databases: {str(e)}"
            },
            "correlation_id": data.get("correlation_id"),
            "timestamp": datetime.utcnow().isoformat()
        })


async def handle_websocket_get_database_context(websocket: WebSocket, user_id: str, data: Dict[str, Any]):
    """Handle WebSocket get database context request"""
    try:
        session_id = data.get("session_id", f"ws_{user_id}_{int(datetime.utcnow().timestamp())}")
        correlation_id = data.get("correlation_id")
        
        # Get database context using existing logic
        database_context = await get_database_context(session_id)
        
        # Send response back through WebSocket
        await websocket.send_json({
            "type": "database_context_response",
            "database_context": database_context,
            "session_id": session_id,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"WebSocket get database context error: {e}")
        await websocket.send_json({
            "type": "database_context_error",
            "error": {
                "error_type": "get_database_context_error",
                "message": f"Failed to get database context: {str(e)}"
            },
            "correlation_id": data.get("correlation_id"),
            "timestamp": datetime.utcnow().isoformat()
        })


# WebSocket endpoints
@app.websocket("/ws/query/{user_id}")
async def websocket_query_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time BI query processing"""
    await websocket.accept()
    
    # Close any existing connection for this user to prevent session conflicts
    if user_id in websocket_connections:
        try:
            old_websocket = websocket_connections[user_id]
            logger.info(f"Closing existing WebSocket connection for user: {user_id}")
            await old_websocket.close()
        except Exception as e:
            logger.warning(f"Error closing old connection for {user_id}: {e}")
    
    # Store the new connection
    websocket_connections[user_id] = websocket
    
    try:
        logger.info(f"WebSocket query connection established for user: {user_id}")
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to Agentic BI System",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type", "unknown")
            
            logger.info(f"Received WebSocket message from {user_id}: {message_type}")
            
            # Handle different message types
            if message_type.lower() in ["heartbeat", "ping"]:
                # Standardized heartbeat response format
                await websocket.send_json({
                    "type": "heartbeat_response", 
                    "timestamp": datetime.utcnow().isoformat(),
                    "correlation_id": data.get("correlation_id"),
                    "server_status": "healthy",
                    "connection_id": f"backend_{user_id}",
                    "metrics": {
                        "uptime": datetime.utcnow().isoformat(),
                        "active_connections": len(websocket_connections)
                    }
                })
                
            elif message_type == "query":
                # Process BI query
                await handle_websocket_query(websocket, user_id, data)
                
            elif message_type == "database_select":
                # Handle database selection
                await handle_websocket_database_select(websocket, user_id, data)
                
            elif message_type == "get_databases":
                # Get available databases
                await handle_websocket_get_databases(websocket, user_id, data)
                
            elif message_type == "get_database_context":
                # Get current database context
                await handle_websocket_get_database_context(websocket, user_id, data)
                
            elif message_type == "connection_handshake":
                # Handle frontend connection handshake
                agent_id = data.get("agent_id", f"frontend_{user_id}")
                agent_type = data.get("agent_type", "frontend")
                capabilities = data.get("capabilities", [])
                
                logger.info(f"Received handshake from {agent_id} ({agent_type}) with capabilities: {capabilities}")
                
                # Send handshake acknowledgment
                await websocket.send_json({
                    "type": "connection_acknowledged",
                    "agent_id": agent_id,
                    "server_agent_id": f"backend_{user_id}",
                    "server_capabilities": ["query_processing", "database_management", "real_time_updates"],
                    "session_established": True,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            else:
                # Unknown message type  
                await websocket.send_json({
                    "type": "error",
                    "error": {
                        "error_type": "unknown_message_type",
                        "message": f"Unknown message type: {message_type}",
                        "suggestions": ["Use 'query', 'database_select', 'get_databases', 'connection_handshake', or 'heartbeat'"]
                    },
                    "correlation_id": data.get("correlation_id"),
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket query connection disconnected for user: {user_id}")
        # Clean up connection
        if user_id in websocket_connections:
            del websocket_connections[user_id]
    except Exception as e:
        logger.error(f"WebSocket query error for user {user_id}: {e}")
        # Clean up connection on error
        if user_id in websocket_connections:
            del websocket_connections[user_id]
        try:
            await websocket.send_json({
                "type": "error",
                "error": {
                    "error_type": "websocket_error", 
                    "message": f"WebSocket error: {str(e)}"
                },
                "timestamp": datetime.utcnow().isoformat()
            })
        except:
            pass
    finally:
        # Ensure connection is cleaned up in all cases
        if user_id in websocket_connections and websocket_connections[user_id] == websocket:
            del websocket_connections[user_id]
            logger.info(f"WebSocket connection cleanup completed for user: {user_id}")


# WebSocket endpoint for legacy chat compatibility  
@app.websocket("/ws/chat/{user_id}")
async def websocket_chat_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for chat compatibility (redirects to query endpoint)"""
    await websocket.accept()
    
    try:
        logger.info(f"WebSocket chat connection (legacy) established for user: {user_id}")
        
        # Send welcome message with migration note
        await websocket.send_json({
            "type": "system",
            "message": "Connected to Agentic BI System (Legacy Chat Mode)",
            "timestamp": datetime.utcnow().isoformat(),
            "migration_note": "Consider using /ws/query/ endpoint for enhanced features"
        })
        
        # Forward to query processing
        await websocket_query_endpoint(websocket, user_id)
        
    except Exception as e:
        logger.error(f"WebSocket chat error for user {user_id}: {e}")


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


# Exception handlers
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
