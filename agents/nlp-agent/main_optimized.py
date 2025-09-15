"""
Enhanced NLP Agent v2.2.0 with advanced reliability, performance optimization, and monitoring
"""
import asyncio
import json
import logging
import os
import psutil
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv
import websockets.exceptions

from src.optimized_nlp_agent import OptimizedNLPAgent
from src.enhanced_websocket_client import EnhancedWebSocketMCPClient
from src.hybrid_mcp_operations_adapter import HybridMCPOperationsAdapter
from src.enhanced_monitoring import EnhancedMonitoringSystem
# Query classifier removed - using unified processing approach
# PerformanceOptimizer removed - using AdvancedCacheManager directly
from performance_config import PerformanceConfig

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Enhanced NLP Agent v2.2.0",
    version="2.2.0",
    description="NLP Agent with enhanced reliability, performance optimization, and comprehensive monitoring"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instances
nlp_agent: OptimizedNLPAgent = None
websocket_client: EnhancedWebSocketMCPClient = None
hybrid_mcp_client: HybridMCPOperationsAdapter = None
# query_classifier removed - using unified processing approach
# performance_optimizer removed - using AdvancedCacheManager directly
monitoring_system: EnhancedMonitoringSystem = None

# WebSocket server for backend communication
active_websocket_connections: Dict[str, WebSocket] = {}

# Request/Response models
class ProcessRequest(BaseModel):
    query: str = Field(..., description="Natural language query to process")
    query_id: str = Field(..., description="Unique query identifier")
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    database_context: Optional[Dict[str, Any]] = Field(None, description="Database context for query processing")
    force_comprehensive: bool = Field(False, description="Force comprehensive processing path")
    use_cache: bool = Field(True, description="Enable semantic caching")
    timeout: int = Field(180, description="Request timeout in seconds")

class ProcessResponse(BaseModel):
    query: str
    intent: Dict[str, Any]
    entities: Dict[str, Any]
    sql_query: str
    explanation: str
    complexity: str
    processing_path: str
    execution_time: float
    cache_hit: bool
    timestamp: str
    success: bool = True

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    uptime: float
    connections: Dict[str, Any]
    performance_metrics: Dict[str, Any]

@app.on_event("startup")
async def startup_event():
    """Initialize the enhanced NLP agent with all optimization features"""
    global nlp_agent, websocket_client, monitoring_system
    
    try:
        logger.info("Starting Enhanced NLP Agent v2.2.0...")
        
        # Initialize monitoring system first
        async def alert_handler(alert):
            logger.error(f"ALERT [{alert.level.value.upper()}]: {alert.message}")
        
        monitoring_system = EnhancedMonitoringSystem(
            metrics_retention_hours=24,
            snapshot_interval_seconds=30,
            alert_handlers=[alert_handler]
        )
        await monitoring_system.start()
        
        # Get environment-specific performance configuration
        environment = os.getenv("ENVIRONMENT", "development")
        perf_config = PerformanceConfig.get_config(environment)
        logger.info(f"Using performance configuration for: {environment}")
        
        # Performance optimization now handled by AdvancedCacheManager in NLP agent
        
        # Initialize query classifier
        # QueryClassifier removed - using unified processing approach
        
        # Initialize MCP communication
        kimi_api_key = os.getenv("KIMI_API_KEY")
        if not kimi_api_key:
            raise ValueError("KIMI_API_KEY environment variable is required")
            
        mcp_server_ws_url = os.getenv("MCP_SERVER_WS_URL", "ws://tidb-mcp-server:8000/ws")
        mcp_server_http_url = os.getenv("MCP_SERVER_HTTP_URL", "http://tidb-mcp-server:8000")
        
        # Get WebSocket configuration from performance config
        websocket_config = perf_config["websocket"]
        
        # Initialize hybrid MCP client (WebSocket-first with HTTP fallback)
        hybrid_mcp_client = HybridMCPOperationsAdapter(
            ws_url=mcp_server_ws_url,
            http_url=mcp_server_http_url,
            agent_id="nlp-agent-001",
            ws_failure_threshold=3,
            ws_retry_cooldown=60.0,
            prefer_websocket=True
        )
        
        # Apply performance configuration to both WebSocket and HTTP clients
        websocket_client = hybrid_mcp_client.websocket_client
        websocket_client.request_timeout = websocket_config["request_timeout"]
        websocket_client.heartbeat_interval = websocket_config["heartbeat_interval"] 
        websocket_client.health_check_interval = websocket_config["health_check_interval"]
        websocket_client.ping_timeout = websocket_config["ping_timeout"]
        
        # Apply HTTP timeout configuration
        hybrid_mcp_client.http_timeout = websocket_config["request_timeout"]
        
        # Register connection event handler
        async def connection_event_handler(event_type, stats):
            logger.info(f"WebSocket connection event: {event_type}")
            monitoring_system.record_metric(
                "websocket_connected",
                1 if event_type == "connected" else 0
            )
        
        websocket_client.register_connection_event_handler(connection_event_handler)
        
        # Initialize optimized NLP agent with hybrid MCP client
        nlp_agent = OptimizedNLPAgent(
            kimi_api_key=kimi_api_key,
            mcp_ws_url=mcp_server_ws_url,
            agent_id="nlp-agent-001",
            enable_optimizations=True,
            enable_semantic_caching=True,
            enable_request_batching=True,
            websocket_client=websocket_client  # Use the WebSocket client
        )
        
        # Set external WebSocket client and hybrid adapter for the NLP agent
        nlp_agent.mcp_client = websocket_client
        nlp_agent.mcp_ops = hybrid_mcp_client  # Use the hybrid adapter
        logger.info(f"✅ Configured NLP agent with external WebSocket client: {type(websocket_client)}")
        
        # Start all services
        await hybrid_mcp_client.start()
        await nlp_agent.start()
        
        logger.info("Enhanced NLP Agent v2.2.0 started successfully!")
        logger.info(f"MCP communication: WebSocket={mcp_server_ws_url}, HTTP={mcp_server_http_url}")
        logger.info("Features enabled: performance optimization, enhanced monitoring, reliability improvements, HTTP fallback")
        
        # Perform initial health check
        health_status = monitoring_system.get_health_status()
        logger.info(f"Initial health status: {health_status['status']} (score: {health_status['health_score']:.2f})")
        
    except Exception as e:
        logger.error(f"Failed to start Enhanced NLP Agent: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global nlp_agent, websocket_client, hybrid_mcp_client, monitoring_system
    
    logger.info("Shutting down Enhanced NLP Agent...")
    
    # Stop all services gracefully
    if monitoring_system:
        await monitoring_system.stop()
    
    # Performance optimizer removed - cache manager shutdown handled by NLP agent
    
    if nlp_agent:
        await nlp_agent.stop()
    
    if hybrid_mcp_client:
        await hybrid_mcp_client.stop()
    elif websocket_client:
        await websocket_client.disconnect()
    
    logger.info("Enhanced NLP Agent shutdown complete")

@app.post("/process", response_model=ProcessResponse)
async def process_query(request: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Process natural language query with enhanced performance and reliability
    """
    if not nlp_agent or not monitoring_system:
        raise HTTPException(status_code=503, detail="NLP Agent not initialized")
    
    start_time = asyncio.get_event_loop().time()
    
    # Track request with monitoring system
    async with monitoring_system.track_request():
        try:
            logger.info(f"Processing query: {request.query[:100]}...")
            
            # Log database context if present
            logger.info("🎯 TRACE POINT 1: Extracting database_context from request")
            database_context = getattr(request, 'database_context', None)
            logger.info(f"🎯 TRACE POINT 2: database_context = {database_context}")
            
            if database_context:
                logger.info(f"Using database context: {database_context.get('database_name', 'unknown')}")
                # Basic validation of database context
                if 'database_name' not in database_context:
                    logger.warning("Database context missing required 'database_name' field")
            else:
                logger.warning("🎯 TRACE POINT 3: No database_context found in request")
            
            # Use unified processing approach
            logger.info("Using unified processing path for all queries")
            
            # Use performance optimizer for query processing
            async def process_with_nlp_agent():
                logger.info(f"🎯 TRACE POINT 4: About to call process_query_optimized with database_context: {database_context}")
                return await nlp_agent.process_query_optimized(
                    query=request.query,
                    user_id=getattr(request, 'user_id', 'default_user'),
                    session_id=getattr(request, 'session_id', 'default_session'),
                    context=request.context,
                    database_context=database_context  # Pass database context to NLP agent
                )
            
            # Process query with request deduplication using cache manager
            import hashlib
            import json
            request_signature = hashlib.sha256(
                json.dumps({"query": request.query, "context": request.context}, sort_keys=True).encode()
            ).hexdigest()
            
            # Use cache manager's deduplication feature
            result = await nlp_agent.cache_manager.deduplicate_request(
                request_signature=request_signature,
                request_executor=process_with_nlp_agent
            )
            
            # Create optimization stats for compatibility
            optimization_stats = {
                "cache_hits": 0,
                "cache_misses": 1,
                "deduplication_used": request_signature in nlp_agent.cache_manager._pending_requests,
                "optimization_methods": ["request_deduplication"]
            }
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Get current system metrics
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            cpu_percent = psutil.Process().cpu_percent()
            
            # Capture performance snapshot
            cache_hit_rate = optimization_stats.get("cache_hits", 0) / max(
                optimization_stats.get("cache_hits", 0) + optimization_stats.get("cache_misses", 1), 1
            )
            
            await monitoring_system.capture_performance_snapshot(
                response_time_ms=execution_time * 1000,
                cache_hit_rate=cache_hit_rate,
                websocket_connected=websocket_client.is_connected,
                active_requests=len(websocket_client.pending_requests),
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_percent
            )
            
            # Check if processing was successful
            if not result.success:
                # If processing failed, return error response
                logger.error(f"NLP processing failed: {result.error}")
                response = ProcessResponse(
                    query=request.query,
                    intent={},
                    entities={},
                    sql_query="",
                    explanation="",
                    complexity="unified",
                    processing_path="unified_path",
                    execution_time=execution_time,
                    cache_hit=optimization_stats.get("cache_hits", 0) > 0,
                    timestamp=datetime.now().isoformat(),
                    success=False
                )
                
                # Add error information to response for backend to process
                response_dict = response.model_dump()
                response_dict["error"] = result.error or "Unknown processing error"
                return response_dict
            
            response = ProcessResponse(
                query=request.query,
                intent=result.intent.model_dump() if result.intent else {},
                entities={},  # Not directly available in ProcessingResult
                sql_query=result.sql_query or "",
                explanation="",  # Not directly available in ProcessingResult
                complexity="unified",
                processing_path="unified_path",
                execution_time=execution_time,
                cache_hit=optimization_stats.get("cache_hits", 0) > 0,
                timestamp=datetime.now().isoformat(),
                success=True
            )
            
            # Log performance metrics with optimization details
            logger.info(
                f"Query processed in {execution_time:.3f}s "
                f"(unified_path, cache_hit={response.cache_hit}) "
                f"Optimizations: {', '.join(optimization_stats.get('optimization_methods', []))}"
            )
            
            # Background task for analytics (non-blocking)
            background_tasks.add_task(
                log_query_analytics,
                request.query,
                "unified",
                execution_time,
                response.cache_hit,
                optimization_stats
            )
            
            return response
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Error processing query in {execution_time:.3f}s: {e}")
            
            # Record error metrics
            monitoring_system.record_metric("request_errors", 1)
            
            raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Enhanced health check with comprehensive performance metrics and diagnostics"""
    try:
        if not monitoring_system:
            raise HTTPException(status_code=503, detail="Monitoring system not initialized")
        
        # Get comprehensive health status
        health_status = monitoring_system.get_health_status()
        
        # Get WebSocket connection statistics
        websocket_stats = {}
        if websocket_client:
            websocket_stats = websocket_client.get_connection_stats()
        
        # Get performance optimization statistics from cache manager
        optimization_stats = {}
        if nlp_agent and nlp_agent.cache_manager:
            cache_stats = nlp_agent.cache_manager.get_stats()
            optimization_stats = {
                "overall": {
                    "total_requests": cache_stats.get("l1_hits", 0) + cache_stats.get("l1_misses", 0),
                    "total_cache_hits": cache_stats.get("total_hits", 0),
                    "total_cache_misses": cache_stats.get("total_misses", 0),
                    "overall_hit_rate": cache_stats.get("hit_rate_percent", 0) / 100,
                    "pending_requests": cache_stats.get("pending_requests", 0)
                },
                "features": {
                    "request_deduplication": cache_stats.get("request_deduplication_enabled", True)
                }
            }
        
        # Calculate uptime
        uptime = getattr(app.state, "start_time", 0)
        if uptime:
            uptime = asyncio.get_event_loop().time() - uptime
        else:
            app.state.start_time = asyncio.get_event_loop().time()
            uptime = 0.0
        
        return HealthResponse(
            status=health_status["status"],
            timestamp=datetime.now().isoformat(),
            version="2.2.0",
            uptime=uptime,
            connections={
                "websocket": websocket_stats,
                "nlp_agent_active": nlp_agent is not None,
                "monitoring_active": monitoring_system is not None,
                "optimizer_active": nlp_agent and nlp_agent.cache_manager is not None
            },
            performance_metrics={
                "health_score": health_status["health_score"],
                "response_metrics": health_status["metrics"],
                "optimization_stats": optimization_stats,
                "alerts": health_status["alerts"],
                "performance_trend": health_status["performance_trend"]
            }
        )
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.post("/cache/clear")
async def clear_cache():
    """Clear semantic cache and optimization caches"""
    try:
        if not nlp_agent or not nlp_agent.cache_manager:
            raise HTTPException(status_code=503, detail="Cache manager not initialized")
        
        # Clear L1 cache and get count
        cleared_count = len(nlp_agent.cache_manager._l1_cache)
        nlp_agent.cache_manager._l1_cache.clear()
        nlp_agent.cache_manager._l1_access_order.clear()
        
        # Also clear NLP agent cache if available
        nlp_cleared_count = 0
        if nlp_agent and hasattr(nlp_agent, 'clear_cache'):
            nlp_cleared_count = await nlp_agent.clear_cache()
        
        total_cleared = cleared_count + nlp_cleared_count
        
        return {
            "message": "Cache cleared successfully",
            "cleared_entries": {
                "optimization_cache": cleared_count,
                "nlp_cache": nlp_cleared_count,
                "total": total_cleared
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")

# New advanced endpoints

@app.get("/metrics")
async def get_metrics():
    """Get detailed performance metrics"""
    try:
        if not monitoring_system:
            raise HTTPException(status_code=503, detail="Monitoring system not initialized")
        
        # Get optimization statistics from cache manager
        optimization_stats = {}
        if nlp_agent and nlp_agent.cache_manager:
            optimization_stats = nlp_agent.cache_manager.get_stats()
        
        # Get WebSocket statistics
        websocket_stats = {}
        if websocket_client:
            websocket_stats = websocket_client.get_connection_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "health_status": monitoring_system.get_health_status(),
            "optimization_stats": optimization_stats,
            "websocket_stats": websocket_stats,
            "system_metrics": {
                "memory_usage_mb": psutil.Process().memory_info().rss / 1024 / 1024,
                "cpu_percent": psutil.Process().cpu_percent(),
                "open_files": len(psutil.Process().open_files()),
                "threads": psutil.Process().num_threads()
            }
        }
        
    except Exception as e:
        logger.error(f"Metrics retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics retrieval failed: {str(e)}")

@app.get("/performance")
async def get_performance_dashboard():
    """Get comprehensive performance dashboard with optimization statistics"""
    try:
        if not nlp_agent or not nlp_agent.cache_manager:
            raise HTTPException(status_code=503, detail="Cache manager not initialized")
        
        # Get optimization stats from cache manager
        optimization_stats = nlp_agent.cache_manager.get_stats()
        
        # Get WebSocket connection stats
        websocket_stats = {}
        if websocket_client:
            websocket_stats = {
                "connection_state": websocket_client.connection_state.value,
                "is_connected": websocket_client.is_connected,
                "stats": {
                    "connection_attempts": websocket_client.stats.connection_attempts,
                    "successful_connections": websocket_client.stats.successful_connections,
                    "failed_connections": websocket_client.stats.failed_connections,
                    "reconnection_attempts": websocket_client.stats.reconnection_attempts,
                    "last_successful_connection": (
                        websocket_client.stats.last_successful_connection.isoformat()
                        if websocket_client.stats.last_successful_connection else None
                    ),
                    "last_connection_error": websocket_client.stats.last_connection_error,
                    "average_response_time": websocket_client.stats.average_response_time
                }
            }
        
        # Get monitoring system performance data
        monitoring_stats = {}
        if monitoring_system:
            monitoring_stats = {
                "alerts_triggered": len(monitoring_system.active_alerts),
                "metrics_count": len(monitoring_system.metrics),
                "uptime_seconds": (datetime.now() - monitoring_system.start_time).total_seconds() if monitoring_system.start_time else 0
            }
        
        # Get system resource usage
        system_stats = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_mb": psutil.virtual_memory().available // (1024 * 1024),
            "disk_usage_percent": psutil.disk_usage('/').percent
        }
        
        # Performance recommendations based on current stats
        recommendations = []
        overall_hit_rate = optimization_stats["hit_rate_percent"] / 100.0
        avg_response_time = optimization_stats["avg_response_time_ms"] / 1000
        total_requests = optimization_stats["total_hits"] + optimization_stats["total_misses"]
        
        if overall_hit_rate < 0.4:
            recommendations.append("Consider increasing cache sizes for better hit rates")
        if avg_response_time > 3.0:
            recommendations.append("Response times are high - check network connectivity and query complexity")
        if websocket_stats.get("stats", {}).get("failed_connections", 0) > 5:
            recommendations.append("High WebSocket connection failures - check MCP server availability")
        if system_stats["memory_percent"] > 80:
            recommendations.append("High memory usage - consider reducing cache sizes")
        if system_stats["cpu_percent"] > 80:
            recommendations.append("High CPU usage - system may be under stress")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "performance_summary": {
                "overall_hit_rate": overall_hit_rate,
                "average_response_time_seconds": avg_response_time,
                "total_requests": total_requests,
                "websocket_connected": websocket_stats.get("is_connected", False)
            },
            "optimization_stats": optimization_stats,
            "websocket_stats": websocket_stats,
            "monitoring_stats": monitoring_stats,
            "system_stats": system_stats,
            "recommendations": recommendations,
            "configuration": {
                "environment": os.getenv("ENVIRONMENT", "development"),
                "cache_sizes": {
                    "l1_cache": nlp_agent.cache_manager.l1_max_size if nlp_agent and nlp_agent.cache_manager else 1000,
                    "l1_ttl": nlp_agent.cache_manager.l1_ttl_seconds if nlp_agent and nlp_agent.cache_manager else 300,
                    "max_memory_mb": nlp_agent.cache_manager.max_memory_bytes // (1024 * 1024) if nlp_agent and nlp_agent.cache_manager else 100
                },
                "cache_features": ["multi_level", "redis_integration", "request_deduplication"]
            }
        }
        
    except Exception as e:
        logger.error(f"Performance dashboard error: {e}")
        raise HTTPException(status_code=500, detail=f"Performance dashboard failed: {str(e)}")

@app.post("/performance/optimize")
async def trigger_performance_optimization():
    """Manually trigger performance optimization and cache warming"""
    try:
        if not nlp_agent or not nlp_agent.cache_manager:
            raise HTTPException(status_code=503, detail="Cache manager not initialized")
        
        # Trigger manual cache optimization (basic cleanup)
        cleared_expired = 0
        for key, entry in list(nlp_agent.cache_manager._l1_cache.items()):
            if entry.is_expired():
                del nlp_agent.cache_manager._l1_cache[key]
                if key in nlp_agent.cache_manager._l1_access_order:
                    nlp_agent.cache_manager._l1_access_order.remove(key)
                cleared_expired += 1
        
        # Get connection performance recommendations
        if websocket_client:
            recent_failures = websocket_client.stats.failed_connections
            avg_response_time = websocket_client.stats.average_response_time
            current_timeout = websocket_client.request_timeout
            
            # Simple connection recommendations without performance optimizer
            connection_recommendations = {
                "recommended_timeout": current_timeout,
                "recent_failures": recent_failures,
                "avg_response_time": avg_response_time,
                "status": "stable" if recent_failures < 3 else "needs_attention"
            }
        else:
            connection_recommendations = {}
        
        return {
            "timestamp": datetime.now().isoformat(),
            "optimization_triggered": True,
            "actions_performed": [
                "cache_cleanup",
                "expired_entries_removal",
                "connection_analysis"
            ],
            "cleared_expired_entries": cleared_expired,
            "connection_recommendations": connection_recommendations,
            "message": "Performance optimization completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Performance optimization error: {e}")
        raise HTTPException(status_code=500, detail=f"Performance optimization failed: {str(e)}")

@app.get("/alerts")
async def get_alerts():
    """Get current alerts and alert history"""
    try:
        if not monitoring_system:
            raise HTTPException(status_code=503, detail="Monitoring system not initialized")
        
        active_alerts = [alert.to_dict() for alert in monitoring_system.active_alerts]
        alert_history = [alert.to_dict() for alert in list(monitoring_system.alert_history)[-20:]]  # Last 20
        
        return {
            "active_alerts": active_alerts,
            "alert_history": alert_history,
            "summary": {
                "active_count": len(active_alerts),
                "critical_count": len([a for a in active_alerts if a["level"] == "critical"]),
                "error_count": len([a for a in active_alerts if a["level"] == "error"]),
                "warning_count": len([a for a in active_alerts if a["level"] == "warning"])
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Alerts retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Alerts retrieval failed: {str(e)}")

@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an active alert"""
    try:
        if not monitoring_system:
            raise HTTPException(status_code=503, detail="Monitoring system not initialized")
        
        success = monitoring_system.acknowledge_alert(alert_id)
        
        if success:
            return {
                "message": f"Alert {alert_id} acknowledged successfully",
                "alert_id": alert_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found or already acknowledged")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Alert acknowledgment error: {e}")
        raise HTTPException(status_code=500, detail=f"Alert acknowledgment failed: {str(e)}")

@app.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve an active alert"""
    try:
        if not monitoring_system:
            raise HTTPException(status_code=503, detail="Monitoring system not initialized")
        
        success = monitoring_system.resolve_alert(alert_id)
        
        if success:
            return {
                "message": f"Alert {alert_id} resolved successfully",
                "alert_id": alert_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Alert resolution error: {e}")
        raise HTTPException(status_code=500, detail=f"Alert resolution failed: {str(e)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for backend communication on port 8011"""
    client_id = f"backend_{uuid.uuid4().hex[:8]}"
    
    try:
        await websocket.accept()
        active_websocket_connections[client_id] = websocket
        
        logger.info(f"WebSocket connection established with backend client: {client_id}")
        
        # Send connection acknowledgment
        await websocket.send_json({
            "type": "connection_established",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "server": "nlp-agent",
            "capabilities": ["query_processing", "sql_generation", "intent_extraction"]
        })
        
        # Main message handling loop
        while True:
            try:
                # Receive message from backend
                message = await websocket.receive_json()
                logger.info(f"Received WebSocket message from {client_id}: {message.get('type', 'unknown')}")
                
                # Handle different message types
                message_type = message.get("type", "unknown")
                
                if message_type == "heartbeat":
                    # Respond to heartbeat
                    await websocket.send_json({
                        "type": "heartbeat_response",
                        "timestamp": datetime.now().isoformat(),
                        "correlation_id": message.get("correlation_id")
                    })
                    logger.debug(f"Heartbeat response sent to {client_id}")
                    
                elif message_type == "sql_query":
                    # Handle SQL query requests from backend
                    await handle_websocket_sql_query(websocket, message, client_id)
                    
                elif message_type == "query":
                    # Handle general query requests (same as HTTP /process)
                    await handle_websocket_query(websocket, message, client_id)
                    
                elif message_type == "nlp_query_with_context":
                    # Handle enhanced query requests with database context
                    await handle_websocket_nlp_query_with_context(websocket, message, client_id)
                    
                else:
                    logger.warning(f"Unknown message type from {client_id}: {message_type}")
                    await websocket.send_json({
                        "type": "error",
                        "error": {
                            "type": "unknown_message_type",
                            "message": f"Unknown message type: {message_type}"
                        },
                        "response_to": message.get("message_id"),
                        "timestamp": datetime.now().isoformat()
                    })
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected by backend client: {client_id}")
                break
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"WebSocket connection closed for client: {client_id}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from {client_id}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "error": {
                        "type": "invalid_json",
                        "message": "Invalid JSON format"
                    },
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error handling WebSocket message from {client_id}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "error": {
                        "type": "processing_error",
                        "message": str(e)
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
    except Exception as e:
        logger.error(f"WebSocket connection error for {client_id}: {e}")
    finally:
        # Cleanup connection
        if client_id in active_websocket_connections:
            del active_websocket_connections[client_id]
        logger.info(f"WebSocket connection cleaned up for client: {client_id}")

async def handle_websocket_sql_query(websocket: WebSocket, message: Dict[str, Any], client_id: str):
    """Handle SQL query messages from backend via WebSocket"""
    start_time = asyncio.get_event_loop().time()
    message_id = message.get("message_id")
    
    try:
        if not nlp_agent:
            raise HTTPException(status_code=503, detail="NLP Agent not initialized")
        
        # Extract request parameters
        sql_query = message.get("sql_query", "")
        query_id = message.get("query_id", f"ws_query_{int(time.time() * 1000)}")
        query_context = message.get("query_context", {})
        execution_config = message.get("execution_config", {})
        
        logger.info(f"Processing WebSocket SQL query request: {query_id}")
        
        if not sql_query:
            raise ValueError("SQL query is required")
        
        # For SQL queries, we'll convert to a natural language processing request
        # This maintains compatibility with the NLP agent's processing pipeline
        fake_nl_query = f"Execute SQL: {sql_query}"
        
        # Process using the NLP agent's optimized processing
        result = await nlp_agent.process_query_optimized(
            query=fake_nl_query,
            user_id=query_context.get("user_id", "backend_user"),
            session_id=query_context.get("session_id", "backend_session"),
            context=query_context,
            database_context=query_context.get("database_context")
        )
        
        execution_time = asyncio.get_event_loop().time() - start_time
        
        # Build WebSocket response
        response = {
            "type": "sql_query_response",
            "success": True,
            "query_id": query_id,
            "intent": result.intent.model_dump() if result.intent else {},
            "sql_query": result.sql_query or sql_query,  # Return original if no new SQL generated
            "explanation": f"Processed SQL query via NLP agent",
            "processing_time_ms": int(execution_time * 1000),
            "response_to": message_id,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "agent": "nlp-agent",
                "version": "2.2.0",
                "processing_path": "websocket_sql",
                "cache_hit": False  # Direct SQL queries typically bypass cache
            }
        }
        
        # Send response
        await websocket.send_json(response)
        logger.info(f"WebSocket SQL query response sent to {client_id} in {execution_time:.3f}s")
        
    except Exception as e:
        execution_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"WebSocket SQL query processing error for {client_id}: {e}")
        
        error_response = {
            "type": "sql_query_response",
            "success": False,
            "query_id": message.get("query_id", "unknown"),
            "error": {
                "type": "sql_processing_error",
                "message": str(e)
            },
            "processing_time_ms": int(execution_time * 1000),
            "response_to": message_id,
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket.send_json(error_response)

async def handle_websocket_query(websocket: WebSocket, message: Dict[str, Any], client_id: str):
    """Handle general query messages from backend via WebSocket"""
    start_time = asyncio.get_event_loop().time()
    message_id = message.get("message_id")
    
    try:
        if not nlp_agent:
            raise HTTPException(status_code=503, detail="NLP Agent not initialized")
        
        # Extract request parameters
        query = message.get("query", "")
        query_id = message.get("query_id", f"ws_query_{int(time.time() * 1000)}")
        context = message.get("context", {})
        database_context = message.get("database_context")
        
        logger.info(f"Processing WebSocket query request: {query[:100]}...")
        
        if not query:
            raise ValueError("Query is required")
        
        # Process using the NLP agent's optimized processing
        result = await nlp_agent.process_query_optimized(
            query=query,
            user_id=context.get("user_id", "backend_user"),
            session_id=context.get("session_id", "backend_session"),
            context=context,
            database_context=database_context
        )
        
        execution_time = asyncio.get_event_loop().time() - start_time
        
        # Build WebSocket response
        response = {
            "type": "query_response",
            "success": True,
            "query_id": query_id,
            "query": query,
            "intent": result.intent.model_dump() if result.intent else {},
            "sql_query": result.sql_query or "",
            "explanation": f"Processed natural language query",
            "processing_time_ms": int(execution_time * 1000),
            "response_to": message_id,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "agent": "nlp-agent",
                "version": "2.2.0", 
                "processing_path": "websocket_query",
                "cache_hit": False  # WebSocket queries typically bypass cache for real-time processing
            }
        }
        
        # Send response
        await websocket.send_json(response)
        logger.info(f"WebSocket query response sent to {client_id} in {execution_time:.3f}s")
        
    except Exception as e:
        execution_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"WebSocket query processing error for {client_id}: {e}")
        
        error_response = {
            "type": "query_response",
            "success": False,
            "query_id": message.get("query_id", "unknown"),
            "error": {
                "type": "query_processing_error",
                "message": str(e)
            },
            "processing_time_ms": int(execution_time * 1000),
            "response_to": message_id,
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket.send_json(error_response)

async def handle_websocket_nlp_query_with_context(websocket: WebSocket, message: Dict[str, Any], client_id: str):
    """Handle enhanced NLP query messages with database context from backend via WebSocket"""
    start_time = asyncio.get_event_loop().time()
    message_id = message.get("message_id")
    
    try:
        if not nlp_agent:
            raise HTTPException(status_code=503, detail="NLP Agent not initialized")
        
        # Extract request parameters
        query = message.get("query", "")
        query_id = message.get("query_id", f"ws_nlp_query_{int(time.time() * 1000)}")
        user_id = message.get("user_id", "backend_user")
        session_id = message.get("session_id", "backend_session")
        context = message.get("context", {})
        database_context = message.get("database_context")
        
        logger.info(f"Processing enhanced WebSocket NLP query: {query[:100]}...")
        
        if not query:
            raise ValueError("Query is required")
        
        # Process using the NLP agent's optimized processing with enhanced context
        result = await nlp_agent.process_query_optimized(
            query=query,
            user_id=user_id,
            session_id=session_id,
            context=context,
            database_context=database_context
        )
        
        execution_time = asyncio.get_event_loop().time() - start_time
        
        # Build enhanced WebSocket response matching backend expectations
        response = {
            "type": "nlp_response",
            "success": True,
            "query_id": query_id,
            "query": query,
            "intent": result.intent.model_dump() if result.intent else {},
            "entities": {},  # Not available in ProcessingResult - placeholder for compatibility
            "sql_query": result.sql_query or "",
            "explanation": "Processed natural language query with database context",
            "complexity": "medium",
            "processing_path": result.processing_path or "websocket_nlp_enhanced",
            "execution_time": execution_time,
            "cache_hit": False,
            "processing_time_ms": result.processing_time_ms or int(execution_time * 1000),
            "response_to": message_id,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "agent": "nlp-agent",
                "version": "2.2.0",
                "processing_method": "enhanced_websocket",
                "database_context_available": database_context is not None
            }
        }
        
        # Send response
        await websocket.send_json(response)
        logger.info(f"Enhanced WebSocket NLP response sent to {client_id} in {execution_time:.3f}s")
        
    except Exception as e:
        execution_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"Enhanced WebSocket NLP processing error for {client_id}: {e}")
        
        error_response = {
            "type": "nlp_response",
            "success": False,
            "query_id": message.get("query_id", "unknown"),
            "query": message.get("query", ""),
            "error": {
                "type": "nlp_processing_error",
                "message": str(e)
            },
            "execution_time": execution_time,
            "processing_time_ms": int(execution_time * 1000),
            "response_to": message_id,
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket.send_json(error_response)

@app.get("/diagnostics")
async def get_diagnostics():
    """Get comprehensive system diagnostics"""
    try:
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "system_info": {
                "platform": os.name,
                "python_version": os.sys.version,
                "working_directory": os.getcwd(),
                "environment_variables": {
                    "KIMI_API_KEY": "***" if os.getenv("KIMI_API_KEY") else None,
                    "MCP_SERVER_WS_URL": os.getenv("MCP_SERVER_WS_URL"),
                    "HOST": os.getenv("HOST", "0.0.0.0"),
                    "PORT": os.getenv("PORT", "8001")
                }
            },
            "service_status": {
                "nlp_agent": nlp_agent is not None,
                "websocket_client": websocket_client is not None and websocket_client.is_connected,
                "processing_approach": "unified",
                "cache_manager": nlp_agent and nlp_agent.cache_manager is not None,
                "monitoring_system": monitoring_system is not None
            }
        }
        
        # Add WebSocket diagnostics
        if websocket_client:
            connection_stats = websocket_client.get_connection_stats()
            diagnostics["websocket_diagnostics"] = {
                "connection_state": connection_stats.get("connection_state"),
                "url": websocket_client.ws_url,
                "reconnection_attempts": connection_stats.get("stats", {}).get("reconnection_attempts", 0),
                "success_rate": connection_stats.get("stats", {}).get("success_rate", 0),
                "circuit_breaker": connection_stats.get("circuit_breaker", {})
            }
        
        # Add performance diagnostics from cache manager
        if nlp_agent and nlp_agent.cache_manager:
            cache_stats = nlp_agent.cache_manager.get_stats()
            diagnostics["performance_diagnostics"] = {
                "cache_efficiency": cache_stats.get("hit_rate_percent", 0) / 100,
                "average_response_time": cache_stats.get("avg_response_time_ms", 0),
                "pending_requests": cache_stats.get("pending_requests", 0),
                "l1_cache_size": cache_stats.get("l1_cache_size", 0),
                "memory_usage_percent": cache_stats.get("memory_usage_percent", 0)
            }
        
        # Add health diagnostics
        if monitoring_system:
            health_status = monitoring_system.get_health_status()
            diagnostics["health_diagnostics"] = {
                "health_score": health_status.get("health_score", 0),
                "status": health_status.get("status", "unknown"),
                "performance_trend": health_status.get("performance_trend", "unknown"),
                "active_alerts": len(monitoring_system.active_alerts)
            }
        
        # Add agent status information (consolidated from removed /status endpoint)
        if nlp_agent:
            diagnostics["agent_status"] = {
                "performance_metrics": nlp_agent.get_performance_metrics(),
                "cache_stats": nlp_agent.get_cache_stats(),
                "websocket_connected": (
                    nlp_agent.mcp_client.is_connected 
                    if hasattr(nlp_agent, 'mcp_client') and nlp_agent.mcp_client 
                    else False
                ),
                "connection_stats": (
                    nlp_agent.mcp_client.get_connection_stats()
                    if hasattr(nlp_agent, 'mcp_client') and nlp_agent.mcp_client and hasattr(nlp_agent.mcp_client, 'get_connection_stats')
                    else {}
                )
            }
        
        return diagnostics
        
    except Exception as e:
        logger.error(f"Diagnostics error: {e}")
        raise HTTPException(status_code=500, detail=f"Diagnostics failed: {str(e)}")

# Background task functions
async def log_query_analytics(
    query: str, 
    complexity: str, 
    execution_time: float, 
    cache_hit: bool,
    optimization_stats: Dict[str, Any] = None
):
    """Enhanced query analytics logging with optimization metrics"""
    try:
        analytics = {
            "query_length": len(query),
            "query_words": len(query.split()),
            "complexity": complexity,
            "execution_time_ms": execution_time * 1000,
            "cache_hit": cache_hit,
            "optimization_methods": optimization_stats.get("optimization_methods", []) if optimization_stats else [],
            "cache_hits": optimization_stats.get("cache_hits", 0) if optimization_stats else 0,
            "cache_misses": optimization_stats.get("cache_misses", 0) if optimization_stats else 0,
            "semantic_similarity": optimization_stats.get("semantic_similarity", 0.0) if optimization_stats else 0.0,
            "processing_time_saved_ms": optimization_stats.get("processing_time_saved_ms", 0.0) if optimization_stats else 0.0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Record analytics metrics in monitoring system
        if monitoring_system:
            monitoring_system.record_metric("query_complexity", 
                {"simple": 1, "standard": 2, "comprehensive": 3}.get(complexity, 1))
            monitoring_system.record_metric("query_length", len(query))
            monitoring_system.record_metric("optimization_savings_ms", 
                analytics["processing_time_saved_ms"])
        
        logger.info(f"Query analytics: {analytics}")
        
    except Exception as e:
        logger.error(f"Analytics logging error: {e}")

if __name__ == "__main__":
    # Run the enhanced server
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))
    
    logger.info(f"Starting Enhanced NLP Agent v2.2.0 on {host}:{port}")
    logger.info("Features: WebSocket reliability, performance optimization, enhanced monitoring")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False,
        log_level="info",
        access_log=True
    )
