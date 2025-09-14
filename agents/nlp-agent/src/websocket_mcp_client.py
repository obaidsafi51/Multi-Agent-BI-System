"""
WebSocket-based MCP Client for optimized communication with TiDB MCP Server.
Provides persistent connections, request batching, and real-time event handling.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """WebSocket message types"""
    REQUEST = "request"
    RESPONSE = "response" 
    BATCH_REQUEST = "batch_request"
    BATCH_RESPONSE = "batch_response"
    EVENT = "event"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class WebSocketMCPClientError(Exception):
    """Base exception for WebSocket MCP client errors"""
    pass


class ConnectionError(WebSocketMCPClientError):
    """Connection-related errors"""
    pass


class RequestTimeoutError(WebSocketMCPClientError):
    """Request timeout errors"""
    pass


class RequestBatcher:
    """Intelligent request batching for improved performance"""
    
    def __init__(self, batch_size: int = 5, batch_timeout: float = 0.1):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_requests = []
        self.batch_lock = asyncio.Lock()
        self.batch_timer = None
        
    async def add_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Add request to batch and return result when processed"""
        future = asyncio.Future()
        
        async with self.batch_lock:
            self.pending_requests.append({
                "request": request,
                "future": future,
                "timestamp": time.time()
            })
            
            # Trigger immediate batch if size threshold reached
            if len(self.pending_requests) >= self.batch_size:
                if self.batch_timer:
                    self.batch_timer.cancel()
                asyncio.create_task(self._process_batch())
            elif len(self.pending_requests) == 1:
                # Start timeout timer for first request in batch
                self.batch_timer = asyncio.create_task(self._batch_timeout_handler())
        
        return await future
    
    async def _batch_timeout_handler(self):
        """Handle batch timeout - process batch when timeout reached"""
        try:
            await asyncio.sleep(self.batch_timeout)
            await self._process_batch()
        except asyncio.CancelledError:
            pass  # Timer was cancelled due to batch size threshold
    
    async def _process_batch(self):
        """Process accumulated batch of requests"""
        async with self.batch_lock:
            if not self.pending_requests:
                return
                
            batch = self.pending_requests.copy()
            self.pending_requests.clear()
            self.batch_timer = None
        
        if len(batch) == 1:
            # Single request - send directly
            item = batch[0]
            try:
                result = await self._send_single_request(item["request"])
                item["future"].set_result(result)
            except Exception as e:
                item["future"].set_exception(e)
        else:
            # Multiple requests - send as batch
            try:
                batch_requests = [item["request"] for item in batch]
                results = await self._send_batch_request(batch_requests)
                
                # Resolve futures with results
                for item, result in zip(batch, results):
                    if isinstance(result, Exception):
                        item["future"].set_exception(result)
                    else:
                        item["future"].set_result(result)
                        
            except Exception as e:
                # Resolve all futures with error
                for item in batch:
                    item["future"].set_exception(e)
    
    def set_client(self, client):
        """Set the WebSocket client for sending requests"""
        self.client = client
    
    async def _send_single_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send single request via WebSocket client"""
        return await self.client._send_request_internal(request)
    
    async def _send_batch_request(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Send batch request via WebSocket client"""
        return await self.client._send_batch_request_internal(requests)


class WebSocketMCPClient:
    """
    WebSocket-based MCP client for persistent connection to TiDB MCP Server.
    Optimized for multi-agent architecture with connection sharing and event handling.
    """
    
    def __init__(
        self,
        ws_url: str = "ws://tidb-mcp-server:8000/ws",
        agent_id: str = "nlp-agent",
        ping_interval: int = 30,
        ping_timeout: int = 10,
        close_timeout: int = 10,
        max_message_size: int = 10**7,
        reconnect_delay: float = 5.0,
        max_reconnect_attempts: int = 10,
        enable_batching: bool = True,
        batch_size: int = 5,
        batch_timeout: float = 0.1
    ):
        self.ws_url = ws_url
        self.agent_id = agent_id
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.close_timeout = close_timeout
        self.max_message_size = max_message_size
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        
        # Connection state
        self.websocket = None
        self.is_connected = False
        self.connection_lock = asyncio.Lock()
        self.reconnect_count = 0
        
        # Request handling
        self.request_id_counter = 0
        self.pending_requests = {}
        self.request_timeout = 30.0
        
        # Event handling
        self.event_handlers = {}
        self.message_handler_task = None
        self.heartbeat_task = None
        
        # Request batching
        self.enable_batching = enable_batching
        if self.enable_batching:
            self.request_batcher = RequestBatcher(batch_size, batch_timeout)
            self.request_batcher.set_client(self)
        
        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "batched_requests": 0,
            "connection_count": 0,
            "reconnection_count": 0,
            "total_latency": 0.0,
            "event_count": 0
        }
        
        logger.info(f"WebSocket MCP client initialized for agent {agent_id}")
    
    async def connect(self) -> bool:
        """Establish WebSocket connection to MCP server"""
        async with self.connection_lock:
            if self.is_connected:
                return True
            
            try:
                logger.info(f"Connecting to MCP server at {self.ws_url}")
                
                self.websocket = await websockets.connect(
                    self.ws_url,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                    close_timeout=self.close_timeout,
                    max_size=self.max_message_size
                )
                
                self.is_connected = True
                self.reconnect_count = 0
                self.metrics["connection_count"] += 1
                
                # Start message handler and heartbeat
                self.message_handler_task = asyncio.create_task(self._message_handler())
                self.heartbeat_task = asyncio.create_task(self._heartbeat_handler())
                
                # Send connection initialization
                await self._send_connection_init()
                
                logger.info("WebSocket connection established with MCP server")
                return True
                
            except Exception as e:
                logger.error(f"Failed to establish WebSocket connection: {e}")
                self.is_connected = False
                return False
    
    async def disconnect(self):
        """Gracefully disconnect from MCP server"""
        async with self.connection_lock:
            if not self.is_connected:
                return
            
            logger.info("Disconnecting from MCP server")
            
            # Cancel background tasks
            if self.message_handler_task:
                self.message_handler_task.cancel()
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            
            # Close WebSocket connection
            if self.websocket:
                try:
                    await self.websocket.close()
                except:
                    pass
            
            self.is_connected = False
            self.websocket = None
            
            # Reject all pending requests
            for request_id, future in self.pending_requests.items():
                if not future.done():
                    future.set_exception(ConnectionError("Connection closed"))
            self.pending_requests.clear()
            
            logger.info("Disconnected from MCP server")
    
    async def _reconnect(self):
        """Attempt to reconnect to MCP server"""
        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached")
            return False
        
        self.reconnect_count += 1
        self.metrics["reconnection_count"] += 1
        
        wait_time = min(self.reconnect_delay * (2 ** (self.reconnect_count - 1)), 60)
        logger.info(f"Attempting reconnection {self.reconnect_count}/{self.max_reconnect_attempts} in {wait_time}s")
        
        await asyncio.sleep(wait_time)
        return await self.connect()
    
    async def _send_connection_init(self):
        """Send connection initialization message"""
        init_message = {
            "type": MessageType.EVENT.value,
            "event_name": "agent_connected",
            "payload": {
                "agent_id": self.agent_id,
                "agent_type": "nlp-agent",
                "capabilities": [
                    "natural_language_processing",
                    "intent_extraction",
                    "entity_recognition",
                    "query_classification",
                    "context_building"
                ],
                "version": "2.0.0",
                "connection_time": datetime.now().isoformat()
            }
        }
        await self.websocket.send(json.dumps(init_message))
    
    async def _message_handler(self):
        """Handle incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse WebSocket message: {e}")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
                    
        except ConnectionClosed:
            logger.warning("WebSocket connection closed by server")
            self.is_connected = False
            if self.reconnect_count < self.max_reconnect_attempts:
                await self._reconnect()
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.is_connected = False
            await self._reconnect()
        except Exception as e:
            logger.error(f"Unexpected error in message handler: {e}")
    
    async def _process_message(self, data: Dict[str, Any]):
        """Process incoming WebSocket message"""
        message_type = data.get("type")
        
        if message_type == MessageType.RESPONSE.value:
            await self._handle_response(data)
        elif message_type == MessageType.BATCH_RESPONSE.value:
            await self._handle_batch_response(data)
        elif message_type == MessageType.EVENT.value:
            await self._handle_event(data)
        elif message_type == MessageType.ERROR.value:
            await self._handle_error(data)
        elif message_type == MessageType.PONG.value:
            await self._handle_pong(data)
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def _handle_response(self, data: Dict[str, Any]):
        """Handle response message"""
        request_id = data.get("request_id")
        if request_id in self.pending_requests:
            future = self.pending_requests.pop(request_id)
            if not future.done():
                future.set_result(data.get("payload"))
    
    async def _handle_batch_response(self, data: Dict[str, Any]):
        """Handle batch response message"""
        request_id = data.get("request_id")
        if request_id in self.pending_requests:
            future = self.pending_requests.pop(request_id)
            if not future.done():
                future.set_result(data.get("results", []))
    
    async def _handle_event(self, data: Dict[str, Any]):
        """Handle event message from server"""
        event_name = data.get("event_name")
        payload = data.get("payload", {})
        
        self.metrics["event_count"] += 1
        
        # Call registered event handlers
        if event_name in self.event_handlers:
            try:
                await self.event_handlers[event_name](payload)
            except Exception as e:
                logger.error(f"Error in event handler for {event_name}: {e}")
        
        # Handle built-in events
        if event_name == "schema_update":
            logger.info("Received schema update event from MCP server")
        elif event_name == "cache_invalidation":
            logger.info("Received cache invalidation event from MCP server")
        elif event_name == "server_status":
            logger.debug(f"Received server status: {payload}")
    
    async def _handle_error(self, data: Dict[str, Any]):
        """Handle error message"""
        request_id = data.get("request_id")
        error_message = data.get("error", "Unknown error")
        
        if request_id in self.pending_requests:
            future = self.pending_requests.pop(request_id)
            if not future.done():
                future.set_exception(WebSocketMCPClientError(error_message))
    
    async def _handle_pong(self, data: Dict[str, Any]):
        """Handle pong message"""
        logger.debug("Received pong from MCP server")
    
    async def _heartbeat_handler(self):
        """Send periodic heartbeat to maintain connection"""
        while self.is_connected:
            try:
                await asyncio.sleep(self.ping_interval)
                if self.is_connected and self.websocket:
                    ping_message = {
                        "type": MessageType.PING.value,
                        "timestamp": datetime.now().isoformat(),
                        "agent_id": self.agent_id
                    }
                    await self.websocket.send(json.dumps(ping_message))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat handler: {e}")
                break
    
    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        use_batching: bool = None
    ) -> Dict[str, Any]:
        """Send request to MCP server with optional batching"""
        if not self.is_connected:
            if not await self.connect():
                raise ConnectionError("Cannot establish connection to MCP server")
        
        request = {
            "method": method,
            "params": params or {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Use batching if enabled and not explicitly disabled
        if self.enable_batching and (use_batching is None or use_batching):
            return await self.request_batcher.add_request(request)
        else:
            return await self._send_request_internal(request)
    
    async def _send_request_internal(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send single request directly"""
        start_time = time.time()
        
        request_id = f"req_{self.agent_id}_{self.request_id_counter}"
        self.request_id_counter += 1
        
        message = {
            "type": MessageType.REQUEST.value,
            "request_id": request_id,
            **request
        }
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        try:
            # Send request
            await self.websocket.send(json.dumps(message))
            self.metrics["total_requests"] += 1
            
            # Wait for response with timeout
            result = await asyncio.wait_for(future, timeout=self.request_timeout)
            
            # Update metrics
            latency = time.time() - start_time
            self.metrics["total_latency"] += latency
            
            return result
            
        except asyncio.TimeoutError:
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            raise RequestTimeoutError(f"Request {request_id} timed out after {self.request_timeout}s")
        except Exception as e:
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            raise WebSocketMCPClientError(f"Request failed: {e}")
    
    async def _send_batch_request_internal(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Send batch request directly"""
        start_time = time.time()
        
        request_id = f"batch_{self.agent_id}_{self.request_id_counter}"
        self.request_id_counter += 1
        
        message = {
            "type": MessageType.BATCH_REQUEST.value,
            "request_id": request_id,
            "requests": requests,
            "timestamp": datetime.now().isoformat()
        }
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        try:
            # Send batch request
            await self.websocket.send(json.dumps(message))
            self.metrics["total_requests"] += len(requests)
            self.metrics["batched_requests"] += 1
            
            # Wait for response with timeout
            results = await asyncio.wait_for(future, timeout=self.request_timeout * 2)
            
            # Update metrics
            latency = time.time() - start_time
            self.metrics["total_latency"] += latency
            
            return results
            
        except asyncio.TimeoutError:
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            raise RequestTimeoutError(f"Batch request {request_id} timed out")
        except Exception as e:
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            raise WebSocketMCPClientError(f"Batch request failed: {e}")
    
    def register_event_handler(self, event_name: str, handler: Callable):
        """Register event handler for specific event type"""
        self.event_handlers[event_name] = handler
        logger.info(f"Registered event handler for {event_name}")
    
    def unregister_event_handler(self, event_name: str):
        """Unregister event handler"""
        if event_name in self.event_handlers:
            del self.event_handlers[event_name]
            logger.info(f"Unregistered event handler for {event_name}")
    
    async def health_check(self) -> bool:
        """Check connection health"""
        try:
            if not self.is_connected:
                return False
            
            result = await self.send_request("health_check", use_batching=False)
            return result.get("status") == "healthy"
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        avg_latency = (
            self.metrics["total_latency"] / self.metrics["total_requests"]
            if self.metrics["total_requests"] > 0 else 0
        )
        
        batch_efficiency = (
            self.metrics["batched_requests"] / self.metrics["total_requests"]
            if self.metrics["total_requests"] > 0 else 0
        )
        
        return {
            **self.metrics,
            "is_connected": self.is_connected,
            "reconnect_count": self.reconnect_count,
            "average_latency": avg_latency,
            "batch_efficiency": batch_efficiency
        }


# Convenience methods for common MCP operations
class MCPOperations:
    """Helper class for common MCP operations via WebSocket"""
    
    def __init__(self, ws_client: WebSocketMCPClient):
        self.client = ws_client
    
    async def get_schema_context(self, databases: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get database schema context"""
        return await self.client.send_request(
            "build_schema_context",
            {"databases": databases} if databases else {}
        )
    
    async def generate_sql(
        self,
        natural_language_query: str,
        schema_info: Optional[str] = None,
        examples: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate SQL query from natural language"""
        return await self.client.send_request(
            "llm_generate_sql_tool",
            {
                "natural_language_query": natural_language_query,
                "schema_info": schema_info,
                "examples": examples
            }
        )
    
    async def validate_query(self, query: str) -> Dict[str, Any]:
        """Validate SQL query"""
        return await self.client.send_request(
            "validate_query_tool",
            {"query": query}
        )
    
    async def execute_query(
        self,
        query: str,
        timeout: Optional[int] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Execute SQL query"""
        params = {
            "query": query,
            "use_cache": use_cache
        }
        if timeout:
            params["timeout"] = timeout
        
        return await self.client.send_request("execute_query_tool", params)
    
    async def analyze_data(
        self,
        data: str,
        analysis_type: str = "financial",
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze data using LLM"""
        return await self.client.send_request(
            "llm_analyze_data_tool",
            {
                "data": data,
                "analysis_type": analysis_type,
                "context": context
            }
        )
