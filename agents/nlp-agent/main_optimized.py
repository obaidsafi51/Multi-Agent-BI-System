"""
Enhanced NLP Agent v2.2.0 with advanced reliability, performance optimization, and monitoring
"""
import asyncio
import logging
import os
import psutil
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

from src.optimized_nlp_agent import OptimizedNLPAgent
from src.enhanced_websocket_client import EnhancedWebSocketMCPClient
from src.performance_optimizer import PerformanceOptimizer
from src.enhanced_monitoring import EnhancedMonitoringSystem, AlertLevel
from src.query_classifier import QueryClassifier, QueryComplexity
from performance_config import PerformanceConfig

# Import standardized models from local shared package
from shared.models.workflow import NLPResponse, QueryIntent, AgentMetadata, ErrorResponse

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
query_classifier: QueryClassifier = None
performance_optimizer: PerformanceOptimizer = None
monitoring_system: EnhancedMonitoringSystem = None

# Request/Response models
class ProcessRequest(BaseModel):
    query: str = Field(..., description="Natural language query to process")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    force_comprehensive: bool = Field(False, description="Force comprehensive processing path")
    use_cache: bool = Field(True, description="Enable semantic caching")
    timeout: int = Field(30, description="Request timeout in seconds")
    user_id: Optional[str] = Field("anonymous", description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")

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
    global nlp_agent, websocket_client, query_classifier, performance_optimizer, monitoring_system
    
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
        
        # Initialize performance optimizer with configuration
        optimizer_config = perf_config["optimizer"]
        performance_optimizer = PerformanceOptimizer(
            memory_cache_size=optimizer_config["memory_cache_size"],
            semantic_cache_size=optimizer_config["semantic_cache_size"],
            query_cache_size=optimizer_config["query_cache_size"],
            schema_cache_ttl=optimizer_config["schema_cache_ttl"],
            context_cache_ttl=optimizer_config["context_cache_ttl"],
            semantic_similarity_threshold=optimizer_config["semantic_similarity_threshold"],
            enable_request_deduplication=optimizer_config["enable_request_deduplication"],
            enable_response_prediction=optimizer_config["enable_response_prediction"]
        )
        performance_optimizer.start()
        
        # Initialize query classifier
        query_classifier = QueryClassifier()
        
        # Initialize enhanced WebSocket client
        kimi_api_key = os.getenv("KIMI_API_KEY")
        if not kimi_api_key:
            raise ValueError("KIMI_API_KEY environment variable is required")
            
        mcp_server_url = os.getenv("MCP_SERVER_WS_URL", "ws://tidb-mcp-server:8001/ws")
        
        # Initialize enhanced WebSocket client with configuration
        websocket_config = perf_config["websocket"]
        websocket_client = EnhancedWebSocketMCPClient(
            ws_url=mcp_server_url,
            agent_id="nlp-agent-001",
            initial_reconnect_delay=websocket_config["initial_reconnect_delay"],
            max_reconnect_delay=websocket_config["max_reconnect_delay"],
            max_reconnect_attempts=-1,        # Unlimited reconnections
            connection_timeout=websocket_config["connection_timeout"],
            request_timeout=websocket_config["request_timeout"],
            heartbeat_interval=websocket_config["heartbeat_interval"],
            health_check_interval=websocket_config["health_check_interval"],
            ping_timeout=websocket_config["ping_timeout"],
            enable_request_batching=websocket_config["enable_request_batching"],
            batch_size=websocket_config["batch_size"],
            batch_timeout=websocket_config["batch_timeout"]
        )
        
        # Register connection event handler
        async def connection_event_handler(event_type, stats):
            logger.info(f"WebSocket connection event: {event_type}")
            monitoring_system.record_metric(
                "websocket_connected",
                1 if event_type == "connected" else 0
            )
        
        websocket_client.register_connection_event_handler(connection_event_handler)
        
        # Initialize optimized NLP agent with all enhancements
        nlp_agent = OptimizedNLPAgent(
            kimi_api_key=kimi_api_key,
            mcp_ws_url=mcp_server_url,
            agent_id="nlp-agent-001",
            enable_optimizations=True,
            enable_semantic_caching=True,
            enable_request_batching=True
        )
        
        # Start all services
        await websocket_client.connect()
        await nlp_agent.start()
        
        logger.info("Enhanced NLP Agent v2.2.0 started successfully!")
        logger.info(f"WebSocket connected to: {mcp_server_url}")
        logger.info("Features enabled: performance optimization, enhanced monitoring, reliability improvements")
        
        # Perform initial health check
        health_status = monitoring_system.get_health_status()
        logger.info(f"Initial health status: {health_status['status']} (score: {health_status['health_score']:.2f})")
        
    except Exception as e:
        logger.error(f"Failed to start Enhanced NLP Agent: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global nlp_agent, websocket_client, performance_optimizer, monitoring_system
    
    logger.info("Shutting down Enhanced NLP Agent...")
    
    # Stop all services gracefully
    if monitoring_system:
        await monitoring_system.stop()
    
    if performance_optimizer:
        await performance_optimizer.stop()
    
    if nlp_agent:
        await nlp_agent.stop()
    
    if websocket_client:
        await websocket_client.disconnect()
    
    logger.info("Enhanced NLP Agent shutdown complete")

@app.post("/process", response_model=NLPResponse)
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
            database_context = getattr(request, 'database_context', None)
            if database_context:
                logger.info(f"Using database context: {database_context.get('database_name', 'unknown')}")
                # Basic validation of database context
                if 'database_name' not in database_context:
                    logger.warning("Database context missing required 'database_name' field")
            
            # Classify query complexity unless forced comprehensive
            if request.force_comprehensive:
                complexity = QueryComplexity.COMPREHENSIVE
                processing_path = "comprehensive"
            else:
                classification = query_classifier.classify_query(request.query, request.context)
                complexity = classification.complexity
                processing_path = classification.processing_path
            
            logger.info(f"Query classified as: {complexity.value} -> {processing_path} path")
            
            # Use performance optimizer for query processing
            async def process_with_nlp_agent():
                return await nlp_agent.process_query_optimized(
                    query=request.query,
                    user_id=getattr(request, 'user_id', 'default_user'),
                    session_id=getattr(request, 'session_id', 'default_session'),
                    context=request.context
                )
            
            # Optimize query processing with caching and deduplication
            result, optimization_stats = await performance_optimizer.optimize_query_processing(
                query=request.query,
                context=request.context,
                processing_function=process_with_nlp_agent
            )
            
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
            
            # Create standardized agent metadata
            operation_id = f"nlp_op_{int(datetime.now().timestamp() * 1000)}"
            agent_metadata = AgentMetadata(
                agent_name="nlp-agent",
                agent_version="2.2.0",
                processing_time_ms=int(execution_time * 1000),
                operation_id=operation_id,
                status="success"
            )
            
            # Extract or create query intent
            intent = None
            if hasattr(result, 'intent') and result.intent:
                intent = QueryIntent(
                    metric_type=result.intent.metric_type or "unknown",
                    time_period=result.intent.time_period or "unknown",
                    aggregation_level=getattr(result.intent, 'aggregation_level', 'monthly'),
                    confidence_score=getattr(result.intent, 'confidence_score', 0.0),
                    visualization_hint=getattr(result.intent, 'visualization_hint', 'table')
                )
            elif hasattr(result, 'query_intent') and result.query_intent:
                # Handle different response format
                intent_data = result.query_intent
                intent = QueryIntent(
                    metric_type=intent_data.get('metric_type', 'unknown'),
                    time_period=intent_data.get('time_period', 'unknown'),
                    aggregation_level=intent_data.get('aggregation_level', 'monthly'),
                    confidence_score=intent_data.get('confidence_score', getattr(result, 'confidence_score', 0.0)),
                    visualization_hint=intent_data.get('visualization_hint', 'table')
                )
            
            # Create standardized response
            response = NLPResponse(
                success=True,
                agent_metadata=agent_metadata,
                intent=intent,
                sql_query=result.sql_query or "",
                entities_recognized=[],  # Extract from result if available
                confidence_score=getattr(result, 'confidence_score', 0.0),
                processing_path=processing_path
            )
            
            # Log performance metrics with optimization details
            cache_hit = optimization_stats.get("cache_hits", 0) > 0
            logger.info(
                f"Query processed in {execution_time:.3f}s "
                f"({processing_path} path, cache_hit={cache_hit}) "
                f"Optimizations: {', '.join(optimization_stats.get('optimization_methods', []))}"
            )
            
            # Background task for analytics (non-blocking)
            background_tasks.add_task(
                log_query_analytics,
                request.query,
                complexity.value,
                execution_time,
                optimization_stats.get("cache_hits", 0) > 0,
                optimization_stats
            )
            
            return response
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Error processing query in {execution_time:.3f}s: {e}")
            
            # Record error metrics
            monitoring_system.record_metric("request_errors", 1)
            
            # Create error response using standardized format
            operation_id = f"nlp_op_{int(datetime.now().timestamp() * 1000)}"
            agent_metadata = AgentMetadata(
                agent_name="nlp-agent",
                agent_version="2.2.0",
                processing_time_ms=int(execution_time * 1000),
                operation_id=operation_id,
                status="error"
            )
            
            error_response = ErrorResponse(
                error_type="nlp_processing_error",
                message=str(e),
                recovery_action="retry",
                suggestions=[
                    "Try rephrasing your query",
                    "Check if the query is too complex",
                    "Verify database connectivity"
                ]
            )
            
            return NLPResponse(
                success=False,
                agent_metadata=agent_metadata,
                error=error_response
            )

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
        
        # Get performance optimization statistics
        optimization_stats = {}
        if performance_optimizer:
            optimization_stats = performance_optimizer.get_optimization_stats()
        
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
                "optimizer_active": performance_optimizer is not None
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

@app.get("/status")
async def get_status():
    """Get detailed agent status and metrics"""
    global nlp_agent, query_classifier
    
    try:
        status = {
            "agent_initialized": nlp_agent is not None,
            "timestamp": datetime.now().isoformat()
        }
        
        if nlp_agent:
            status["performance_metrics"] = nlp_agent.get_performance_metrics()
            status["cache_stats"] = nlp_agent.get_cache_stats()
            
            # Check if the NLP agent has a WebSocket client
            if hasattr(nlp_agent, 'mcp_client') and nlp_agent.mcp_client:
                status["websocket_connected"] = nlp_agent.mcp_client.is_connected
                if hasattr(nlp_agent.mcp_client, 'get_connection_stats'):
                    status["connection_stats"] = nlp_agent.mcp_client.get_connection_stats()
            else:
                status["websocket_connected"] = False
        
        if query_classifier:
            if hasattr(query_classifier, 'get_stats'):
                status["classifier_stats"] = query_classifier.get_stats()
            else:
                status["classifier_stats"] = {"classifier_type": "QueryClassifier", "status": "active"}
        
        return status
        
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@app.post("/classify")
async def classify_query(request: ProcessRequest):
    """Classify query complexity without processing"""
    try:
        if not query_classifier:
            raise HTTPException(status_code=503, detail="Query classifier not initialized")
        
        classification = query_classifier.classify_query(request.query, request.context)
        
        return {
            "query": request.query,
            "complexity": classification.complexity.value,
            "processing_path": classification.processing_path,
            "confidence": classification.confidence_score,
            "features": classification.reasoning,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Classification error: {e}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")

@app.post("/cache/clear")
async def clear_cache():
    """Clear semantic cache and optimization caches"""
    try:
        if not performance_optimizer:
            raise HTTPException(status_code=503, detail="Performance optimizer not initialized")
        
        cleared_count = await performance_optimizer.clear_cache()
        
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
        
        # Get optimization statistics
        optimization_stats = {}
        if performance_optimizer:
            optimization_stats = performance_optimizer.get_optimization_stats()
        
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

@app.get("/metrics/export/{format_type}")
async def export_metrics(format_type: str):
    """Export metrics in various formats (json, prometheus)"""
    try:
        if not monitoring_system:
            raise HTTPException(status_code=503, detail="Monitoring system not initialized")
        
        if format_type not in ["json", "prometheus"]:
            raise HTTPException(status_code=400, detail="Supported formats: json, prometheus")
        
        exported_data = monitoring_system.export_metrics(format_type)
        
        content_type = "application/json" if format_type == "json" else "text/plain"
        
        return {
            "format": format_type,
            "data": exported_data,
            "content_type": content_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Metrics export error: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics export failed: {str(e)}")

@app.get("/performance")
async def get_performance_dashboard():
    """Get comprehensive performance dashboard with optimization statistics"""
    try:
        if not performance_optimizer:
            raise HTTPException(status_code=503, detail="Performance optimizer not initialized")
        
        # Get optimization stats
        optimization_stats = performance_optimizer.get_optimization_stats()
        
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
        overall_hit_rate = optimization_stats["overall"]["overall_hit_rate"]
        avg_response_time = optimization_stats["overall"]["average_response_time_ms"] / 1000
        
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
                "total_requests": optimization_stats["overall"]["total_requests"],
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
                    "memory": performance_optimizer.memory_cache_size,
                    "semantic": performance_optimizer.semantic_cache_size,
                    "query": performance_optimizer.query_cache_size
                },
                "similarity_threshold": performance_optimizer.semantic_similarity_threshold
            }
        }
        
    except Exception as e:
        logger.error(f"Performance dashboard error: {e}")
        raise HTTPException(status_code=500, detail=f"Performance dashboard failed: {str(e)}")

@app.post("/performance/optimize")
async def trigger_performance_optimization():
    """Manually trigger performance optimization and cache warming"""
    try:
        if not performance_optimizer:
            raise HTTPException(status_code=503, detail="Performance optimizer not initialized")
        
        # Trigger manual optimization
        await performance_optimizer._proactive_cache_warming()
        await performance_optimizer._optimize_memory_usage()
        
        # Get connection performance recommendations
        if websocket_client:
            recent_failures = websocket_client.stats.failed_connections
            avg_response_time = websocket_client.stats.average_response_time
            current_timeout = websocket_client.request_timeout
            
            connection_recommendations = performance_optimizer.optimize_connection_performance(
                current_timeout, recent_failures, avg_response_time
            )
        else:
            connection_recommendations = {}
        
        return {
            "timestamp": datetime.now().isoformat(),
            "optimization_triggered": True,
            "actions_performed": [
                "cache_warming",
                "memory_optimization",
                "connection_analysis"
            ],
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
                "query_classifier": query_classifier is not None,
                "performance_optimizer": performance_optimizer is not None,
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
        
        # Add performance diagnostics
        if performance_optimizer:
            optimization_stats = performance_optimizer.get_optimization_stats()
            diagnostics["performance_diagnostics"] = {
                "cache_efficiency": optimization_stats.get("overall", {}).get("overall_hit_rate", 0),
                "average_response_time": optimization_stats.get("overall", {}).get("average_response_time_ms", 0),
                "active_optimizations": optimization_stats.get("features", {})
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
    # Check if WebSocket server should be enabled
    enable_websocket = os.getenv("ENABLE_WEBSOCKETS", "true").lower() == "true"
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))
    
    if enable_websocket:
        # Import and start WebSocket server alongside HTTP
        from websocket_server import start_websocket_server, stop_websocket_server
        
        async def run_both_servers():
            """Run both HTTP and WebSocket servers"""
            logger.info(f"Starting Enhanced NLP Agent v2.2.0 with both HTTP (:{port}) and WebSocket (:8011) servers")
            logger.info("Features: WebSocket reliability, performance optimization, enhanced monitoring")
            
            # Start HTTP server with proper async handling
            config = uvicorn.Config(
                app,
                host=host,
                port=port,
                reload=False,
                log_level="info",
                access_log=True
            )
            http_server = uvicorn.Server(config)
            http_task = asyncio.create_task(http_server.serve())
            
            tasks = [http_task]
            
            # Start WebSocket server
            logger.info("WebSocket server starting...")
            websocket_task = asyncio.create_task(start_websocket_server())
            tasks.append(websocket_task)
            
            logger.info("Both servers started successfully")
            
            # Wait for all tasks
            try:
                await asyncio.gather(*tasks)
            except KeyboardInterrupt:
                logger.info("Shutting down servers...")
            finally:
                try:
                    await stop_websocket_server()
                    logger.info("WebSocket server stopped")
                except Exception as e:
                    logger.error(f"Error stopping WebSocket server: {e}")
                    
                try:
                    http_server.should_exit = True
                    logger.info("HTTP server stopped")
                except Exception as e:
                    logger.error(f"Error stopping HTTP server: {e}")
        
        # Run both servers
        asyncio.run(run_both_servers())
        
    else:
        # HTTP only mode (fallback)
        logger.info(f"Starting Enhanced NLP Agent v2.2.0 on {host}:{port} (HTTP only)")
        logger.info("Features: Performance optimization, enhanced monitoring")
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=False,
            log_level="info",
            access_log=True
        )
