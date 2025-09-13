"""
NLP Agent WebSocket Server v2.2.0
Simple WebSocket server for NLP agent with heartbeat support
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Set
from websockets.server import WebSocketServerProtocol, serve

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NLPWebSocketServer:
    """WebSocket server for NLP Agent with basic functionality"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8011):
        self.host = host
        self.port = port
        self.connections: Set[WebSocketServerProtocol] = set()
        self.server = None
        
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str = "/"):
        """Handle new WebSocket connection"""
        client_id = f"nlp-client-{uuid.uuid4().hex[:8]}"
        logger.info(f"New WebSocket connection from {websocket.remote_address} on path {path} (ID: {client_id})")
        
        # Add to active connections
        self.connections.add(websocket)
        
        try:
            # Send welcome message
            welcome_message = {
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "server": "nlp-agent-websocket",
                "version": "2.2.0"
            }
            await websocket.send(json.dumps(welcome_message))
            
            # Handle messages
            async for message in websocket:
                await self.handle_message(websocket, message, client_id)
                
        except Exception as e:
            logger.error(f"Error in connection {client_id}: {str(e)}")
        finally:
            # Remove from active connections
            self.connections.discard(websocket)
            logger.info(f"Connection {client_id} closed")
            
    async def handle_message(self, websocket: WebSocketServerProtocol, message: str, client_id: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            message_type = data.get("type", "").lower()
            
            logger.info(f"NLP agent received message type: '{message_type}' from {client_id}")
            
            if message_type in ["heartbeat", "ping"]:
                await self.handle_heartbeat(websocket, data, client_id)
            elif message_type == "test_message":
                # Handle test messages from connectivity tests
                response = {
                    "type": "test_response",
                    "message": "Test message received successfully",
                    "client_id": client_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "correlation_id": data.get("correlation_id")
                }
                await websocket.send(json.dumps(response))
            else:
                # For now, just acknowledge unknown message types
                await self.send_error(websocket, f"Message type '{message_type}' received but not implemented", client_id)
                
        except json.JSONDecodeError:
            await self.send_error(websocket, "Invalid JSON message", client_id)
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {str(e)}")
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
        
    async def send_error(self, websocket: WebSocketServerProtocol, error_message: str, client_id: str):
        """Send error response"""
        error_response = {
            "type": "error",
            "error": error_message,
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send(json.dumps(error_response))
        
    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"Starting NLP WebSocket server on {self.host}:{self.port}")
        try:
            self.server = await serve(
                self.handle_connection,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10
            )
            logger.info(f"NLP WebSocket server started successfully on {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start NLP WebSocket server: {str(e)}")
            raise
            
    async def stop_server(self):
        """Stop the WebSocket server"""
        if self.server:
            logger.info("Stopping NLP WebSocket server...")
            self.server.close()
            await self.server.wait_closed()
            logger.info("NLP WebSocket server stopped")

# Global server instance
websocket_server = None

async def start_websocket_server():
    """Start the WebSocket server"""
    global websocket_server
    try:
        websocket_server = NLPWebSocketServer()
        await websocket_server.start_server()
        
        # Keep the server running
        if websocket_server.server:
            await websocket_server.server.wait_closed()
    except Exception as e:
        logger.error(f"Error starting WebSocket server: {str(e)}")
        raise

async def stop_websocket_server():
    """Stop the WebSocket server"""
    global websocket_server
    if websocket_server:
        await websocket_server.stop_server()

if __name__ == "__main__":
    asyncio.run(start_websocket_server())
