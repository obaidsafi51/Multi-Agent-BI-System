"""
WebSocket Agent Connection Pool Manager

Manages persistent WebSocket connections to all agents with connection pooling,
failover, and real-time communication capabilities.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import websockets
import websockets.exceptions
from orchestration import CircuitBreaker, retry_with_backoff, RetryConfig

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Agent types"""
    NLP = "nlp"
    DATA = "data"
    VIZ = "viz"


class ConnectionState(Enum):
    """WebSocket connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class WebSocketConnection:
    """WebSocket connection wrapper"""
    websocket: Optional[websockets.WebSocketServerProtocol] = None
    state: ConnectionState = ConnectionState.DISCONNECTED
    last_heartbeat: Optional[float] = None
    connection_time: Optional[float] = None
    reconnect_count: int = 0
    message_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    pending_responses: Dict[str, asyncio.Future] = field(default_factory=dict)
    recv_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


@dataclass 
class AgentConfig:
    """Agent configuration"""
    name: str
    agent_type: AgentType
    http_url: str
    websocket_url: str
    enabled: bool = True
    use_websocket: bool = True  # Feature flag for WebSocket vs HTTP
    heartbeat_interval: float = 30.0
    connection_timeout: float = 10.0
    max_reconnect_attempts: int = 5
    reconnect_delay: float = 2.0
    circuit_breaker_config: Optional[Dict[str, Any]] = None


class WebSocketAgentManager:
    """
    Manages WebSocket connections to all agents with connection pooling,
    failover, and real-time communication.
    """
    
    def __init__(self):
        self.agents: Dict[AgentType, AgentConfig] = {}
        self.connections: Dict[AgentType, WebSocketConnection] = {}
        self.circuit_breakers: Dict[AgentType, CircuitBreaker] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.heartbeat_tasks: Dict[AgentType, asyncio.Task] = {}
        self.reconnect_tasks: Dict[AgentType, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()
        
        # Initialize agent configurations
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize agent configurations"""
        import os
        
        # NLP Agent
        self.agents[AgentType.NLP] = AgentConfig(
            name="nlp-agent",
            agent_type=AgentType.NLP,
            http_url=os.getenv("NLP_AGENT_URL", "http://nlp-agent:8001"),
            websocket_url=os.getenv("NLP_AGENT_WS_URL", "ws://nlp-agent:8001/ws"),
            use_websocket=os.getenv("NLP_AGENT_USE_WS", "true").lower() == "true",
            circuit_breaker_config={
                "failure_threshold": 3,
                "recovery_timeout": 30.0,
                "name": "nlp-agent-ws"
            }
        )
        
        # Data Agent
        self.agents[AgentType.DATA] = AgentConfig(
            name="data-agent", 
            agent_type=AgentType.DATA,
            http_url=os.getenv("DATA_AGENT_URL", "http://data-agent:8002"),
            websocket_url=os.getenv("DATA_AGENT_WS_URL", "ws://data-agent:8012"),
            use_websocket=os.getenv("DATA_AGENT_USE_WS", "true").lower() == "true",
            circuit_breaker_config={
                "failure_threshold": 3,
                "recovery_timeout": 30.0,
                "name": "data-agent-ws"
            }
        )
        
        # Viz Agent
        self.agents[AgentType.VIZ] = AgentConfig(
            name="viz-agent",
            agent_type=AgentType.VIZ,
            http_url=os.getenv("VIZ_AGENT_URL", "http://viz-agent:8003"),
            websocket_url=os.getenv("VIZ_AGENT_WS_URL", "ws://viz-agent:8013"),
            use_websocket=os.getenv("VIZ_AGENT_USE_WS", "true").lower() == "true",
            circuit_breaker_config={
                "failure_threshold": 3,
                "recovery_timeout": 30.0,
                "name": "viz-agent-ws"
            }
        )        # Initialize circuit breakers
        for agent_type, config in self.agents.items():
            if config.circuit_breaker_config:
                self.circuit_breakers[agent_type] = CircuitBreaker(**config.circuit_breaker_config)
            
            # Initialize connections
            self.connections[agent_type] = WebSocketConnection()
        
        # Task to handle incoming messages
        self.message_router_tasks: Dict[AgentType, asyncio.Task] = {}
    
    async def start(self):
        """Start the WebSocket agent manager with delayed connection attempts"""
        logger.info("Starting WebSocket Agent Manager")
        
        # Don't attempt connections during startup - let agents start first
        logger.info("WebSocket Agent Manager initialized - connections will be established when needed")
        
        # Start cleanup and maintenance tasks
        asyncio.create_task(self._maintenance_loop())
        
        logger.info(f"WebSocket Agent Manager started with {len([a for a in self.agents.values() if a.use_websocket])} WebSocket agents configured")
    
    async def _maintenance_loop(self):
        """Background maintenance task to establish and maintain connections"""
        await asyncio.sleep(10)  # Wait for agents to start up
        
        while not self._shutdown_event.is_set():
            try:
                # Try to establish connections for WebSocket-enabled agents
                for agent_type, config in self.agents.items():
                    if config.enabled and config.use_websocket:
                        connection = self.connections[agent_type]
                        if connection.state == ConnectionState.DISCONNECTED:
                            await self._start_agent_connection(agent_type)
                
                # Wait before next maintenance cycle
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in maintenance loop: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Stop the WebSocket agent manager"""
        logger.info("Stopping WebSocket Agent Manager")
        self._shutdown_event.set()
        
        # Cancel all tasks
        all_tasks = (list(self.heartbeat_tasks.values()) + 
                    list(self.reconnect_tasks.values()) + 
                    list(self.message_router_tasks.values()))
        
        for task in all_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close all connections
        for agent_type, connection in self.connections.items():
            if connection.websocket:
                try:
                    await connection.websocket.close()
                except:
                    pass
                connection.state = ConnectionState.DISCONNECTED
        
        logger.info("WebSocket Agent Manager stopped")
    
    async def _start_agent_connection(self, agent_type: AgentType):
        """Start WebSocket connection for an agent"""
        config = self.agents[agent_type]
        connection = self.connections[agent_type]
        
        logger.info(f"Starting WebSocket connection to {config.name}")
        
        # Start connection task
        connection_task = asyncio.create_task(
            self._maintain_connection(agent_type)
        )
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(agent_type)
        )
        
        self.reconnect_tasks[agent_type] = connection_task
        self.heartbeat_tasks[agent_type] = heartbeat_task
    
    async def _maintain_connection(self, agent_type: AgentType):
        """Maintain WebSocket connection with reconnection logic"""
        config = self.agents[agent_type]
        connection = self.connections[agent_type]
        
        while not self._shutdown_event.is_set():
            try:
                if connection.state == ConnectionState.DISCONNECTED:
                    await self._connect_agent(agent_type)
                
                if connection.websocket and connection.state == ConnectionState.CONNECTED:
                    # Start message router task if not already running
                    if agent_type not in self.message_router_tasks or self.message_router_tasks[agent_type].done():
                        self.message_router_tasks[agent_type] = asyncio.create_task(
                            self._message_router(agent_type)
                        )
                    
                    # Wait for connection to be lost
                    try:
                        await self.message_router_tasks[agent_type]
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Message router failed for {config.name}: {e}")
                        connection.state = ConnectionState.FAILED
                        connection.last_error = str(e)
                        connection.error_count += 1
                
                # Wait before reconnecting
                if connection.state in [ConnectionState.DISCONNECTED, ConnectionState.FAILED]:
                    await asyncio.sleep(config.reconnect_delay)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in connection maintenance for {config.name}: {e}")
                await asyncio.sleep(config.reconnect_delay)
    
    async def _message_router(self, agent_type: AgentType):
        """Central message router that handles all incoming WebSocket messages"""
        config = self.agents[agent_type]
        connection = self.connections[agent_type]
        
        try:
            async for message in connection.websocket:
                if isinstance(message, str):
                    connection.message_count += 1
                    try:
                        data = json.loads(message)
                        message_id = data.get("response_to")
                        msg_type = data.get("type", "unknown")
                        
                        # Only complete futures for actual response messages, not progress updates
                        if (message_id and message_id in connection.pending_responses and 
                            msg_type not in ["progress_update", "heartbeat", "heartbeat_response"]):
                            future = connection.pending_responses.pop(message_id)
                            if not future.done():
                                future.set_result(data)
                                logger.debug(f"Completed future for message_id {message_id} with type {msg_type}")
                        else:
                            # Handle other message types (including progress updates)
                            await self._handle_message(agent_type, message)
                            
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON message from {agent_type.value}: {message}")
                    except Exception as e:
                        logger.error(f"Error processing message from {agent_type.value}: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"WebSocket connection to {config.name} closed")
            connection.state = ConnectionState.DISCONNECTED
        except Exception as e:
            logger.error(f"Error in message router for {config.name}: {e}")
            connection.state = ConnectionState.FAILED
            connection.last_error = str(e)
            connection.error_count += 1
        finally:
            # Cancel any pending responses
            for future in connection.pending_responses.values():
                if not future.done():
                    future.cancel()
            connection.pending_responses.clear()
    
    async def _connect_agent(self, agent_type: AgentType):
        """Connect to agent WebSocket with better error handling"""
        config = self.agents[agent_type]
        connection = self.connections[agent_type]
        
        if connection.reconnect_count >= config.max_reconnect_attempts:
            logger.warning(f"Max reconnect attempts ({config.max_reconnect_attempts}) reached for {config.name}")
            connection.state = ConnectionState.FAILED
            return
        
        try:
            connection.state = ConnectionState.CONNECTING
            logger.info(f"Attempting connection to {config.name} at {config.websocket_url} (attempt {connection.reconnect_count + 1})")
            
            # Connect with timeout
            websocket = await asyncio.wait_for(
                websockets.connect(
                    config.websocket_url,
                    ping_interval=config.heartbeat_interval,
                    ping_timeout=config.connection_timeout,
                    close_timeout=5.0
                ),
                timeout=config.connection_timeout
            )
            
            connection.websocket = websocket
            connection.state = ConnectionState.CONNECTED
            connection.connection_time = time.time()
            connection.reconnect_count = 0  # Reset on successful connection
            
            logger.info(f"Successfully connected to {config.name}")
            
        except (ConnectionRefusedError, OSError) as e:
            logger.debug(f"Connection refused to {config.name} - agent may not be ready yet: {e}")
            connection.state = ConnectionState.FAILED
            connection.last_error = f"Connection refused: {str(e)}"
            connection.reconnect_count += 1
            
        except asyncio.TimeoutError:
            logger.debug(f"Connection timeout for {config.name} - retrying later")
            connection.state = ConnectionState.FAILED
            connection.last_error = "Connection timeout"
            connection.reconnect_count += 1
            
        except Exception as e:
            logger.warning(f"Failed to connect to {config.name}: {e}")
            connection.state = ConnectionState.FAILED
            connection.last_error = str(e)
            connection.reconnect_count += 1
    
    async def _heartbeat_loop(self, agent_type: AgentType):
        """Send periodic heartbeat to agent"""
        config = self.agents[agent_type]
        connection = self.connections[agent_type]
        
        while not self._shutdown_event.is_set():
            try:
                if (connection.state == ConnectionState.CONNECTED and 
                    connection.websocket):
                    
                    # Send heartbeat
                    heartbeat_msg = {
                        "type": "heartbeat",
                        "timestamp": time.time(),
                        "from": "backend"
                    }
                    
                    await connection.websocket.send(json.dumps(heartbeat_msg))
                    connection.last_heartbeat = time.time()
                
                await asyncio.sleep(config.heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Heartbeat failed for {config.name}: {e}")
                await asyncio.sleep(5)
    
    async def _handle_message(self, agent_type: AgentType, message: str):
        """Handle incoming WebSocket message from agent"""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "unknown")
            
            # Handle heartbeat messages (both heartbeat and heartbeat_response)
            if msg_type in ["heartbeat", "heartbeat_response"]:
                connection = self.connections[agent_type]
                connection.last_heartbeat = time.time()
                logger.debug(f"Received {msg_type} from {agent_type.value}")
                
                # If it's a heartbeat, respond with heartbeat_response
                if msg_type == "heartbeat":
                    response = {
                        "type": "heartbeat_response",
                        "timestamp": time.time(),
                        "correlation_id": data.get("correlation_id")
                    }
                    await connection.websocket.send(json.dumps(response))
                return
            
            # Handle connection established
            if msg_type == "connection_established":
                logger.info(f"Connection established with {agent_type.value}")
                return
            
            # Handle progress updates
            if msg_type == "progress_update":
                status = data.get("status", "unknown")
                progress = data.get("progress", 0)
                logger.debug(f"Progress from {agent_type.value}: {status} ({progress}%)")
                return
            
            # Handle error messages
            if msg_type == "error":
                error_msg = data.get("error", {})
                if isinstance(error_msg, dict):
                    error_text = error_msg.get("message", "Unknown error")
                else:
                    error_text = str(error_msg)
                logger.error(f"Error from {agent_type.value}: {error_text}")
                return
            
            # Handle other message types
            handler = self.message_handlers.get(msg_type)
            if handler:
                await handler(agent_type, data)
            else:
                logger.debug(f"No handler for message type '{msg_type}' from {agent_type.value}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON message from {agent_type.value}: {message}")
        except Exception as e:
            logger.error(f"Error handling message from {agent_type.value}: {e}")
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """Register a message handler for specific message type"""
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
    
    async def send_message(
        self, 
        agent_type: AgentType, 
        message: Dict[str, Any], 
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Send message to agent via WebSocket or HTTP fallback
        
        Args:
            agent_type: Target agent type
            message: Message to send
            timeout: Request timeout
            
        Returns:
            Agent response
        """
        config = self.agents[agent_type]
        
        # Use WebSocket if enabled and connected
        if config.use_websocket and self.is_agent_connected(agent_type):
            return await self._send_websocket_message(agent_type, message, timeout)
        else:
            # Fallback to HTTP
            return await self._send_http_message(agent_type, message, timeout)
    
    async def _send_websocket_message(
        self, 
        agent_type: AgentType, 
        message: Dict[str, Any], 
        timeout: float
    ) -> Dict[str, Any]:
        """Send message via WebSocket"""
        connection = self.connections[agent_type]
        circuit_breaker = self.circuit_breakers.get(agent_type)
        
        async def _send():
            if not connection.websocket or connection.state != ConnectionState.CONNECTED:
                raise ConnectionError(f"WebSocket not connected to {agent_type.value}")
            
            # Add message ID for response correlation
            message_id = str(uuid.uuid4())
            message["message_id"] = message_id
            message["timestamp"] = time.time()
            
            # Create a future to wait for the response
            response_future = asyncio.Future()
            connection.pending_responses[message_id] = response_future
            
            try:
                # Send message
                await connection.websocket.send(json.dumps(message))
                
                # Wait for response
                response = await asyncio.wait_for(response_future, timeout=timeout)
                return response
                
            except asyncio.TimeoutError:
                # Clean up pending response
                connection.pending_responses.pop(message_id, None)
                raise TimeoutError(f"No response received from {agent_type.value} within {timeout}s")
            except Exception as e:
                # Clean up pending response
                connection.pending_responses.pop(message_id, None)
                raise e
        
        if circuit_breaker:
            return await circuit_breaker.call(_send)
        else:
            return await _send()
    
    async def _send_http_message(
        self, 
        agent_type: AgentType, 
        message: Dict[str, Any], 
        timeout: float
    ) -> Dict[str, Any]:
        """Send message via HTTP fallback"""
        config = self.agents[agent_type]
        
        # Import here to avoid circular imports
        import httpx
        
        # Determine the correct endpoint based on agent type
        if agent_type == AgentType.DATA:
            endpoint = "/execute"  # Data agent uses /execute endpoint
        elif agent_type == AgentType.VIZ:
            endpoint = "/visualize"  # VIZ agent uses /visualize endpoint
        else:
            endpoint = "/process"  # NLP agent uses /process endpoint
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.http_url}{endpoint}",
                json=message,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
    
    def is_agent_connected(self, agent_type: AgentType) -> bool:
        """Check if agent is connected via WebSocket"""
        connection = self.connections.get(agent_type)
        return (connection and 
                connection.state == ConnectionState.CONNECTED and 
                connection.websocket is not None)
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """Get connection statistics for all agents"""
        stats = {}
        
        for agent_type, connection in self.connections.items():
            config = self.agents[agent_type]
            circuit_breaker = self.circuit_breakers.get(agent_type)
            
            agent_stats = {
                "name": config.name,
                "enabled": config.enabled,
                "use_websocket": config.use_websocket,
                "state": connection.state.value,
                "connected": self.is_agent_connected(agent_type),
                "connection_time": connection.connection_time,
                "last_heartbeat": connection.last_heartbeat,
                "reconnect_count": connection.reconnect_count,
                "message_count": connection.message_count,
                "error_count": connection.error_count,
                "last_error": connection.last_error
            }
            
            if circuit_breaker:
                agent_stats["circuit_breaker"] = circuit_breaker.get_stats()
            
            stats[agent_type.value] = agent_stats
        
        return stats
    
    def enable_websocket_for_agent(self, agent_type: AgentType):
        """Enable WebSocket for specific agent (Phase 2 migration)"""
        config = self.agents[agent_type]
        if not config.use_websocket:
            config.use_websocket = True
            logger.info(f"Enabled WebSocket for {config.name}")
            
            # Start connection if not already started
            if agent_type not in self.reconnect_tasks:
                asyncio.create_task(self._start_agent_connection(agent_type))
    
    def disable_websocket_for_agent(self, agent_type: AgentType):
        """Disable WebSocket for specific agent (rollback)"""
        config = self.agents[agent_type]
        if config.use_websocket:
            config.use_websocket = False
            logger.info(f"Disabled WebSocket for {config.name}")
            
            # Stop connection
            connection = self.connections[agent_type]
            if connection.websocket:
                asyncio.create_task(connection.websocket.close())
                connection.state = ConnectionState.DISCONNECTED


# Global manager instance
websocket_agent_manager = WebSocketAgentManager()


@asynccontextmanager
async def get_agent_manager():
    """Context manager for WebSocket agent manager"""
    try:
        await websocket_agent_manager.start()
        yield websocket_agent_manager
    finally:
        await websocket_agent_manager.stop()
