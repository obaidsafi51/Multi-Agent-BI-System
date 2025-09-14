"""
Enhanced WebSocket MCP Client with improved reliability, connection management, and performance monitoring.
Addresses connection stability issues and provides better error handling and reconnection logic.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException, InvalidStatusCode

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Connection statistics and metrics"""
    connection_attempts: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    reconnection_attempts: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_successful_connection: Optional[datetime] = None
    last_connection_error: Optional[str] = None
    uptime_seconds: float = 0.0


class ConnectionState(Enum):
    """WebSocket connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


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


class EnhancedWebSocketMCPClient:
    """
    Enhanced WebSocket MCP client with improved reliability features:
    - Exponential backoff reconnection strategy
    - Connection health monitoring with automatic recovery
    - Circuit breaker pattern for failed requests
    - Comprehensive error handling and logging
    - Performance metrics and monitoring
    - Request retry mechanism with timeout handling
    """
    
    def __init__(
        self,
        ws_url: str = "ws://tidb-mcp-server:8000/ws",
        agent_id: str = "nlp-agent",
        # Connection settings - optimized for KIMI API processing
        initial_reconnect_delay: float = 3.0,  # Start with reasonable delay
        max_reconnect_delay: float = 60.0,  # Longer max delay for stability
        max_reconnect_attempts: int = -1,  # Unlimited
        connection_timeout: float = 30.0,  # Increased timeout for Docker + network latency
        request_timeout: float = 180.0,  # 3 minutes for KIMI API processing
        # Health check settings - optimized for KIMI API response times
        heartbeat_interval: float = 45.0,  # Balanced heartbeat interval
        health_check_interval: float = 120.0,  # Less frequent health checks
        ping_timeout: float = 20.0,  # Increased ping timeout
        # Circuit breaker settings - more tolerant for KIMI API variability
        circuit_breaker_threshold: int = 8,  # More tolerant threshold
        circuit_breaker_timeout: float = 120.0,  # Longer cooldown period
        # Performance settings
        max_concurrent_requests: int = 100,
        enable_request_batching: bool = True,
        batch_size: int = 5,
        batch_timeout: float = 0.1
    ):
        # Connection configuration
        self.ws_url = ws_url
        self.agent_id = agent_id
        self.initial_reconnect_delay = initial_reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.connection_timeout = connection_timeout
        self.request_timeout = request_timeout
        
        # Health monitoring
        self.heartbeat_interval = heartbeat_interval
        self.health_check_interval = health_check_interval
        self.ping_timeout = ping_timeout
        
        # Circuit breaker
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        self.circuit_breaker_failures = 0
        self.circuit_breaker_last_failure = 0
        self.circuit_breaker_open = False
        
        # Performance settings
        self.max_concurrent_requests = max_concurrent_requests
        self.enable_request_batching = enable_request_batching
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        
        # Connection state
        self.websocket = None
        self.connection_state = ConnectionState.DISCONNECTED
        self.connection_lock = asyncio.Lock()
        self.stats = ConnectionStats()
        
        # Request handling
        self.request_id_counter = 0
        self.pending_requests = {}
        self.request_semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # Background tasks
        self.message_handler_task = None
        self.heartbeat_task = None
        self.health_monitor_task = None
        self.reconnection_task = None
        
        # Event handling
        self.event_handlers = {}
        self.connection_event_handlers = []
        
        # Request batching
        if self.enable_request_batching:
            self.batch_requests = []
            self.batch_lock = asyncio.Lock()
            self.batch_timer = None
        
        # Performance tracking
        self.last_request_times = []
        self.connection_start_time = None
        
        logger.info(f"Enhanced WebSocket MCP client initialized for {agent_id}")
    
    def _is_websocket_open(self) -> bool:
        """
        Check if WebSocket connection is open using multiple detection methods
        with improved reliability and error handling
        """
        if self.websocket is None:
            return False
            
        try:
            # Method 1: Check using state property (websockets 12.0+/15.0+)
            if hasattr(self.websocket, 'state'):
                try:
                    from websockets.protocol import State
                    is_open = self.websocket.state == State.OPEN
                    logger.debug(f"WebSocket state check: {self.websocket.state.name} -> {is_open}")
                    return is_open
                except (ImportError, AttributeError) as e:
                    logger.debug(f"State check failed: {e}")
                    
            # Method 2: Check using closed attribute (websockets 10.x/11.x)
            elif hasattr(self.websocket, 'closed'):
                is_open = not self.websocket.closed
                logger.debug(f"WebSocket closed check: {self.websocket.closed} -> {is_open}")
                return is_open
                
            # Method 3: Check using close_code (fallback)
            elif hasattr(self.websocket, 'close_code'):
                is_open = self.websocket.close_code is None
                logger.debug(f"WebSocket close_code check: {self.websocket.close_code} -> {is_open}")
                return is_open
                
            # Method 4: Try to access protocol state directly
            elif hasattr(self.websocket, 'protocol') and hasattr(self.websocket.protocol, 'state'):
                try:
                    from websockets.protocol import State
                    is_open = self.websocket.protocol.state == State.OPEN
                    logger.debug(f"WebSocket protocol state check: {self.websocket.protocol.state.name} -> {is_open}")
                    return is_open
                except (ImportError, AttributeError) as e:
                    logger.debug(f"Protocol state check failed: {e}")
            
            # Method 5: Test actual connection by attempting to send ping
            # This is more reliable but slower - only use as last resort
            try:
                # Try to access websocket internal state
                if hasattr(self.websocket, '_connection_lost'):
                    is_open = not self.websocket._connection_lost
                    logger.debug(f"WebSocket connection_lost check: {self.websocket._connection_lost} -> {is_open}")
                    return is_open
            except AttributeError:
                pass
                
        except Exception as e:
            logger.warning(f"WebSocket state check error: {e}")
            return False
            
        # Final fallback: assume open if websocket exists but can't determine state
        # This is conservative - if we can't determine state, assume it's open
        # and let actual operations fail gracefully
        logger.debug("WebSocket state unknown - assuming open for graceful degradation")
        return True

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return (
            self.connection_state == ConnectionState.CONNECTED and
            self.websocket is not None and
            self._is_websocket_open()
        )
    
    @property
    def is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open"""
        if not self.circuit_breaker_open:
            return False
        
        # Check if timeout period has passed
        if time.time() - self.circuit_breaker_last_failure > self.circuit_breaker_timeout:
            self.circuit_breaker_open = False
            self.circuit_breaker_failures = 0
            logger.info("Circuit breaker reset - attempting reconnection")
            return False
        
        return True
    
    async def connect(self) -> bool:
        """Establish WebSocket connection with enhanced error handling"""
        if self.is_connected:
            return True
        
        if self.is_circuit_breaker_open:
            logger.warning("Circuit breaker is open - connection blocked")
            return False
        
        async with self.connection_lock:
            if self.is_connected:  # Double check
                return True
            
            self.connection_state = ConnectionState.CONNECTING
            self.stats.connection_attempts += 1
            
            try:
                logger.info(f"Connecting to MCP server at {self.ws_url}")
                
                # Create WebSocket connection with timeout
                self.websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.ws_url,
                        ping_interval=self.heartbeat_interval,
                        ping_timeout=self.ping_timeout,
                        close_timeout=10,
                        max_size=10**7,
                        compression=None  # Disable compression for better performance
                    ),
                    timeout=self.connection_timeout
                )
                
                self.connection_state = ConnectionState.CONNECTED
                self.stats.successful_connections += 1
                self.stats.last_successful_connection = datetime.now()
                self.connection_start_time = time.time()
                
                # Reset circuit breaker
                self.circuit_breaker_failures = 0
                self.circuit_breaker_open = False
                
                # Start background tasks
                await self._start_background_tasks()
                
                # Small delay to ensure WebSocket is fully established
                await asyncio.sleep(0.1)
                
                # Send connection initialization
                await self._send_connection_init()
                
                # Notify connection event handlers
                await self._notify_connection_event("connected")
                
                logger.info("WebSocket connection established successfully")
                return True
                
            except asyncio.TimeoutError:
                error_msg = f"Connection timeout after {self.connection_timeout}s"
                logger.error(error_msg)
                self.stats.last_connection_error = error_msg
                await self._handle_connection_failure()
                return False
                
            except InvalidStatusCode as e:
                error_msg = f"WebSocket handshake failed: {e}"
                logger.error(error_msg)
                self.stats.last_connection_error = error_msg
                await self._handle_connection_failure()
                return False
                
            except Exception as e:
                error_msg = f"Connection failed: {e}"
                logger.error(error_msg)
                self.stats.last_connection_error = error_msg
                await self._handle_connection_failure()
                return False
            finally:
                if self.connection_state == ConnectionState.CONNECTING:
                    self.connection_state = ConnectionState.DISCONNECTED
    
    async def disconnect(self):
        """Gracefully disconnect from MCP server"""
        async with self.connection_lock:
            logger.info("Disconnecting from MCP server")
            
            self.connection_state = ConnectionState.DISCONNECTED
            
            # Stop background tasks
            await self._stop_background_tasks()
            
            # Close WebSocket connection
            if self.websocket:
                try:
                    # Only close if websocket is still open
                    if self._is_websocket_open():
                        await self.websocket.close()
                except Exception as e:
                    logger.warning(f"Error closing WebSocket: {e}")
            
            self.websocket = None
            
            # Update stats
            if self.connection_start_time:
                self.stats.uptime_seconds += time.time() - self.connection_start_time
                self.connection_start_time = None
            
            # Reject all pending requests
            for request_id, future in self.pending_requests.items():
                if not future.done():
                    future.set_exception(ConnectionError("Connection closed"))
            self.pending_requests.clear()
            
            # Notify connection event handlers
            await self._notify_connection_event("disconnected")
            
            logger.info("Disconnected from MCP server")
    
    async def _handle_connection_failure(self):
        """Handle connection failure with circuit breaker logic"""
        self.stats.failed_connections += 1
        self.connection_state = ConnectionState.FAILED
        
        # Update circuit breaker
        self.circuit_breaker_failures += 1
        self.circuit_breaker_last_failure = time.time()
        
        if self.circuit_breaker_failures >= self.circuit_breaker_threshold:
            self.circuit_breaker_open = True
            logger.warning(
                f"Circuit breaker opened after {self.circuit_breaker_failures} failures. "
                f"Will retry after {self.circuit_breaker_timeout}s"
            )
        
        # Notify connection event handlers
        await self._notify_connection_event("failed")
        
        # Start reconnection if not at max attempts
        if (self.max_reconnect_attempts < 0 or 
            self.stats.reconnection_attempts < self.max_reconnect_attempts):
            asyncio.create_task(self._reconnect())
    
    async def _reconnect(self):
        """Attempt to reconnect with exponential backoff"""
        if self.connection_state == ConnectionState.RECONNECTING:
            return  # Already reconnecting
        
        self.connection_state = ConnectionState.RECONNECTING
        self.stats.reconnection_attempts += 1
        
        # Calculate backoff delay
        backoff_delay = min(
            self.initial_reconnect_delay * (2 ** (self.stats.reconnection_attempts - 1)),
            self.max_reconnect_delay
        )
        
        logger.info(
            f"Attempting reconnection {self.stats.reconnection_attempts} "
            f"in {backoff_delay:.1f}s"
        )
        
        await asyncio.sleep(backoff_delay)
        
        success = await self.connect()
        if success:
            self.stats.reconnection_attempts = 0  # Reset on success
            logger.info("Reconnection successful")
        else:
            logger.warning("Reconnection failed")
    
    async def _start_background_tasks(self):
        """Start background maintenance tasks"""
        self.message_handler_task = asyncio.create_task(self._message_handler())
        self.heartbeat_task = asyncio.create_task(self._heartbeat_handler())
        self.health_monitor_task = asyncio.create_task(self._health_monitor())
    
    async def _stop_background_tasks(self):
        """Stop background tasks"""
        tasks = [
            self.message_handler_task,
            self.heartbeat_task,
            self.health_monitor_task,
            self.reconnection_task
        ]
        
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    
    async def _send_connection_init(self):
        """Send connection initialization message"""
        init_message = {
            "type": MessageType.EVENT.value,
            "event_name": "agent_connected",
            "payload": {
                "agent_id": self.agent_id,
                "agent_type": "nlp-agent",
                "version": "2.1.0",
                "capabilities": [
                    "natural_language_processing",
                    "intent_extraction", 
                    "entity_recognition",
                    "query_classification",
                    "context_building",
                    "request_batching",
                    "real_time_events"
                ],
                "connection_time": datetime.now().isoformat(),
                "client_features": {
                    "circuit_breaker": True,
                    "auto_reconnect": True,
                    "health_monitoring": True,
                    "performance_tracking": True
                }
            }
        }
        await self._send_raw_message(init_message)
    
    async def _send_raw_message(self, message: Dict[str, Any]):
        """Send raw message via WebSocket with improved error handling"""
        if not self.websocket:
            raise ConnectionError("WebSocket not connected")
        
        if not self._is_websocket_open():
            raise ConnectionError("WebSocket connection is not open")
        
        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            # Mark connection as failed if send fails
            if self.connection_state == ConnectionState.CONNECTED:
                self.connection_state = ConnectionState.FAILED
            raise
    
    async def _message_handler(self):
        """Handle incoming WebSocket messages with error recovery"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse WebSocket message: {e}")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
                    
        except ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
            await self._handle_disconnect()
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            await self._handle_disconnect()
        except Exception as e:
            logger.error(f"Unexpected error in message handler: {e}")
            await self._handle_disconnect()
    
    async def _handle_disconnect(self):
        """Handle unexpected disconnection"""
        if self.connection_state == ConnectionState.CONNECTED:
            logger.warning("Unexpected disconnection detected")
            await self._notify_connection_event("disconnected")
            self.connection_state = ConnectionState.DISCONNECTED
            
            # Start reconnection
            asyncio.create_task(self._reconnect())
    
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
            logger.debug(f"Unknown message type: {message_type}")
    
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
        
        # Call registered event handlers
        if event_name in self.event_handlers:
            try:
                handler = self.event_handlers[event_name]
                if asyncio.iscoroutinefunction(handler):
                    await handler(payload)
                else:
                    handler(payload)
            except Exception as e:
                logger.error(f"Error in event handler for {event_name}: {e}")
        
        # Handle built-in events
        if event_name == "connection_acknowledged":
            logger.info("Connection acknowledged by server")
        elif event_name == "schema_update":
            logger.info("Schema update received from server")
        elif event_name == "server_heartbeat":
            logger.debug("Server heartbeat received")
            await self._handle_heartbeat_event(data)
    
    async def _handle_error(self, data: Dict[str, Any]):
        """Handle error message"""
        request_id = data.get("request_id")
        error_message = data.get("error", "Unknown error")
        error_type = data.get("error_type", "unknown")
        
        if request_id in self.pending_requests:
            future = self.pending_requests.pop(request_id)
            if not future.done():
                future.set_exception(Exception(f"{error_type}: {error_message}"))
        
        # Update error stats
        self.stats.failed_requests += 1
        
        logger.error(f"Server error ({error_type}): {error_message}")
    
    async def _handle_pong(self, data: Dict[str, Any]):
        """Handle pong message"""
        logger.debug("Received pong from server")
    
    async def _handle_heartbeat_event(self, data: Dict[str, Any]):
        """Handle heartbeat event from server"""
        logger.debug("Received heartbeat event from server")
        
        # Send heartbeat response as event
        heartbeat_response = {
            "type": MessageType.EVENT.value,
            "event_name": "heartbeat_response",
            "payload": {
                "timestamp": datetime.now().isoformat(),
                "agent_id": self.agent_id,
                "stats": self.get_connection_stats()
            }
        }
        await self._send_raw_message(heartbeat_response)
    
    async def _heartbeat_handler(self):
        """Send periodic heartbeat to server"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                # Check connection state more robustly
                if (self.connection_state != ConnectionState.CONNECTED or 
                    not self._is_websocket_open()):
                    logger.debug("Connection not available for heartbeat")
                    break
                
                ping_message = {
                    "type": MessageType.PING.value,
                    "timestamp": datetime.now().isoformat(),
                    "agent_id": self.agent_id
                }
                await self._send_raw_message(ping_message)
                
            except asyncio.CancelledError:
                logger.debug("Heartbeat handler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in heartbeat handler: {e}")
                break
    
    async def _health_monitor(self):
        """Monitor connection health and performance"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                # Check if we should continue monitoring
                if (self.connection_state != ConnectionState.CONNECTED or 
                    not self._is_websocket_open()):
                    logger.debug("Connection not available for health monitoring")
                    break
                
                # Perform health check with error tolerance
                try:
                    health_ok = await self._perform_health_check()
                    
                    if not health_ok:
                        logger.warning("Health check failed - connection may be stale, will retry on next cycle")
                        # Don't immediately trigger reconnection - wait for next cycle
                        # This prevents unnecessary reconnections during heavy processing
                        continue
                except Exception as health_error:
                    logger.warning(f"Health check error (non-critical): {health_error}")
                    # Continue monitoring - health check failures shouldn't break the connection
                    continue
                
                # Update performance metrics
                self._update_performance_metrics()
                
            except asyncio.CancelledError:
                logger.debug("Health monitor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                # Continue monitoring unless it's a critical error
                if "Connection" in str(e):
                    break
    
    async def _perform_health_check(self) -> bool:
        """Perform lightweight connection health check"""
        try:
            # Use a simple approach - just check if the WebSocket is open and responsive
            # This avoids queuing behind other requests and is much faster
            if not self._is_websocket_open():
                return False
            
            # Try a simple ping instead of a full health check request
            # This is much lighter weight and won't interfere with KIMI API calls
            try:
                ping_message = {
                    "type": "ping",  
                    "timestamp": datetime.now().isoformat(),
                    "agent_id": self.agent_id
                }
                await asyncio.wait_for(
                    self._send_raw_message(ping_message),
                    timeout=10.0  # Short timeout for simple ping
                )
                return True
            except asyncio.TimeoutError:
                logger.debug("Health check ping timeout - connection may be busy")
                return True  # Assume healthy if just busy (not necessarily failed)
            except Exception:
                return False
                
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False
    
    def _update_performance_metrics(self):
        """Update performance tracking metrics"""
        # Clean old request times (keep last 100)
        if len(self.last_request_times) > 100:
            self.last_request_times = self.last_request_times[-100:]
        
        # Calculate average response time
        if self.last_request_times:
            self.stats.average_response_time = sum(self.last_request_times) / len(self.last_request_times)
        
        # Update uptime
        if self.connection_start_time:
            uptime = time.time() - self.connection_start_time
            logger.debug(f"Connection uptime: {uptime:.1f}s")
    
    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        use_batching: bool = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """Send request with enhanced error handling and retry logic"""
        if not self.is_connected:
            if not await self.connect():
                raise ConnectionError("Cannot establish connection to MCP server")
        
        if self.is_circuit_breaker_open:
            raise ConnectionError("Circuit breaker is open - requests blocked")
        
        # Use default timeout if not specified
        timeout = timeout or self.request_timeout
        
        # Acquire semaphore for concurrent request limiting
        async with self.request_semaphore:
            try:
                # Use batching if enabled and not explicitly disabled
                if (self.enable_request_batching and 
                    (use_batching is None or use_batching) and
                    method != "health_check"):  # Don't batch health checks
                    return await self._send_batched_request(method, params, timeout)
                else:
                    return await self._send_single_request(method, params, timeout)
                    
            except Exception as e:
                self.stats.failed_requests += 1
                
                # Retry logic for transient errors
                if (retry_count < 2 and 
                    isinstance(e, (asyncio.TimeoutError, ConnectionError)) and
                    self.is_connected):
                    
                    logger.warning(f"Request failed, retrying ({retry_count + 1}/2): {e}")
                    await asyncio.sleep(0.5 * (retry_count + 1))  # Progressive delay
                    return await self.send_request(
                        method, params, timeout, use_batching, retry_count + 1
                    )
                
                raise
    
    async def _send_single_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]],
        timeout: float
    ) -> Dict[str, Any]:
        """Send single request directly"""
        start_time = time.time()
        
        request_id = f"req_{self.agent_id}_{self.request_id_counter}"
        self.request_id_counter += 1
        
        message = {
            "type": MessageType.REQUEST.value,
            "request_id": request_id,
            "method": method,
            "params": params or {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        try:
            # Send request
            await self._send_raw_message(message)
            self.stats.total_requests += 1
            
            # Wait for response with timeout
            result = await asyncio.wait_for(future, timeout=timeout)
            
            # Update performance tracking
            response_time = time.time() - start_time
            self.last_request_times.append(response_time)
            
            return result
            
        except asyncio.TimeoutError:
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            raise asyncio.TimeoutError(f"Request {request_id} timed out after {timeout}s")
        except Exception as e:
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            raise
    
    async def _send_batched_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]],
        timeout: float
    ) -> Dict[str, Any]:
        """Send request via batching mechanism"""
        request = {
            "method": method,
            "params": params or {},
            "timestamp": datetime.now().isoformat()
        }
        
        future = asyncio.Future()
        
        async with self.batch_lock:
            self.batch_requests.append({
                "request": request,
                "future": future,
                "timeout": timeout,
                "start_time": time.time()
            })
            
            # Process batch if size threshold reached
            if len(self.batch_requests) >= self.batch_size:
                if self.batch_timer:
                    self.batch_timer.cancel()
                asyncio.create_task(self._process_batch())
            elif len(self.batch_requests) == 1:
                # Start timeout timer for first request
                self.batch_timer = asyncio.create_task(self._batch_timeout_handler())
        
        return await future
    
    async def _batch_timeout_handler(self):
        """Handle batch timeout"""
        try:
            await asyncio.sleep(self.batch_timeout)
            await self._process_batch()
        except asyncio.CancelledError:
            pass
    
    async def _process_batch(self):
        """Process accumulated batch of requests"""
        async with self.batch_lock:
            if not self.batch_requests:
                return
            
            batch = self.batch_requests.copy()
            self.batch_requests.clear()
            self.batch_timer = None
        
        if len(batch) == 1:
            # Single request - send directly
            item = batch[0]
            try:
                result = await self._send_single_request(
                    item["request"]["method"],
                    item["request"]["params"],
                    item["timeout"]
                )
                item["future"].set_result(result)
            except Exception as e:
                item["future"].set_exception(e)
        else:
            # Batch request
            request_id = f"batch_{self.agent_id}_{self.request_id_counter}"
            self.request_id_counter += 1
            
            message = {
                "type": MessageType.BATCH_REQUEST.value,
                "request_id": request_id,
                "requests": [item["request"] for item in batch],
                "timestamp": datetime.now().isoformat()
            }
            
            # Create future for batch response
            batch_future = asyncio.Future()
            self.pending_requests[request_id] = batch_future
            
            try:
                # Send batch request
                await self._send_raw_message(message)
                self.stats.total_requests += len(batch)
                
                # Wait for batch response
                max_timeout = max(item["timeout"] for item in batch)
                results = await asyncio.wait_for(batch_future, timeout=max_timeout)
                
                # Resolve individual futures
                for item, result in zip(batch, results):
                    if isinstance(result, dict) and not result.get("success", True):
                        error_msg = result.get("error", "Unknown error")
                        item["future"].set_exception(Exception(error_msg))
                    else:
                        item["future"].set_result(result)
                        
                    # Update performance tracking
                    response_time = time.time() - item["start_time"]
                    self.last_request_times.append(response_time)
                
            except Exception as e:
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]
                
                # Resolve all futures with error
                for item in batch:
                    item["future"].set_exception(e)
    
    def register_event_handler(self, event_name: str, handler: Callable):
        """Register event handler for specific event type"""
        self.event_handlers[event_name] = handler
        logger.info(f"Registered event handler for {event_name}")
    
    def register_connection_event_handler(self, handler: Callable):
        """Register handler for connection events (connected, disconnected, failed)"""
        self.connection_event_handlers.append(handler)
        logger.info("Registered connection event handler")
    
    async def _notify_connection_event(self, event_type: str):
        """Notify connection event handlers"""
        for handler in self.connection_event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_type, self.get_connection_stats())
                else:
                    handler(event_type, self.get_connection_stats())
            except Exception as e:
                logger.error(f"Error in connection event handler: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get comprehensive connection statistics"""
        current_uptime = 0.0
        if self.connection_start_time:
            current_uptime = time.time() - self.connection_start_time
        
        return {
            "connection_state": self.connection_state.value,
            "is_connected": self.is_connected,
            "agent_id": self.agent_id,
            "ws_url": self.ws_url,
            "stats": {
                "connection_attempts": self.stats.connection_attempts,
                "successful_connections": self.stats.successful_connections,
                "failed_connections": self.stats.failed_connections,
                "reconnection_attempts": self.stats.reconnection_attempts,
                "total_requests": self.stats.total_requests,
                "failed_requests": self.stats.failed_requests,
                "success_rate": (
                    (self.stats.total_requests - self.stats.failed_requests) 
                    / max(self.stats.total_requests, 1) * 100
                ),
                "average_response_time_ms": self.stats.average_response_time * 1000,
                "current_uptime_seconds": current_uptime + self.stats.uptime_seconds,
                "last_successful_connection": (
                    self.stats.last_successful_connection.isoformat()
                    if self.stats.last_successful_connection else None
                ),
                "last_connection_error": self.stats.last_connection_error
            },
            "circuit_breaker": {
                "open": self.circuit_breaker_open,
                "failures": self.circuit_breaker_failures,
                "threshold": self.circuit_breaker_threshold
            },
            "performance": {
                "pending_requests": len(self.pending_requests),
                "max_concurrent_requests": self.max_concurrent_requests,
                "recent_response_times": self.last_request_times[-10:] if self.last_request_times else []
            }
        }
