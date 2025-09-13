"""
WebSocket server extension for TiDB MCP Server to support persistent connections
from multiple agents with intelligent request batching and real-time events.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from .mcp_tools import (
    discover_databases,
    discover_tables,
    get_table_schema,
    get_sample_data,
    execute_query,
    validate_query,
    get_server_stats
)
from .llm_tools import (
    generate_sql_tool,
    analyze_data_tool,
    generate_text_tool,
    explain_results_tool
)

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


class AgentConnection:
    """Represents a connected agent with metadata"""
    
    def __init__(self, websocket: WebSocket, agent_id: str, agent_type: str = "unknown"):
        self.websocket = websocket
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.connected_at = datetime.now()
        self.last_ping = time.time()
        self.request_count = 0
        self.total_latency = 0.0
        self.capabilities = []
        
    @property
    def avg_latency(self) -> float:
        return self.total_latency / self.request_count if self.request_count > 0 else 0.0
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message to agent"""
        try:
            if self.websocket.client_state == WebSocketState.CONNECTED:
                await self.websocket.send_text(json.dumps(message))
                return True
        except Exception as e:
            logger.error(f"Failed to send message to {self.agent_id}: {e}")
        return False
    
    def update_stats(self, latency: float):
        """Update connection statistics"""
        self.request_count += 1
        self.total_latency += latency
        self.last_ping = time.time()


class WebSocketMCPServerManager:
    """
    WebSocket server manager for handling multiple agent connections
    with intelligent routing, batching, and real-time event broadcasting.
    """
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.connected_agents: Dict[str, AgentConnection] = {}
        self.agent_types: Dict[str, Set[str]] = {}  # agent_type -> set of agent_ids
        
        # Request handling
        self.request_handlers = {}
        self.batch_processors = {}
        
        # Event broadcasting
        self.event_subscribers: Dict[str, Set[str]] = {}  # event_type -> set of agent_ids
        
        # Performance monitoring
        self.metrics = {
            "total_connections": 0,
            "active_connections": 0,
            "total_requests": 0,
            "batch_requests": 0,
            "events_broadcast": 0,
            "avg_response_time": 0.0
        }
        
        # Background tasks
        self.cleanup_task = None
        self.heartbeat_task = None
        
        self._setup_request_handlers()
        self._setup_websocket_routes()
        
        logger.info("WebSocket MCP Server Manager initialized")
    
    def _setup_websocket_routes(self):
        """Setup WebSocket routes"""
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.handle_agent_connection(websocket)
    
    def _setup_request_handlers(self):
        """Setup request handlers for different MCP tools"""
        
        # Database tools
        self.request_handlers.update({
            "discover_databases": self._handle_discover_databases,
            "discover_tables": self._handle_discover_tables,
            "get_table_schema": self._handle_get_table_schema,
            "get_sample_data": self._handle_get_sample_data,
            "execute_query": self._handle_execute_query,
            "execute_query_tool": self._handle_execute_query,
            "validate_query": self._handle_validate_query,
            "validate_query_tool": self._handle_validate_query,
            "get_server_stats": self._handle_get_server_stats,
            "build_schema_context": self._handle_build_schema_context
        })
        
        # LLM tools
        self.request_handlers.update({
            "llm_generate_sql_tool": self._handle_generate_sql,
            "llm_analyze_data_tool": self._handle_analyze_data,
            "llm_generate_text_tool": self._handle_generate_text,
            "llm_explain_results_tool": self._handle_explain_results,
            "generate_sql": self._handle_generate_sql,
            "analyze_data": self._handle_analyze_data
        })
        
        # Agent management
        self.request_handlers.update({
            "health_check": self._handle_health_check,
            "get_agent_stats": self._handle_get_agent_stats,
            "subscribe_events": self._handle_subscribe_events
        })
    
    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("WebSocket background tasks started")
    
    async def stop_background_tasks(self):
        """Stop background tasks"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        logger.info("WebSocket background tasks stopped")
    
    async def handle_agent_connection(self, websocket: WebSocket):
        """Handle new agent WebSocket connection"""
        await websocket.accept()
        
        agent_id = None
        agent_connection = None
        
        try:
            # Wait for initial connection message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Extract agent information
            if message.get("type") == "event" and message.get("event_name") == "agent_connected":
                payload = message.get("payload", {})
                agent_id = payload.get("agent_id", f"agent_{uuid.uuid4().hex[:8]}")
                agent_type = payload.get("agent_type", "unknown")
                capabilities = payload.get("capabilities", [])
                
                # Create agent connection
                agent_connection = AgentConnection(websocket, agent_id, agent_type)
                agent_connection.capabilities = capabilities
                
                # Register agent
                self.connected_agents[agent_id] = agent_connection
                
                if agent_type not in self.agent_types:
                    self.agent_types[agent_type] = set()
                self.agent_types[agent_type].add(agent_id)
                
                self.metrics["total_connections"] += 1
                self.metrics["active_connections"] = len(self.connected_agents)
                
                logger.info(f"Agent connected: {agent_id} ({agent_type}) with capabilities: {capabilities}")
                
                # Send connection acknowledgment
                ack_message = {
                    "type": "event",
                    "event_name": "connection_acknowledged",
                    "payload": {
                        "agent_id": agent_id,
                        "server_capabilities": [
                            "database_operations",
                            "llm_tools",
                            "real_time_events",
                            "request_batching"
                        ],
                        "connected_at": agent_connection.connected_at.isoformat()
                    }
                }
                await agent_connection.send_message(ack_message)
            
            # Handle subsequent messages
            async for message_text in websocket.iter_text():
                try:
                    message = json.loads(message_text)
                    await self._process_agent_message(agent_id, message)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from {agent_id}: {e}")
                    await self._send_error(agent_id, "invalid_json", str(e))
                except Exception as e:
                    logger.error(f"Error processing message from {agent_id}: {e}")
                    await self._send_error(agent_id, "processing_error", str(e))
                    
        except WebSocketDisconnect:
            logger.info(f"Agent disconnected: {agent_id}")
        except Exception as e:
            logger.error(f"WebSocket error for {agent_id}: {e}")
        finally:
            # Cleanup agent connection
            if agent_id and agent_id in self.connected_agents:
                agent_connection = self.connected_agents[agent_id]
                del self.connected_agents[agent_id]
                
                if agent_connection.agent_type in self.agent_types:
                    self.agent_types[agent_connection.agent_type].discard(agent_id)
                    if not self.agent_types[agent_connection.agent_type]:
                        del self.agent_types[agent_connection.agent_type]
                
                # Remove from event subscriptions
                for event_type, subscribers in self.event_subscribers.items():
                    subscribers.discard(agent_id)
                
                self.metrics["active_connections"] = len(self.connected_agents)
                logger.info(f"Cleaned up connection for agent: {agent_id}")
    
    async def _process_agent_message(self, agent_id: str, message: Dict[str, Any]):
        """Process message from agent"""
        start_time = time.time()
        message_type = message.get("type")
        
        try:
            if message_type == MessageType.REQUEST.value:
                await self._handle_single_request(agent_id, message)
            elif message_type == MessageType.BATCH_REQUEST.value:
                await self._handle_batch_request(agent_id, message)
            elif message_type == MessageType.PING.value:
                await self._handle_ping(agent_id, message)
            elif message_type == MessageType.EVENT.value:
                await self._handle_agent_event(agent_id, message)
            else:
                logger.warning(f"Unknown message type from {agent_id}: {message_type}")
                await self._send_error(agent_id, "unknown_message_type", f"Unknown type: {message_type}")
        
        finally:
            # Update agent statistics
            if agent_id in self.connected_agents:
                latency = time.time() - start_time
                self.connected_agents[agent_id].update_stats(latency)
                self._update_avg_response_time(latency)
    
    async def _handle_single_request(self, agent_id: str, message: Dict[str, Any]):
        """Handle single request from agent"""
        request_id = message.get("request_id")
        method = message.get("method")
        params = message.get("params", {})
        
        self.metrics["total_requests"] += 1
        
        try:
            # Route request to appropriate handler
            if method in self.request_handlers:
                result = await self.request_handlers[method](params)
                
                response = {
                    "type": MessageType.RESPONSE.value,
                    "request_id": request_id,
                    "payload": result
                }
                
                await self._send_to_agent(agent_id, response)
            else:
                await self._send_error(agent_id, "unknown_method", f"Method not found: {method}", request_id)
                
        except Exception as e:
            logger.error(f"Request handler error for {method}: {e}")
            await self._send_error(agent_id, "handler_error", str(e), request_id)
    
    async def _handle_batch_request(self, agent_id: str, message: Dict[str, Any]):
        """Handle batch request from agent"""
        request_id = message.get("request_id")
        requests = message.get("requests", [])
        
        self.metrics["batch_requests"] += 1
        self.metrics["total_requests"] += len(requests)
        
        try:
            # Process requests in parallel
            tasks = []
            for req in requests:
                method = req.get("method")
                params = req.get("params", {})
                
                if method in self.request_handlers:
                    task = self.request_handlers[method](params)
                    tasks.append(task)
                else:
                    # Create error result for unknown method
                    error_task = asyncio.create_task(
                        self._create_error_result(f"Unknown method: {method}")
                    )
                    tasks.append(error_task)
            
            # Wait for all results
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Convert exceptions to error results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append({
                        "success": False,
                        "error": str(result),
                        "method": requests[i].get("method", "unknown")
                    })
                else:
                    processed_results.append(result)
            
            response = {
                "type": MessageType.BATCH_RESPONSE.value,
                "request_id": request_id,
                "results": processed_results
            }
            
            await self._send_to_agent(agent_id, response)
            
        except Exception as e:
            logger.error(f"Batch request error: {e}")
            await self._send_error(agent_id, "batch_error", str(e), request_id)
    
    async def _handle_ping(self, agent_id: str, message: Dict[str, Any]):
        """Handle ping from agent"""
        pong_message = {
            "type": MessageType.PONG.value,
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id
        }
        await self._send_to_agent(agent_id, pong_message)
    
    async def _handle_agent_event(self, agent_id: str, message: Dict[str, Any]):
        """Handle event from agent"""
        event_name = message.get("event_name")
        payload = message.get("payload", {})
        
        logger.debug(f"Received event from {agent_id}: {event_name}")
        
        # Handle specific agent events
        if event_name == "subscribe_events":
            event_types = payload.get("event_types", [])
            for event_type in event_types:
                if event_type not in self.event_subscribers:
                    self.event_subscribers[event_type] = set()
                self.event_subscribers[event_type].add(agent_id)
            
            logger.info(f"Agent {agent_id} subscribed to events: {event_types}")
    
    # Request handlers for MCP tools
    async def _handle_discover_databases(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle discover databases request"""
        try:
            databases = discover_databases()
            return {"success": True, "databases": databases}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_discover_tables(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle discover tables request"""
        try:
            database = params.get("database")
            if not database:
                return {"success": False, "error": "Database parameter required"}
            
            tables = discover_tables(database)
            return {"success": True, "tables": tables}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_get_table_schema(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get table schema request"""
        try:
            database = params.get("database")
            table = params.get("table")
            
            if not database or not table:
                return {"success": False, "error": "Database and table parameters required"}
            
            schema = get_table_schema(database, table)
            return {"success": True, "schema": schema}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_get_sample_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get sample data request"""
        try:
            database = params.get("database")
            table = params.get("table")
            limit = params.get("limit", 10)
            
            if not database or not table:
                return {"success": False, "error": "Database and table parameters required"}
            
            sample_data = get_sample_data(database, table, limit)
            return {"success": True, "sample_data": sample_data}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_execute_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle execute query request"""
        try:
            query = params.get("query")
            timeout = params.get("timeout")
            use_cache = params.get("use_cache", True)
            
            if not query:
                return {"success": False, "error": "Query parameter required"}
            
            result = execute_query(query, timeout, use_cache)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_validate_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle validate query request"""
        try:
            query = params.get("query")
            if not query:
                return {"success": False, "error": "Query parameter required"}
            
            is_valid = validate_query(query)
            return {"success": True, "valid": is_valid}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_generate_sql(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generate SQL request"""
        try:
            result = await generate_sql_tool(
                natural_language_query=params.get("natural_language_query", ""),
                schema_info=params.get("schema_info"),
                examples=params.get("examples")
            )
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_analyze_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analyze data request"""
        try:
            result = await analyze_data_tool(
                data=params.get("data", ""),
                analysis_type=params.get("analysis_type", "general"),
                context=params.get("context")
            )
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_generate_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generate text request"""
        try:
            result = await generate_text_tool(
                prompt=params.get("prompt", ""),
                system_prompt=params.get("system_prompt"),
                max_tokens=params.get("max_tokens"),
                temperature=params.get("temperature"),
                use_cache=params.get("use_cache", True)
            )
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_explain_results(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle explain results request"""
        try:
            result = await explain_results_tool(
                query=params.get("query", ""),
                results=params.get("results", []),
                context=params.get("context")
            )
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_build_schema_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle build schema context request with enhanced error handling"""
        try:
            databases = params.get("databases")
            
            # If no databases specified, discover available databases
            if not databases:
                databases = discover_databases()
            
            schema_context = {
                "databases": {},
                "tables": [],
                "total_tables": 0,
                "total_columns": 0,
                "generation_timestamp": datetime.now().isoformat()
            }
            
            for database in databases:
                try:
                    # Handle database as dict or string
                    if isinstance(database, dict):
                        database_name = database.get("name", "unknown")
                    else:
                        database_name = str(database)
                    
                    # Get tables for this database
                    tables = discover_tables(database_name)
                    database_info = {
                        "name": database_name,
                        "tables": {},
                        "table_count": len(tables)
                    }
                    
                    for table in tables:
                        try:
                            # Get schema for each table (ensure table is string)
                            table_name = table.get("name") if isinstance(table, dict) else str(table)
                            schema = get_table_schema(database_name, table_name)
                            database_info["tables"][table_name] = schema
                            schema_context["total_columns"] += len(schema.get("columns", []))
                        except Exception as e:
                            table_name = table.get("name") if isinstance(table, dict) else str(table)
                            logger.warning(f"Failed to get schema for {database_name}.{table_name}: {e}")
                            database_info["tables"][table_name] = {"error": str(e)}
                    
                    schema_context["databases"][database_name] = database_info
                    schema_context["tables"].extend([f"{database_name}.{table.get('name') if isinstance(table, dict) else str(table)}" for table in tables])
                    schema_context["total_tables"] += len(tables)
                    
                except Exception as e:
                    database_name = database.get("name") if isinstance(database, dict) else str(database)
                    logger.warning(f"Failed to process database {database_name}: {e}")
                    schema_context["databases"][database_name] = {"error": str(e)}
            
            return {
                "success": True,
                "schema_context": schema_context,
                "metadata": {
                    "databases_processed": len(schema_context["databases"]),
                    "total_tables": schema_context["total_tables"],
                    "total_columns": schema_context["total_columns"]
                }
            }
            
        except Exception as e:
            logger.error(f"Schema context building failed: {e}")
            return {"success": False, "error": str(e), "schema_context": None}
    
    async def _handle_health_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check request"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "active_connections": len(self.connected_agents),
            "server_type": "websocket_mcp"
        }
    
    async def _handle_get_server_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get server stats request"""
        try:
            stats = get_server_stats()
            return stats
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_get_agent_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get agent stats request"""
        agent_stats = {}
        
        for agent_id, connection in self.connected_agents.items():
            agent_stats[agent_id] = {
                "agent_type": connection.agent_type,
                "connected_at": connection.connected_at.isoformat(),
                "request_count": connection.request_count,
                "avg_latency": connection.avg_latency,
                "capabilities": connection.capabilities
            }
        
        return {
            "success": True,
            "agent_stats": agent_stats,
            "server_metrics": self.metrics
        }
    
    async def _handle_subscribe_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle event subscription request"""
        return {"success": True, "message": "Use event message type for subscriptions"}
    
    # Utility methods
    async def _send_to_agent(self, agent_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific agent"""
        if agent_id in self.connected_agents:
            return await self.connected_agents[agent_id].send_message(message)
        return False
    
    async def _send_error(
        self,
        agent_id: str,
        error_type: str,
        error_message: str,
        request_id: Optional[str] = None
    ):
        """Send error message to agent"""
        error_response = {
            "type": MessageType.ERROR.value,
            "error_type": error_type,
            "error": error_message,
            "timestamp": datetime.now().isoformat()
        }
        
        if request_id:
            error_response["request_id"] = request_id
        
        await self._send_to_agent(agent_id, error_response)
    
    async def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result for batch processing"""
        return {"success": False, "error": error_message}
    
    def _update_avg_response_time(self, response_time: float):
        """Update average response time metric"""
        total_requests = self.metrics["total_requests"]
        if total_requests > 0:
            current_avg = self.metrics["avg_response_time"]
            alpha = 0.1  # Exponential moving average factor
            self.metrics["avg_response_time"] = (alpha * response_time) + ((1 - alpha) * current_avg)
    
    # Event broadcasting
    async def broadcast_event(
        self,
        event_name: str,
        payload: Dict[str, Any],
        agent_types: Optional[List[str]] = None,
        agent_ids: Optional[List[str]] = None
    ):
        """Broadcast event to subscribed agents"""
        event_message = {
            "type": MessageType.EVENT.value,
            "event_name": event_name,
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }
        
        target_agents = set()
        
        # Add agents subscribed to this event type
        if event_name in self.event_subscribers:
            target_agents.update(self.event_subscribers[event_name])
        
        # Add agents by type filter
        if agent_types:
            for agent_type in agent_types:
                if agent_type in self.agent_types:
                    target_agents.update(self.agent_types[agent_type])
        
        # Add specific agent IDs
        if agent_ids:
            target_agents.update(agent_ids)
        
        # If no specific targets, broadcast to all
        if not target_agents and not agent_types and not agent_ids:
            target_agents = set(self.connected_agents.keys())
        
        # Send to target agents
        sent_count = 0
        for agent_id in target_agents:
            if await self._send_to_agent(agent_id, event_message):
                sent_count += 1
        
        self.metrics["events_broadcast"] += 1
        logger.info(f"Broadcasted event '{event_name}' to {sent_count} agents")
        
        return sent_count
    
    # Background tasks
    async def _cleanup_loop(self):
        """Background cleanup task"""
        while True:
            try:
                await asyncio.sleep(30)  # Cleanup every 30 seconds
                await self._cleanup_stale_connections()
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
    
    async def _heartbeat_loop(self):
        """Background heartbeat task"""
        while True:
            try:
                await asyncio.sleep(60)  # Heartbeat every minute
                await self._send_heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
    
    async def _cleanup_stale_connections(self):
        """Clean up stale connections"""
        current_time = time.time()
        stale_agents = []
        
        for agent_id, connection in self.connected_agents.items():
            # Consider connection stale if no ping for 5 minutes
            if current_time - connection.last_ping > 300:
                stale_agents.append(agent_id)
        
        for agent_id in stale_agents:
            logger.warning(f"Removing stale connection: {agent_id}")
            # Connection will be cleaned up when WebSocket closes
            try:
                await self.connected_agents[agent_id].websocket.close()
            except:
                pass
    
    async def _send_heartbeat(self):
        """Send heartbeat to all connected agents"""
        heartbeat_message = {
            "type": MessageType.EVENT.value,
            "event_name": "server_heartbeat",
            "payload": {
                "timestamp": datetime.now().isoformat(),
                "active_connections": len(self.connected_agents),
                "server_metrics": self.metrics
            }
        }
        
        for agent_id in list(self.connected_agents.keys()):
            await self._send_to_agent(agent_id, heartbeat_message)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        agent_type_counts = {
            agent_type: len(agent_ids)
            for agent_type, agent_ids in self.agent_types.items()
        }
        
        return {
            "total_connections": self.metrics["total_connections"],
            "active_connections": self.metrics["active_connections"],
            "agent_type_distribution": agent_type_counts,
            "total_requests": self.metrics["total_requests"],
            "batch_requests": self.metrics["batch_requests"],
            "events_broadcast": self.metrics["events_broadcast"],
            "avg_response_time": self.metrics["avg_response_time"]
        }
