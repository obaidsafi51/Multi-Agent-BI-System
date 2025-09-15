"""
Enhanced WebSocket MCP Client for Backend to TiDB MCP Server communication.
Provides persistent connection, request batching, and intelligent caching.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Callable
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum

import websockets
from websockets import WebSocketClientProtocol, ConnectionClosed

logger = logging.getLogger(__name__)


class RequestStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class PendingRequest:
    """Represents a pending WebSocket request"""
    request_id: str
    method: str
    params: Dict[str, Any]
    timestamp: float
    future: asyncio.Future
    timeout: float = 30.0


@dataclass
class CachedResult:
    """Represents a cached result with TTL"""
    data: Any
    timestamp: float
    ttl: float = 300.0  # 5 minutes default
    
    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl


class WebSocketMCPClient:
    """
    Enhanced WebSocket MCP Client with intelligent batching and caching.
    
    Features:
    - Persistent WebSocket connection
    - Request batching and deduplication
    - Client-side result caching
    - Automatic reconnection
    - Real-time schema updates
    """
    
    def __init__(self, server_url: Optional[str] = None, agent_type: str = "backend"):
        import os
        # Use environment variable or fallback to default
        default_url = os.getenv('MCP_SERVER_WS_URL', 'ws://tidb-mcp-server:8000/ws')
        self.server_url = (server_url or default_url).replace("http://", "ws://").replace("https://", "wss://")
        self.agent_type = agent_type
        
        # Create a stable agent ID that persists across reconnections
        # Use a hash of the agent type and server URL for consistency
        import hashlib
        stable_hash = hashlib.md5(f"{agent_type}_{self.server_url}".encode()).hexdigest()[:8]
        self.agent_id = f"{agent_type}_{stable_hash}"
        
        # Connection management
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1.0
        self._connection_lock = asyncio.Lock()
        self._connecting = False
        
        # Request management
        self.pending_requests: Dict[str, PendingRequest] = {}
        self.request_lock = asyncio.Lock()
        
        # Intelligent caching
        self.cache: Dict[str, CachedResult] = {}
        self.cache_lock = asyncio.Lock()
        
        # Batching support
        self.batch_queue: List[Dict[str, Any]] = []
        self.batch_timer: Optional[asyncio.Task] = None
        self.batch_delay = 0.1  # 100ms batch window
        self.max_batch_size = 10
        
        # Request deduplication
        self.active_requests: Dict[str, List[asyncio.Future]] = {}  # cache_key -> futures
        
        # Background tasks
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
    async def connect(self) -> bool:
        """Connect to the TiDB MCP Server via WebSocket."""
        # Prevent concurrent connection attempts
        async with self._connection_lock:
            # Check if already connected
            if self.is_connected and self.websocket and not self.websocket.closed:
                logger.debug(f"WebSocket MCP client already connected with agent_id: {self.agent_id}")
                return True
            
            # Check if connection attempt is in progress
            if self._connecting:
                logger.debug("Connection attempt already in progress")
                return False
                
            self._connecting = True
            
        try:
            logger.info(f"Attempting WebSocket connection to {self.server_url} with agent_id: {self.agent_id}")
            
            # Clean up any existing connection first
            if self.websocket and not self.websocket.closed:
                logger.debug("Closing existing WebSocket connection")
                await self.websocket.close()
            
            self.websocket = await websockets.connect(
                self.server_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            # Send initial connection message in the format expected by TiDB MCP server
            connection_msg = {
                "type": "event",
                "event_name": "agent_connected",
                "payload": {
                    "agent_id": self.agent_id,
                    "agent_type": self.agent_type,
                    "capabilities": [
                        "batch_requests",
                        "event_subscriptions", 
                        "schema_caching",
                        "request_deduplication"
                    ]
                },
                "timestamp": time.time()
            }
            
            await self.websocket.send(json.dumps(connection_msg))
            
            # Wait for connection acknowledgment
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10.0)
            response_data = json.loads(response)
            
            # Handle both connection_ack and connection_acknowledged events
            if response_data.get("type") == "connection_ack":
                self.is_connected = True
                self.reconnect_attempts = 0
                
                # Start background tasks
                await self._start_background_tasks()
                
                logger.info(f"Successfully connected to WebSocket MCP Server with agent_id: {self.agent_id}")
                self._connecting = False
                return True
            elif (response_data.get("type") == "event" and 
                  response_data.get("event_name") == "connection_acknowledged"):
                self.is_connected = True
                self.reconnect_attempts = 0
                
                # Start background tasks
                await self._start_background_tasks()
                
                logger.info(f"Successfully connected to WebSocket MCP Server with agent_id: {self.agent_id}")
                self._connecting = False
                return True
            else:
                logger.error(f"Unexpected connection response: {response_data}")
                
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket MCP Server: {e}")
            await self._cleanup_connection()
        finally:
            self._connecting = False
        
        return False
    
    async def disconnect(self):
        """Disconnect from the WebSocket MCP Server."""
        if not self.is_connected:
            logger.debug("WebSocket MCP client already disconnected")
            return
            
        logger.info(f"Disconnecting WebSocket MCP client {self.agent_id} from server")
        self.is_connected = False
        self._connecting = False
        
        # Stop background tasks
        await self._stop_background_tasks()
        
        # Cancel pending requests
        async with self.request_lock:
            for request in self.pending_requests.values():
                if not request.future.done():
                    request.future.set_exception(ConnectionClosed(None, None))
            self.pending_requests.clear()
        
        # Clear active request deduplication
        for cache_key, futures in self.active_requests.items():
            for future in futures:
                if not future.done():
                    future.set_exception(ConnectionClosed(None, None))
        self.active_requests.clear()
        
        # Close WebSocket connection
        await self._cleanup_connection()
        
        logger.info(f"WebSocket MCP client {self.agent_id} disconnected successfully")
        
    async def _cleanup_connection(self):
        """Clean up WebSocket connection."""
        if self.websocket:
            try:
                if not self.websocket.closed:
                    await self.websocket.close()
            except Exception as e:
                logger.debug(f"Error closing websocket: {e}")
            finally:
                self.websocket = None
                
    def _is_connection_healthy(self) -> bool:
        """Check if the WebSocket connection is healthy."""
        return (self.is_connected and 
                self.websocket is not None and 
                not self.websocket.closed)
    
    async def _start_background_tasks(self):
        """Start background tasks for message handling and maintenance."""
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Start message handling task
        asyncio.create_task(self._message_handler())
        
    async def _stop_background_tasks(self):
        """Stop background tasks."""
        tasks = [self.heartbeat_task, self.cleanup_task, self.batch_timer]
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    
    async def _message_handler(self):
        """Handle incoming WebSocket messages."""
        try:
            while self.is_connected and self.websocket:
                try:
                    message = await self.websocket.recv()
                    await self._process_message(json.loads(message))
                except ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    break
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue
        except Exception as e:
            logger.error(f"Message handler error: {e}")
        finally:
            await self._handle_disconnection()
    
    async def _process_message(self, message: Dict[str, Any]):
        """Process incoming WebSocket message."""
        message_type = message.get("type")
        
        if message_type == "response":
            await self._handle_response(message)
        elif message_type == "batch_response":
            await self._handle_batch_response(message)
        elif message_type == "event":
            await self._handle_event(message)
        elif message_type == "error":
            await self._handle_error(message)
        elif message_type == "pong":
            pass  # Heartbeat response
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def _handle_response(self, message: Dict[str, Any]):
        """Handle individual response message."""
        request_id = message.get("request_id")
        if not request_id:
            return
            
        async with self.request_lock:
            request = self.pending_requests.pop(request_id, None)
            
        if request:
            # Handle TiDB MCP server response format
            payload = message.get("payload", {})
            if payload.get("success", True):
                # Extract result from payload
                result = payload.get("databases") or payload.get("tables") or payload.get("data") or payload
                
                # Cache the result if it's a schema operation
                if request.method in ["get_table_schema", "discover_tables", "discover_databases"]:
                    await self._cache_result(request, result)
                
                request.future.set_result(result)
            else:
                error = payload.get("error") or message.get("error", "Unknown error")
                request.future.set_exception(Exception(error))
    
    async def _handle_batch_response(self, message: Dict[str, Any]):
        """Handle batch response message."""
        responses = message.get("responses", [])
        
        for response in responses:
            await self._handle_response(response)
    
    async def _handle_event(self, message: Dict[str, Any]):
        """Handle event message."""
        event_type = message.get("event_type")
        event_data = message.get("data")
        
        # Handle schema change events
        if event_type == "schema_changed":
            await self._handle_schema_change(event_data)
        
        # Call registered event handlers
        handlers = self.event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(event_data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
    
    async def _handle_schema_change(self, event_data: Dict[str, Any]):
        """Handle schema change event by invalidating cache."""
        database = event_data.get("database")
        table = event_data.get("table")
        
        async with self.cache_lock:
            # Invalidate related cache entries
            keys_to_remove = []
            for key in self.cache.keys():
                if database in key and (not table or table in key):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.cache[key]
                
        logger.info(f"Invalidated cache for schema change: {database}.{table}")
    
    async def _handle_error(self, message: Dict[str, Any]):
        """Handle error message."""
        request_id = message.get("request_id")
        error_msg = message.get("error", "Unknown error")
        
        if request_id:
            async with self.request_lock:
                request = self.pending_requests.pop(request_id, None)
                
            if request:
                request.future.set_exception(Exception(error_msg))
    
    async def _cache_result(self, request: PendingRequest, result: Any):
        """Cache the result of a successful request."""
        cache_key = self._get_cache_key(request.method, request.params)
        
        async with self.cache_lock:
            # Determine TTL based on operation type
            ttl = 300.0  # 5 minutes default
            if request.method == "get_table_schema":
                ttl = 600.0  # 10 minutes for schema (less frequent changes)
            elif request.method in ["discover_databases", "discover_tables"]:
                ttl = 180.0  # 3 minutes for discovery (moderate changes)
                
            self.cache[cache_key] = CachedResult(
                data=result,
                timestamp=time.time(),
                ttl=ttl
            )
    
    def _get_cache_key(self, method: str, params: Dict[str, Any]) -> str:
        """Generate cache key for method and parameters."""
        # Sort params for consistent keys
        sorted_params = json.dumps(params, sort_keys=True)
        return f"{method}:{sorted_params}"
    
    async def _get_cached_result(self, method: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached result if available and not expired."""
        cache_key = self._get_cache_key(method, params)
        
        async with self.cache_lock:
            cached = self.cache.get(cache_key)
            if cached and not cached.is_expired():
                logger.debug(f"Cache hit for {method}: {cache_key}")
                return cached.data
            elif cached:
                # Remove expired entry
                del self.cache[cache_key]
                logger.debug(f"Cache expired for {method}: {cache_key}")
        
        return None
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages."""
        try:
            while self.is_connected:
                await asyncio.sleep(30)
                if self.websocket and self.is_connected:
                    ping_msg = {"type": "ping", "timestamp": time.time()}
                    await self.websocket.send(json.dumps(ping_msg))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
    
    async def _cleanup_loop(self):
        """Periodic cleanup of expired cache entries and timed-out requests."""
        try:
            while self.is_connected:
                await asyncio.sleep(60)  # Run every minute
                
                current_time = time.time()
                
                # Clean expired cache entries
                async with self.cache_lock:
                    expired_keys = [
                        key for key, cached in self.cache.items()
                        if cached.is_expired()
                    ]
                    for key in expired_keys:
                        del self.cache[key]
                    
                    if expired_keys:
                        logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")
                
                # Clean timed-out requests
                async with self.request_lock:
                    timed_out = [
                        req_id for req_id, request in self.pending_requests.items()
                        if current_time - request.timestamp > request.timeout
                    ]
                    
                    for req_id in timed_out:
                        request = self.pending_requests.pop(req_id)
                        if not request.future.done():
                            request.future.set_exception(TimeoutError(f"Request {req_id} timed out"))
                    
                    if timed_out:
                        logger.warning(f"Cleaned {len(timed_out)} timed-out requests")
                        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Cleanup loop error: {e}")
    
    async def _handle_disconnection(self):
        """Handle WebSocket disconnection with reconnection logic."""
        self.is_connected = False
        
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = min(self.reconnect_delay * (2 ** self.reconnect_attempts), 30)
            
            logger.info(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts} in {delay}s")
            await asyncio.sleep(delay)
            
            if await self.connect():
                logger.info("Successfully reconnected to WebSocket MCP Server")
            else:
                await self._handle_disconnection()  # Retry
        else:
            logger.error("Maximum reconnection attempts reached. Connection failed.")
    
    async def call_tool(self, method: str, **params) -> Any:
        """
        Call an MCP tool with intelligent caching and deduplication.
        
        Args:
            method: Tool method name
            **params: Tool parameters
            
        Returns:
            Tool result
        """
        # Check cache first
        cached_result = await self._get_cached_result(method, params)
        if cached_result is not None:
            return cached_result
        
        # Check for duplicate in-flight requests
        cache_key = self._get_cache_key(method, params)
        
        # If same request is already in flight, wait for it
        if cache_key in self.active_requests:
            logger.debug(f"Deduplicating request for {method}")
            future = asyncio.Future()
            self.active_requests[cache_key].append(future)
            return await future
        
        # Create new request
        self.active_requests[cache_key] = []
        
        try:
            # Check connection health and reconnect if needed
            if not self._is_connection_healthy():
                logger.info("WebSocket connection unhealthy, attempting to reconnect")
                connected = await self.connect()
                if not connected:
                    raise Exception("Failed to establish WebSocket connection to MCP Server")
            
            request_id = str(uuid.uuid4())
            future = asyncio.Future()
            
            request = PendingRequest(
                request_id=request_id,
                method=method,
                params=params,
                timestamp=time.time(),
                future=future
            )
            
            async with self.request_lock:
                self.pending_requests[request_id] = request
            
            # Send request
            message = {
                "type": "request",
                "request_id": request_id,
                "method": method,
                "params": params,
                "timestamp": time.time()
            }
            
            await self.websocket.send(json.dumps(message))
            
            # Wait for response
            result = await future
            
            # Notify duplicate requesters
            duplicates = self.active_requests.pop(cache_key, [])
            for dup_future in duplicates:
                if not dup_future.done():
                    dup_future.set_result(result)
            
            return result
            
        except Exception as e:
            # Notify duplicate requesters of error
            duplicates = self.active_requests.pop(cache_key, [])
            for dup_future in duplicates:
                if not dup_future.done():
                    dup_future.set_exception(e)
            raise
    
    # Convenience methods for common operations
    async def get_table_schema(self, database: str, table: str) -> Dict[str, Any]:
        """Get table schema with caching."""
        return await self.call_tool("get_table_schema", database=database, table=table)
    
    async def discover_tables(self, database: str) -> List[Dict[str, Any]]:
        """Discover tables with caching."""
        return await self.call_tool("discover_tables", database=database)
    
    async def discover_databases(self) -> List[Dict[str, Any]]:
        """Discover databases with caching."""
        return await self.call_tool("discover_databases")
    
    async def execute_query(self, query: str, timeout: Optional[int] = None, use_cache: bool = True) -> Dict[str, Any]:
        """Execute SQL query."""
        params = {"query": query, "use_cache": use_cache}
        if timeout:
            params["timeout"] = timeout
        return await self.call_tool("execute_query", **params)
    
    async def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        return await self.call_tool("get_server_stats")
    
    def subscribe_to_events(self, event_type: str, handler: Callable):
        """Subscribe to real-time events."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    @asynccontextmanager
    async def connection(self):
        """Context manager for WebSocket connection."""
        connected = await self.connect()
        if not connected:
            raise Exception("Failed to connect to WebSocket MCP Server")
        
        try:
            yield self
        finally:
            await self.disconnect()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get client-side cache statistics."""
        total_entries = len(self.cache)
        expired_entries = sum(1 for cached in self.cache.values() if cached.is_expired())
        
        return {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
            "pending_requests": len(self.pending_requests),
            "active_dedup_requests": len(self.active_requests)
        }
