"""
Viz Agent WebSocket Server

WebSocket server for visualization agent with real-time chart generation,
interactive features, and enhanced performance monitoring.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Set
from contextlib import asynccontextmanager

import websockets
from websockets.server import WebSocketServerProtocol
import websockets.exceptions

from src.visualization_agent import VisualizationAgent
from src.models import VisualizationRequest
from src.performance_optimizer import PerformanceOptimizer

logger = logging.getLogger(__name__)


class WebSocketVizServer:
    """WebSocket server for Viz agent with connection management and chart generation"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8013):
        self.host = host
        self.port = port
        self.server = None
        self.connections: Set[WebSocketServerProtocol] = set()
        
        # Agent components (will be initialized)
        self.viz_agent: Optional[VisualizationAgent] = None
        self.performance_optimizer: Optional[PerformanceOptimizer] = None
        
        # Statistics
        self.start_time = time.time()
        self.message_count = 0
        self.connection_count = 0
        self.chart_generation_count = 0
    
    async def initialize_agent(self):
        """Initialize the Viz agent and its components"""
        try:
            logger.info("Initializing Enhanced Viz Agent components for WebSocket server...")
            
            # Initialize performance optimizer
            self.performance_optimizer = PerformanceOptimizer()
            
            # Initialize main Viz agent
            self.viz_agent = VisualizationAgent()
            
            logger.info("Enhanced Viz Agent components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Viz agent: {e}")
            raise
    
    async def start_server(self):
        """Start the WebSocket server"""
        try:
            await self.initialize_agent()
            
            logger.info(f"Starting Viz WebSocket server on {self.host}:{self.port}")
            
            self.server = await websockets.serve(
                self.handle_connection,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5,
                process_request=self.process_request
            )
            
            logger.info(f"Viz WebSocket server started on ws://{self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start Viz WebSocket server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the WebSocket server"""
        try:
            if self.server:
                self.server.close()
                await self.server.wait_closed()
                logger.info("Viz WebSocket server stopped")
            
            # Close all connections
            if self.connections:
                await asyncio.gather(
                    *[conn.close() for conn in self.connections],
                    return_exceptions=True
                )
                self.connections.clear()
                
        except Exception as e:
            logger.error(f"Error stopping Viz WebSocket server: {e}")
    
    async def process_request(self, path, request_headers):
        """Process request before WebSocket handling to accept all paths"""
        # Accept both root path and /ws path for compatibility
        if path in ["/", "/ws"]:
            logger.debug(f"Accepting WebSocket connection on path: {path}")
            return None  # Continue with WebSocket connection
        else:
            logger.debug(f"WebSocket connection attempt on unknown path: {path}")
            return None  # Still continue for now, but log for debugging
    
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection"""
        client_id = f"viz-client-{uuid.uuid4().hex[:8]}"
        self.connections.add(websocket)
        self.connection_count += 1
        
        logger.info(f"Viz agent WebSocket connection established on path {path}: {client_id}")
        
        try:
            # Send welcome message
            welcome_message = {
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "server": "viz-agent-websocket",
                "version": "2.2.0",
                "capabilities": [
                    "chart_generation",
                    "interactive_features", 
                    "real_time_updates",
                    "export_management"
                ]
            }
            await websocket.send(json.dumps(welcome_message))
            
            # Handle messages
            async for message in websocket:
                try:
                    if isinstance(message, str):
                        data = json.loads(message)
                        await self.handle_message(websocket, data, client_id)
                    self.message_count += 1
                    
                except json.JSONDecodeError:
                    await self.send_error(websocket, "Invalid JSON message", client_id)
                except Exception as e:
                    logger.error(f"Error handling message from {client_id}: {e}")
                    await self.send_error(websocket, str(e), client_id)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Viz agent WebSocket connection closed: {client_id}")
        except Exception as e:
            logger.error(f"Error in Viz agent WebSocket connection {client_id}: {e}")
        finally:
            self.connections.discard(websocket)
    
    async def handle_message(self, websocket: WebSocketServerProtocol, data: Dict, client_id: str):
        """Handle incoming WebSocket message"""
        message_type = data.get("type", "unknown").lower()
        message_id = data.get("message_id", str(uuid.uuid4()))
        
        logger.info(f"Viz agent received message type: '{message_type}' from {client_id}")
        
        try:
            if message_type in ["heartbeat", "ping"]:
                await self.handle_heartbeat(websocket, data, client_id)
            elif message_type == "generate_chart":
                await self.handle_chart_generation(websocket, data, client_id, message_id)
            elif message_type == "health_check":
                await self.handle_health_check(websocket, data, client_id, message_id)
            elif message_type == "stats":
                await self.handle_stats_request(websocket, data, client_id, message_id)
            elif message_type == "export_chart":
                await self.handle_chart_export(websocket, data, client_id, message_id)
            elif message_type == "test_message":
                # Handle test messages from connectivity tests
                response = {
                    "type": "test_response",
                    "timestamp": datetime.utcnow().isoformat(),
                    "client_id": client_id,
                    "message": "Test message received"
                }
                await websocket.send(json.dumps(response))
            else:
                logger.warning(f"Unknown message type '{message_type}' from {client_id}")
                await self.send_error(websocket, f"Unknown message type: {message_type}", client_id)
        except Exception as e:
            logger.error(f"Error handling message type '{message_type}': {str(e)}")
            await self.send_error(websocket, f"Error processing message: {str(e)}", client_id)
    
    async def handle_heartbeat(self, websocket: WebSocketServerProtocol, data: Dict, client_id: str):
        """Handle heartbeat message"""
        response = {
            "type": "heartbeat_response",
            "timestamp": datetime.utcnow().isoformat(),
            "server_time": time.time(),
            "client_id": client_id,
            "correlation_id": data.get("correlation_id")
        }
        await websocket.send(json.dumps(response))
    
    async def handle_chart_generation(self, websocket: WebSocketServerProtocol, data: Dict, client_id: str, message_id: str):
        """Handle chart generation request"""
        try:
            if not self.viz_agent:
                raise RuntimeError("Viz agent not initialized")
            
            # Extract chart generation parameters
            chart_data = data.get("data", [])
            chart_config = data.get("config", {})
            query_context = data.get("query_context", {})
            
            if not chart_data:
                await self.send_error(websocket, "Missing data for chart generation", client_id)
                return
            
            # Send processing status
            await self.send_progress(websocket, message_id, client_id, "processing", 20)
            
            # Create visualization request
            viz_request = VisualizationRequest(
                data=chart_data,
                query_context=query_context,
                config=chart_config,
                request_id=message_id
            )
            
            # Generate chart
            start_time = time.time()
            viz_response = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.viz_agent.create_visualization,
                viz_request
            )
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            self.chart_generation_count += 1
            
            # Send completion status
            await self.send_progress(websocket, message_id, client_id, "completed", 100)
            
            # Send result
            response = {
                "type": "chart_generation_response",
                "response_to": message_id,
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "chart": viz_response.chart_specification.dict() if viz_response.chart_specification else None,
                "config": viz_response.chart_config.dict() if viz_response.chart_config else None,
                "interactive": viz_response.interactive_config.dict() if viz_response.interactive_config else None,
                "processing_time_ms": processing_time,
                "success": viz_response.success,
                "error": viz_response.error_message if not viz_response.success else None
            }
            
            await websocket.send(json.dumps(response))
            logger.info(f"Chart generated for {client_id} in {processing_time:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error generating chart for {client_id}: {e}")
            await self.send_error(websocket, str(e), client_id)
    
    async def handle_chart_export(self, websocket: WebSocketServerProtocol, data: Dict, client_id: str, message_id: str):
        """Handle chart export request"""
        try:
            if not self.viz_agent:
                raise RuntimeError("Viz agent not initialized")
            
            chart_data = data.get("chart")
            export_format = data.get("format", "png")
            export_config = data.get("export_config", {})
            
            if not chart_data:
                await self.send_error(websocket, "Missing chart data for export", client_id)
                return
            
            # Send processing status
            await self.send_progress(websocket, message_id, client_id, "exporting", 50)
            
            # Export chart using the export manager
            start_time = time.time()
            export_result = await asyncio.get_event_loop().run_in_executor(
                None,
                self.viz_agent.export_manager.export_chart,
                chart_data, export_format, export_config
            )
            processing_time = (time.time() - start_time) * 1000
            
            # Send completion status
            await self.send_progress(websocket, message_id, client_id, "completed", 100)
            
            # Send result
            response = {
                "type": "chart_export_response",
                "response_to": message_id,
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "export_result": export_result,
                "processing_time_ms": processing_time
            }
            
            await websocket.send(json.dumps(response))
            logger.info(f"Chart exported for {client_id} in {processing_time:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error exporting chart for {client_id}: {e}")
            await self.send_error(websocket, str(e), client_id)
    
    async def handle_health_check(self, websocket: WebSocketServerProtocol, data: Dict, client_id: str, message_id: str):
        """Handle health check request"""
        uptime = time.time() - self.start_time
        
        health_data = {
            "status": "healthy",
            "uptime": uptime,
            "connections": len(self.connections),
            "messages_processed": self.message_count,
            "charts_generated": self.chart_generation_count,
            "version": "2.2.0",
            "agent_ready": self.viz_agent is not None,
            "performance_optimizer": "active" if self.performance_optimizer else "inactive"
        }
        
        response = {
            "type": "health_check_response",
            "response_to": message_id,
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": health_data
        }
        
        await websocket.send(json.dumps(response))
    
    async def handle_stats_request(self, websocket: WebSocketServerProtocol, data: Dict, client_id: str, message_id: str):
        """Handle statistics request"""
        stats = self.get_stats()
        
        response = {
            "type": "stats_response",
            "response_to": message_id,
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": stats
        }
        
        await websocket.send(json.dumps(response))
    
    async def send_progress(self, websocket: WebSocketServerProtocol, message_id: str, client_id: str, status: str, progress: int):
        """Send progress update"""
        progress_message = {
            "type": "progress_update",
            "response_to": message_id,
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            "progress": progress
        }
        
        await websocket.send(json.dumps(progress_message))
    
    async def send_error(self, websocket: WebSocketServerProtocol, error_message: str, client_id: str):
        """Send error message to client"""
        error_response = {
            "type": "error",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat(),
            "error": {
                "message": error_message,
                "type": "server_error"
            }
        }
        
        try:
            await websocket.send(json.dumps(error_response))
        except Exception as e:
            logger.error(f"Failed to send error message to client {client_id}: {e}")
    
    async def broadcast_message(self, message: Dict):
        """Broadcast message to all connected clients"""
        if self.connections:
            message["timestamp"] = datetime.utcnow().isoformat()
            message_str = json.dumps(message)
            
            # Send to all connections
            await asyncio.gather(
                *[conn.send(message_str) for conn in self.connections],
                return_exceptions=True
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        uptime = time.time() - self.start_time
        
        return {
            "server": "viz-agent-websocket",
            "version": "2.2.0",
            "uptime": uptime,
            "connections": len(self.connections),
            "total_connections": self.connection_count,
            "messages_processed": self.message_count,
            "charts_generated": self.chart_generation_count,
            "agent_initialized": self.viz_agent is not None,
            "status": "running" if self.server else "stopped"
        }


# Global WebSocket server instance
websocket_viz_server = WebSocketVizServer()


# Server control functions
async def start_websocket_server():
    """Start the Viz WebSocket server"""
    try:
        host = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
        port = int(os.getenv("WEBSOCKET_PORT", "8013"))
        
        server = WebSocketVizServer(host, port)
        await server.start_server()
        
        # Keep server running
        await server.server.wait_closed()
        
    except Exception as e:
        logger.error(f"Failed to start Viz WebSocket server: {e}")
        raise


async def stop_websocket_server():
    """Stop the Viz WebSocket server"""
    try:
        await websocket_viz_server.stop_server()
    except Exception as e:
        logger.error(f"Error stopping Viz WebSocket server: {e}")


if __name__ == "__main__":
    # For standalone testing
    asyncio.run(start_websocket_server())
