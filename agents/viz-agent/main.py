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
        try:
            # No explicit cleanup needed for viz_agent currently
            logger.info("Visualization Agent stopped")
        except Exception as e:
            logger.warning(f"Error during Visualization Agent shutdown: {e}")

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from src.visualization_agent import VisualizationAgent
from src.models import VisualizationRequest, ChartType

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic models
class VisualizeRequest(BaseModel):
    data: List[Dict[str, Any]]
    query_context: Dict[str, Any]
    query_id: str
    visualization_config: Optional[Dict[str, Any]] = None
    database_context: Optional[Dict[str, Any]] = Field(None, description="Database context information")

class VisualizeResponse(BaseModel):
    success: bool
    query_id: str
    chart_config: Optional[Dict[str, Any]] = None
    chart_html: Optional[str] = None
    chart_json: Optional[Dict[str, Any]] = None
    processing_time_ms: int
    error: Optional[str] = None

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

@app.post("/visualize", response_model=VisualizeResponse)
async def create_visualization(request: VisualizeRequest) -> VisualizeResponse:
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
            return VisualizeResponse(
                success=False,
                query_id=request.query_id,
                processing_time_ms=result.processing_time_ms,
                error=result.error_message
            )
        
        # Build response
        response = VisualizeResponse(
            success=True,
            query_id=request.query_id,
            chart_config={
                "chart_type": result.chart_spec.chart_config.chart_type.value,
                "title": result.chart_spec.chart_config.title,
                "x_axis_label": result.chart_spec.chart_config.x_axis_label,
                "y_axis_label": result.chart_spec.chart_config.y_axis_label,
                "color_scheme": result.chart_spec.chart_config.color_scheme,
                "interactive": result.chart_spec.chart_config.interactive,
                "height": result.chart_spec.chart_config.height,
                "width": result.chart_spec.chart_config.width
            },
            chart_html=result.chart_html,
            chart_json=result.chart_json,
            processing_time_ms=result.processing_time_ms
        )
        
        logger.info(f"Successfully created visualization for query {request.query_id} in {result.processing_time_ms}ms")
        return response
        
    except Exception as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.error(f"Visualization creation failed for {request.query_id}: {e}")
        
        return VisualizeResponse(
            success=False,
            query_id=request.query_id,
            processing_time_ms=processing_time,
            error=str(e)
        )


class DashboardVisualizationRequest(BaseModel):
    data: List[Dict[str, Any]]
    columns: List[str]
    query: str
    query_id: str
    session_id: str
    user_id: Optional[str] = "anonymous"
    intent: Optional[Dict[str, Any]] = None

class DashboardVisualizationResponse(BaseModel):
    success: bool
    query_id: str
    dashboard_updated: bool
    chart_config: Optional[Dict[str, Any]] = None
    processing_time_ms: int
    error: Optional[str] = None


@app.post("/dashboard/visualize", response_model=DashboardVisualizationResponse)
async def create_dashboard_visualization(request: DashboardVisualizationRequest) -> DashboardVisualizationResponse:
    """Create visualization specifically for dashboard display"""
    if not viz_agent:
        raise HTTPException(status_code=503, detail="Visualization Agent not initialized")
    
    start_time = datetime.now()
    
    try:
        logger.info(f"Creating dashboard visualization for query {request.query_id} in session {request.session_id}")
        
        # Import dashboard integration manager
        from src.dashboard_integration import dashboard_integration_manager
        
        # Process the query data and create dashboard visualization
        dashboard_result = await dashboard_integration_manager.process_query_for_dashboard(
            data=request.data,
            columns=request.columns,
            query=request.query,
            query_id=request.query_id,
            session_id=request.session_id,
            user_id=request.user_id,
            intent=request.intent
        )
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return DashboardVisualizationResponse(
            success=dashboard_result["success"],
            query_id=request.query_id,
            dashboard_updated=dashboard_result.get("dashboard_updated", False),
            chart_config=dashboard_result.get("chart_config"),
            processing_time_ms=dashboard_result.get("processing_time_ms", processing_time),
            error=dashboard_result.get("error")
        )
        
    except Exception as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.error(f"Dashboard visualization creation failed for {request.query_id}: {e}")
        
        return DashboardVisualizationResponse(
            success=False,
            query_id=request.query_id,
            dashboard_updated=False,
            processing_time_ms=processing_time,
            error=str(e)
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


@app.get("/dashboard/cards/{session_id}")
async def get_dashboard_cards(session_id: str):
    """Get all dashboard cards for a session"""
    try:
        from src.dashboard_integration import dashboard_integration_manager
        
        cards = dashboard_integration_manager.get_session_cards(session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "cards": [card.__dict__ for card in cards],
            "total_cards": len(cards)
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard cards for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/dashboard/cards/{session_id}")
async def clear_dashboard_cards(session_id: str):
    """Clear all dashboard cards for a session"""
    try:
        from src.dashboard_integration import dashboard_integration_manager
        
        dashboard_integration_manager.clear_session_cards(session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Dashboard cards cleared"
        }
        
    except Exception as e:
        logger.error(f"Failed to clear dashboard cards for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard integration statistics"""
    try:
        from src.dashboard_integration import dashboard_integration_manager
        
        stats = dashboard_integration_manager.get_stats()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            **stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=False,
        log_level="info"
    )