"""
Data Agent with TiDB Integration
Main entry point for the Data Agent service with HTTP API
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from src.agent import get_data_agent, close_data_agent
from src.mcp_agent import get_mcp_data_agent, close_mcp_data_agent

# Import standardized models from local shared package
from shared.models.workflow import DataQueryResponse, QueryResult, AgentMetadata, ValidationResult, ErrorResponse

# Load environment variables
load_dotenv()

# Check if MCP mode is enabled
USE_MCP = os.getenv('USE_MCP_CLIENT', 'true').lower() == 'true'

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

# Pydantic models
class QueryExecuteRequest(BaseModel):
    sql_query: str
    query_context: Dict[str, Any]
    query_id: str
    execution_config: Optional[Dict[str, Any]] = None

# Global references
data_agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    global data_agent
    
    # Startup
    logger.info(f"Starting Data Agent (MCP mode: {USE_MCP})...")
    
    try:
        # Initialize Data Agent (MCP or direct mode)
        if USE_MCP:
            data_agent = await get_mcp_data_agent()
            logger.info("Data Agent started successfully with MCP integration")
        else:
            data_agent = await get_data_agent()
            logger.info("Data Agent started successfully with direct database integration")
        
    except Exception as e:
        logger.error(f"Failed to start Data Agent: {e}")
        raise
    
    yield
    
    # Shutdown
    if data_agent:
        if USE_MCP:
            await close_mcp_data_agent()
        else:
            await close_data_agent()
        logger.info("Data Agent stopped")

app = FastAPI(title="Data Agent API", version="1.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/execute", response_model=DataQueryResponse)
async def execute_query(request: QueryExecuteRequest) -> DataQueryResponse:
    """Execute SQL query and return processed data"""
    if not data_agent:
        raise HTTPException(status_code=503, detail="Data Agent not initialized")
    
    start_time = datetime.now()
    
    try:
        logger.info(f"Executing query {request.query_id}")
        
        # Convert query context to intent format expected by data agent
        query_intent = {
            "metric_type": request.query_context.get("metric_type", "revenue"),
            "time_period": request.query_context.get("time_period", "monthly"),
            "aggregation_level": request.query_context.get("aggregation_level", "monthly"),
            "filters": request.query_context.get("filters", {}),
            "comparison_periods": request.query_context.get("comparison_periods", [])
        }
        
        # Process query through the data agent
        result = await data_agent.process_query(query_intent, user_context={
            "query_id": request.query_id,
            "sql_query": request.sql_query
        })
        
        if not result.get("success", False):
            # Create error response using standardized format
            operation_id = f"data_op_{int(datetime.now().timestamp() * 1000)}"
            agent_metadata = AgentMetadata(
                agent_name="data-agent",
                agent_version="1.0.0",
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                operation_id=operation_id,
                status="error"
            )
            
            error_response = ErrorResponse(
                error_type="data_query_error",
                message=result.get("error", {}).get("message", "Unknown error"),
                recovery_action="retry",
                suggestions=[
                    "Check SQL query syntax",
                    "Verify database connectivity",
                    "Check data availability"
                ]
            )
            
            return DataQueryResponse(
                success=False,
                agent_metadata=agent_metadata,
                error=error_response
            )
        
        # Build standardized response
        operation_id = f"data_op_{int(datetime.now().timestamp() * 1000)}"
        processing_time_ms = result.get("metadata", {}).get("processing_time_ms", 0)
        if not processing_time_ms:
            # Calculate processing time if not provided
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        agent_metadata = AgentMetadata(
            agent_name="data-agent",
            agent_version="1.0.0",
            processing_time_ms=processing_time_ms,
            operation_id=operation_id,
            status="success"
        )
        
        # Create query result with proper data format
        processed_data = result.get("data", result.get("processed_data", []))
        columns = result.get("columns", [])
        
        query_result = QueryResult(
            data=processed_data,
            columns=columns,
            row_count=len(processed_data) if processed_data else result.get("row_count", 0),
            processing_time_ms=processing_time_ms
        )
        
        # Create validation result if available
        data_quality = result.get("metadata", {}).get("data_quality", result.get("data_quality", {}))
        validation = ValidationResult(
            is_valid=data_quality.get("is_valid", True),
            quality_score=data_quality.get("quality_score", 1.0),
            issues=data_quality.get("issues", []),
            warnings=data_quality.get("warnings", [])
        )
        
        response = DataQueryResponse(
            success=True,
            agent_metadata=agent_metadata,
            result=query_result,
            validation=validation,
            query_optimization=result.get("metadata", {}).get("optimization", {}),
            cache_metadata={"cache_hit": False}  # Default for now
        )
        
        logger.info(f"Successfully executed query {request.query_id} in {response.agent_metadata.processing_time_ms}ms")
        return response
        
    except Exception as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.error(f"Query execution failed for {request.query_id}: {e}")
        
        # Create error response using standardized format
        operation_id = f"data_op_{int(datetime.now().timestamp() * 1000)}"
        agent_metadata = AgentMetadata(
            agent_name="data-agent",
            agent_version="1.0.0",
            processing_time_ms=processing_time,
            operation_id=operation_id,
            status="error"
        )
        
        error_response = ErrorResponse(
            error_type="data_execution_error",
            message=str(e),
            recovery_action="retry",
            suggestions=[
                "Check database connectivity",
                "Verify query parameters",
                "Try again in a few moments"
            ]
        )
        
        return DataQueryResponse(
            success=False,
            agent_metadata=agent_metadata,
            error=error_response
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not data_agent:
        raise HTTPException(status_code=503, detail="Data Agent not initialized")
    
    try:
        health_status = await data_agent.health_check()
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/status")
async def get_status():
    """Get agent status"""
    return {
        "agent_type": "data-agent",
        "status": "running" if data_agent and data_agent.is_initialized else "stopped",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/metrics")
async def get_metrics():
    """Get agent metrics"""
    if not data_agent:
        raise HTTPException(status_code=503, detail="Data Agent not initialized")
    
    try:
        metrics = await data_agent.get_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import signal
    
    # Check if WebSocket server should be enabled
    enable_websockets = os.getenv('ENABLE_WEBSOCKETS', 'true').lower() == 'true'
    websocket_port = int(os.getenv('WEBSOCKET_PORT', '8012'))
    http_port = int(os.getenv('PORT', '8002'))
    
    async def start_servers():
        """Start both HTTP and WebSocket servers"""
        logger.info(f"Starting Enhanced Data Agent v2.2.0 with HTTP server (:8002)")
        
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
            
            logger.info(f"Starting Enhanced Data Agent v2.2.0 with both HTTP (:{http_port}) and WebSocket (:{websocket_port}) servers")
            logger.info("Features: WebSocket reliability, performance optimization, enhanced monitoring")
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
        logger.info("Data Agent shutdown complete")
    except Exception as e:
        logger.error(f"Error starting Data Agent: {e}")
        sys.exit(1)