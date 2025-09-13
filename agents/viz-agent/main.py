"""
Visualization Agent with HTTP API
Main entry point for the Visualization Agent service
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional, List

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from src.visualization_agent import VisualizationAgent
from src.models import VisualizationRequest, ChartType

# Import standardized models from local shared package
from shared.models.workflow import VisualizationResponse, AgentMetadata, ErrorResponse

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global visualization agent instance
viz_agent: Optional[VisualizationAgent] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown"""
    global viz_agent
    
    # Startup
    logger.info("Starting Visualization Agent...")
    
    try:
        # Initialize Visualization Agent
        viz_agent = VisualizationAgent()
        logger.info("Visualization Agent started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start Visualization Agent: {e}")
        raise
    
    yield
    
    # Shutdown
    if viz_agent:
        logger.info("Visualization Agent stopped")

# Pydantic models
class VisualizeRequest(BaseModel):
    data: List[Dict[str, Any]]
    query_context: Dict[str, Any]
    query_id: str
    visualization_config: Optional[Dict[str, Any]] = None
    database_context: Optional[Dict[str, Any]] = Field(None, description="Database context information")

# Global references
viz_agent: Optional[VisualizationAgent] = None
app = FastAPI(title="Visualization Agent API", version="1.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/visualize", response_model=VisualizationResponse)
async def create_visualization(request: VisualizeRequest) -> VisualizationResponse:
    """Create visualization from data and context"""
    if not viz_agent:
        raise HTTPException(status_code=503, detail="Visualization Agent not initialized")
    
    start_time = datetime.now()
    
    try:
        logger.info(f"Creating visualization for query {request.query_id}")
        
        # Log database context if present
        if request.database_context:
            logger.info(f"Using database context: {request.database_context.get('database_name', 'unknown')}")
            # Basic validation of database context
            if 'database_name' not in request.database_context:
                logger.warning("Database context missing required 'database_name' field")
        
        # Create visualization request
        viz_request = VisualizationRequest(
            request_id=request.query_id,
            user_id="anonymous",
            query_intent=request.query_context.get("query_intent", {}),
            data=request.data,
            preferences=request.visualization_config or {},
            database_context=request.database_context
        )
        
        # Process visualization through the agent
        result = await viz_agent.process_visualization_request(viz_request)
        
        if not result.success:
            # Create error response using standardized format
            operation_id = f"viz_op_{int(datetime.now().timestamp() * 1000)}"
            agent_metadata = AgentMetadata(
                agent_name="viz-agent",
                agent_version="1.0.0",
                processing_time_ms=result.processing_time_ms,
                operation_id=operation_id,
                status="error"
            )
            
            error_response = ErrorResponse(
                error_type="visualization_error",
                message=result.error_message or "Unknown visualization error",
                recovery_action="retry",
                suggestions=[
                    "Check data format compatibility",
                    "Verify chart configuration",
                    "Try a different visualization type"
                ]
            )
            
            return VisualizationResponse(
                success=False,
                agent_metadata=agent_metadata,
                error=error_response
            )
        
        # Create standardized agent metadata
        operation_id = f"viz_op_{int(datetime.now().timestamp() * 1000)}"
        agent_metadata = AgentMetadata(
            agent_name="viz-agent",
            agent_version="1.0.0",
            processing_time_ms=result.processing_time_ms,
            operation_id=operation_id,
            status="success"
        )
        
        # Build standardized response
        if result.success:
            chart_config = {
                "chart_type": result.chart_spec.chart_config.chart_type.value if hasattr(result.chart_spec.chart_config, 'chart_type') else "table",
                "title": result.chart_spec.chart_config.title if hasattr(result.chart_spec.chart_config, 'title') else "Chart",
                "x_axis_label": getattr(result.chart_spec.chart_config, 'x_axis_label', ''),
                "y_axis_label": getattr(result.chart_spec.chart_config, 'y_axis_label', ''),
                "color_scheme": getattr(result.chart_spec.chart_config, 'color_scheme', 'corporate'),
                "interactive": getattr(result.chart_spec.chart_config, 'interactive', True),
                "height": getattr(result.chart_spec.chart_config, 'height', 400),
                "width": getattr(result.chart_spec.chart_config, 'width', 600),
                "responsive": True
            }
            
            # Build chart data from result
            chart_data = result.chart_json if hasattr(result, 'chart_json') else {}
            
            # Create dashboard cards (basic implementation)
            dashboard_cards = [
                {
                    "type": "kpi",
                    "title": "Data Points",
                    "value": str(len(request.data)),
                    "trend": "neutral"
                }
            ]
            
            # Export options
            export_options = {
                "formats": ["png", "pdf", "svg"],
                "sizes": ["small", "medium", "large"]
            }

            response = VisualizationResponse(
                success=True,
                agent_metadata=agent_metadata,
                chart_config=chart_config,
                chart_data=chart_data,
                dashboard_cards=dashboard_cards,
                export_options=export_options
            )
        else:
            # Handle failure case - use empty/default values
            chart_config = {
                "chart_type": "table",
                "title": "Error",
                "responsive": True
            }
            chart_data = {}
            dashboard_cards = []
            export_options = {"formats": [], "sizes": []}
            
            response = VisualizationResponse(
                success=False,
                agent_metadata=agent_metadata,
                chart_config=chart_config,
                chart_data=chart_data,
                dashboard_cards=dashboard_cards,
                export_options=export_options,
                error=ErrorResponse(
                    error_type="visualization_error",
                    message=result.error_message or "Unknown visualization error",
                    recovery_action="retry",
                    suggestions=[
                        "Check data format compatibility",
                        "Verify chart configuration",
                        "Try a different visualization type"
                    ]
                )
            )
        
        logger.info(f"Successfully created visualization for query {request.query_id} in {result.processing_time_ms}ms")
        return response
        
    except Exception as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.error(f"Visualization creation failed for {request.query_id}: {e}")
        
        # Create error response using standardized format
        operation_id = f"viz_op_{int(datetime.now().timestamp() * 1000)}"
        agent_metadata = AgentMetadata(
            agent_name="viz-agent",
            agent_version="1.0.0",
            processing_time_ms=processing_time,
            operation_id=operation_id,
            status="error"
        )
        
        error_response = ErrorResponse(
            error_type="visualization_execution_error",
            message=str(e),
            recovery_action="retry",
            suggestions=[
                "Check data structure",
                "Verify agent connectivity",
                "Try again in a few moments"
            ]
        )
        
        return VisualizationResponse(
            success=False,
            agent_metadata=agent_metadata,
            chart_config={"chart_type": "error", "title": "Error", "responsive": True},
            chart_data={},
            dashboard_cards=[],
            export_options={"formats": [], "sizes": []},
            error=error_response
        )

@app.get("/chart-alternatives/{query_id}")
async def get_chart_alternatives(query_id: str, data: List[Dict[str, Any]]):
    """Get alternative chart types for the given data"""
    if not viz_agent:
        raise HTTPException(status_code=503, detail="Visualization Agent not initialized")
    
    try:
        # Create visualization request for alternatives
        viz_request = VisualizationRequest(
            request_id=query_id,
            user_id="anonymous",
            query_intent={},
            data=data
        )
        
        alternatives = await viz_agent.get_chart_alternatives(viz_request)
        return {"alternatives": alternatives}
        
    except Exception as e:
        logger.error(f"Failed to get chart alternatives: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not viz_agent:
        raise HTTPException(status_code=503, detail="Visualization Agent not initialized")
    
    try:
        health_status = await viz_agent.health_check()
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/status")
async def get_status():
    """Get agent status"""
    return {
        "agent_type": "viz-agent",
        "status": "running" if viz_agent else "stopped",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(viz_agent.chart_cache) if viz_agent else 0
    }

if __name__ == "__main__":
    import signal
    
    # Check if WebSocket server should be enabled
    enable_websockets = os.getenv('ENABLE_WEBSOCKETS', 'true').lower() == 'true'
    websocket_port = int(os.getenv('WEBSOCKET_PORT', '8013'))
    http_port = int(os.getenv('PORT', '8003'))
    
    async def start_servers():
        """Start both HTTP and WebSocket servers"""
        logger.info(f"Starting Enhanced Viz Agent v2.2.0 with HTTP server (:{http_port})")
        
        # Start HTTP server
        config = uvicorn.Config(
            "main:app",
            host="0.0.0.0", 
            port=http_port,
            reload=False,
            log_level="info"
        )
        http_server = uvicorn.Server(config)
        http_task = asyncio.create_task(http_server.serve())
        
        tasks = [http_task]
        
        # Start WebSocket server if enabled
        if enable_websockets:
            logger.info(f"WebSocket support enabled - starting WebSocket server on port {websocket_port}")
            from websocket_server import start_websocket_server
            
            websocket_task = asyncio.create_task(start_websocket_server())
            tasks.append(websocket_task)
            
            logger.info(f"Starting Enhanced Viz Agent v2.2.0 with both HTTP (:{http_port}) and WebSocket (:{websocket_port}) servers")
            logger.info("Features: WebSocket reliability, real-time chart generation, interactive features")
        else:
            logger.info("WebSocket support disabled - HTTP only mode")
        
        # Wait for all tasks
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Shutting down servers...")
            
            # Stop WebSocket server if running
            if enable_websockets:
                try:
                    from websocket_server import stop_websocket_server
                    await stop_websocket_server()
                except Exception as e:
                    logger.error(f"Error stopping WebSocket server: {e}")
            
            # Stop HTTP server
            try:
                http_server.should_exit = True
                await http_task
            except Exception as e:
                logger.error(f"Error stopping HTTP server: {e}")
    
    # Run the servers
    try:
        asyncio.run(start_servers())
    except KeyboardInterrupt:
        logger.info("Viz Agent shutdown complete")
    except Exception as e:
        logger.error(f"Error starting Viz Agent: {e}")
        sys.exit(1)
