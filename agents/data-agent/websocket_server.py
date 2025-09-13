"""
Data Agent WebSocket Server

WebSocket server for data agent with real-time SQL query processing,
connection management, and enhanced performance monitoring.
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

from src.mcp_agent import MCPDataAgent
from src.optimization.optimizer import get_query_optimizer
from src.cache.manager import get_cache_manager

logger = logging.getLogger(__name__)


class WebSocketDataServer:
    """WebSocket server for Data agent with connection management and query processing"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8012):
        self.host = host
        self.port = port
        self.server = None
        self.connections: Set[WebSocketServerProtocol] = set()
        
        # Agent components (will be initialized)
        self.data_agent: Optional[MCPDataAgent] = None
        self.query_optimizer: Optional[Any] = None
        self.cache_manager: Optional[Any] = None
        
        # Statistics
        self.start_time = time.time()
        self.message_count = 0
        self.connection_count = 0
        self.query_count = 0
    
    async def initialize_agent(self):
        """Initialize the Data agent and its components"""
        try:
            logger.info("Initializing Enhanced Data Agent components for WebSocket server...")
            
            # Initialize cache manager
            self.cache_manager = get_cache_manager()
            
            # Initialize query optimizer
            self.query_optimizer = get_query_optimizer()
            
            # Initialize main Data agent
            self.data_agent = MCPDataAgent()
            await self.data_agent.initialize()
            
            logger.info("Enhanced Data Agent components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Data agent: {e}")
            raise
    
    async def start_server(self):
        """Start the WebSocket server"""
        try:
            await self.initialize_agent()
            
            logger.info(f"Starting Data WebSocket server on {self.host}:{self.port}")
            
            self.server = await websockets.serve(
                self.handle_connection,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5,
                process_request=self.process_request
            )
            
            logger.info(f"Data WebSocket server started on ws://{self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start Data WebSocket server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the WebSocket server"""
        try:
            if self.server:
                self.server.close()
                await self.server.wait_closed()
                logger.info("Data WebSocket server stopped")
            
            # Close all connections
            if self.connections:
                await asyncio.gather(
                    *[conn.close() for conn in self.connections],
                    return_exceptions=True
                )
                self.connections.clear()
            
            # Cleanup agent components
            if self.cache_manager:
                await self.cache_manager.close()
                
        except Exception as e:
            logger.error(f"Error stopping Data WebSocket server: {e}")
    
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
        client_id = f"data-client-{uuid.uuid4().hex[:8]}"
        self.connections.add(websocket)
        self.connection_count += 1
        
        logger.info(f"Data agent WebSocket connection established on path {path}: {client_id}")
        
        try:
            # Send welcome message
            welcome_message = {
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "server": "data-agent-websocket",
                "version": "2.2.0"
            }
            await websocket.send(json.dumps(welcome_message))
            
            # Handle messages
            async for message in websocket:
                try:
                    if isinstance(message, str):
                        logger.info(f"Received string message from {client_id}: {message}")
                        data = json.loads(message)
                        logger.info(f"Parsed JSON data: {data}")
                        await self.handle_message(websocket, data, client_id)
                    else:
                        logger.info(f"Received non-string message from {client_id}: {type(message)}")
                    self.message_count += 1
                    
                except json.JSONDecodeError:
                    logger.error(f"JSON decode error for message from {client_id}: {message}")
                    await self.send_error(websocket, "Invalid JSON message", client_id)
                except Exception as e:
                    logger.error(f"Error handling message from {client_id}: {e}")
                    await self.send_error(websocket, str(e), client_id)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Data agent WebSocket connection closed: {client_id}")
        except Exception as e:
            logger.error(f"Error in Data agent WebSocket connection {client_id}: {e}")
        finally:
            self.connections.discard(websocket)
    
    async def handle_message(self, websocket: WebSocketServerProtocol, data: Dict, client_id: str):
        """Handle incoming WebSocket message"""
        message_type = data.get("type", "unknown").lower()
        message_id = data.get("message_id", str(uuid.uuid4()))
        
        logger.info(f"Data agent received message type: '{message_type}' from {client_id}")
        
        try:
            # Process specific message types
            if message_type in ["heartbeat", "ping"]:
                logger.info(f"Handling heartbeat message for {client_id}")
                await self.handle_heartbeat(websocket, data, client_id)
            elif message_type == "sql_query":
                await self.handle_sql_query(websocket, data, client_id, message_id)
            elif message_type == "health_check":
                await self.handle_health_check(websocket, data, client_id, message_id)
            elif message_type == "stats":
                await self.handle_stats_request(websocket, data, client_id, message_id)
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
    
    async def handle_sql_query(self, websocket: WebSocketServerProtocol, data: Dict, client_id: str, message_id: str):
        """Handle SQL query request"""
        try:
            if not self.data_agent:
                raise RuntimeError("Data agent not initialized")
            
            sql_query = data.get("sql_query", "")
            query_context = data.get("query_context", {})
            query_id = data.get("query_id", str(uuid.uuid4()))
            execution_config = data.get("execution_config", {})
            
            if not sql_query:
                await self.send_error(websocket, "Missing sql_query in request", client_id)
                return
            
            # Send processing status
            await self.send_progress(websocket, message_id, client_id, "processing", 20)
            
            # Execute SQL query through MCP data agent
            start_time = time.time()
            result = await self.data_agent.execute_sql(
                sql_query=sql_query,
                query_context=query_context,
                query_id=query_id,
                execution_config=execution_config
            )
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            self.query_count += 1
            
            # Send completion status
            await self.send_progress(websocket, message_id, client_id, "completed", 100)
            
            # Send result
            response = {
                "type": "sql_query_response",
                "response_to": message_id,
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "query_id": query_id,
                "result": result,
                "processing_time_ms": processing_time
            }
            
            await websocket.send(json.dumps(response))
            logger.info(f"SQL query processed for {client_id} in {processing_time:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error processing SQL query for {client_id}: {e}")
            await self.send_error(websocket, str(e), client_id)
    
    async def handle_health_check(self, websocket: WebSocketServerProtocol, data: Dict, client_id: str, message_id: str):
        """Handle health check request"""
        uptime = time.time() - self.start_time
        
        health_data = {
            "status": "healthy",
            "uptime": uptime,
            "connections": len(self.connections),
            "messages_processed": self.message_count,
            "queries_processed": self.query_count,
            "version": "2.2.0",
            "agent_ready": self.data_agent is not None,
            "cache_status": "active" if self.cache_manager else "inactive",
            "optimizer_status": "active" if self.query_optimizer else "inactive"
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
            "server": "data-agent-websocket",
            "version": "2.2.0",
            "uptime": uptime,
            "connections": len(self.connections),
            "total_connections": self.connection_count,
            "messages_processed": self.message_count,
            "queries_processed": self.query_count,
            "agent_initialized": self.data_agent is not None,
            "status": "running" if self.server else "stopped"
        }


# Global WebSocket server instance
websocket_data_server = WebSocketDataServer()


# Server control functions
async def start_websocket_server():
    """Start the Data WebSocket server"""
    try:
        host = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
        port = int(os.getenv("WEBSOCKET_PORT", "8012"))
        
        server = WebSocketDataServer(host, port)
        await server.start_server()
        
        # Keep server running
        await server.server.wait_closed()
        
    except Exception as e:
        logger.error(f"Failed to start Data WebSocket server: {e}")
        raise


async def stop_websocket_server():
    """Stop the Data WebSocket server"""
    try:
        await websocket_data_server.stop_server()
    except Exception as e:
        logger.error(f"Error stopping Data WebSocket server: {e}")


if __name__ == "__main__":
    # For standalone testing
    asyncio.run(start_websocket_server())
