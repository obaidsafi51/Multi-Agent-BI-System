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
from pydantic import BaseModel
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
        
        # Create visualization request
        viz_request = VisualizationRequest(
            request_id=request.query_id,
            user_id="anonymous",
            query_intent=request.query_context.get("query_intent", {}),
            data=request.data,
            preferences=request.visualization_config or {}
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
        chart_config = {
            "chart_type": result.chart_spec.chart_config.chart_type.value,
            "title": result.chart_spec.chart_config.title,
            "x_axis_label": result.chart_spec.chart_config.x_axis_label,
            "y_axis_label": result.chart_spec.chart_config.y_axis_label,
            "color_scheme": result.chart_spec.chart_config.color_scheme,
            "interactive": result.chart_spec.chart_config.interactive,
            "height": result.chart_spec.chart_config.height,
            "width": result.chart_spec.chart_config.width,
            "responsive": True
        }
        
        # Build chart data from result
        chart_data = result.chart_json
        
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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=False,
        log_level="info"
    )
