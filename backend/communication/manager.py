"""
Communication manager that coordinates all communication protocols.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import os

from .mcp import MCPContextStore
from .a2a import A2AMessageBroker
from .acp import ACPOrchestrator
from .router import MessageRouter, RetryManager
from .models import (
    ContextData, AgentMessage, WorkflowTask, MessageType, 
    TaskStatus, AgentType, HealthCheckResponse
)


logger = logging.getLogger(__name__)


class CommunicationManager:
    """Manages all communication protocols and coordination"""
    
    def __init__(self, 
                 redis_url: str = None,
                 rabbitmq_url: str = None,
                 celery_broker_url: str = None,
                 celery_backend_url: str = None):
        """
        Initialize communication manager.
        
        Args:
            redis_url: Redis connection URL for MCP
            rabbitmq_url: RabbitMQ connection URL for A2A
            celery_broker_url: Celery broker URL for ACP
            celery_backend_url: Celery backend URL for ACP
        """
        # Use environment variables as defaults
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.rabbitmq_url = rabbitmq_url or os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self.celery_broker_url = celery_broker_url or os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
        self.celery_backend_url = celery_backend_url or os.getenv("CELERY_BACKEND_URL", "redis://localhost:6379/2")
        
        # Initialize components
        self.mcp_store = MCPContextStore(self.redis_url)
        self.a2a_broker = A2AMessageBroker(self.rabbitmq_url)
        self.acp_orchestrator = ACPOrchestrator(
            self.celery_broker_url,
            self.celery_backend_url,
            self.mcp_store,
            self.a2a_broker
        )
        self.router = MessageRouter(self.mcp_store, self.a2a_broker, self.acp_orchestrator)
        self.retry_manager = RetryManager()
        
        self._agent_type: Optional[AgentType] = None
        self._is_connected = False
        self._health_check_interval = 60  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def initialize(self, agent_type: AgentType) -> None:
        """
        Initialize all communication protocols.
        
        Args:
            agent_type: Type of agent initializing
        """
        try:
            self._agent_type = agent_type
            
            logger.info(f"Initializing communication manager for {agent_type.value} agent")
            
            # Connect to MCP store
            await self.mcp_store.connect()
            logger.info("Connected to MCP context store")
            
            # Connect to A2A broker
            await self.a2a_broker.connect(agent_type)
            logger.info("Connected to A2A message broker")
            
            # Start consuming messages
            await self.a2a_broker.start_consuming()
            logger.info("Started consuming A2A messages")
            
            # Register default message handlers
            self._register_default_handlers()
            
            # Start health check monitoring
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            self._is_connected = True
            logger.info(f"Communication manager initialized successfully for {agent_type.value}")
            
        except Exception as e:
            logger.error(f"Failed to initialize communication manager: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self) -> None:
        """Shutdown all communication protocols"""
        try:
            logger.info("Shutting down communication manager")
            
            self._is_connected = False
            
            # Cancel health check task
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Disconnect from protocols
            if self.a2a_broker:
                await self.a2a_broker.disconnect()
            
            if self.mcp_store:
                await self.mcp_store.disconnect()
            
            logger.info("Communication manager shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def _register_default_handlers(self) -> None:
        """Register default message handlers"""
        
        async def health_check_handler(message: AgentMessage):
            """Handle health check messages"""
            try:
                health_response = HealthCheckResponse(
                    agent_type=self._agent_type,
                    status="healthy",
                    details={
                        "mcp_connected": self.mcp_store._redis is not None,
                        "a2a_connected": not (self.a2a_broker._connection and self.a2a_broker._connection.is_closed),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                # Send response if reply_to is specified
                if message.reply_to:
                    response = AgentMessage(
                        message_type=MessageType.HEALTH_CHECK,
                        sender=self._agent_type,
                        recipient=message.sender,
                        payload=health_response.dict(),
                        correlation_id=message.correlation_id
                    )
                    await self.send_message(response)
                
            except Exception as e:
                logger.error(f"Error handling health check: {e}")
        
        async def error_notification_handler(message: AgentMessage):
            """Handle error notification messages"""
            try:
                logger.error(f"Received error notification from {message.sender}: {message.payload}")
                
                # Store error in context if available
                if message.context_id:
                    await self.update_context(
                        message.context_id,
                        {"last_error": message.payload},
                        {"error_timestamp": datetime.utcnow().isoformat()}
                    )
                
            except Exception as e:
                logger.error(f"Error handling error notification: {e}")
        
        # Register handlers
        self.a2a_broker.register_handler(MessageType.HEALTH_CHECK, health_check_handler)
        self.a2a_broker.register_handler(MessageType.ERROR_NOTIFICATION, error_notification_handler)
    
    async def send_message(self, message: AgentMessage) -> bool:
        """
        Send message through A2A protocol.
        
        Args:
            message: Message to send
            
        Returns:
            True if sent successfully
        """
        if not self._is_connected:
            logger.error("Communication manager not connected")
            return False
        
        return await self.retry_manager.execute_with_retry(
            self.a2a_broker.send_message,
            f"send_message_{message.message_id}",
            message
        )
    
    async def broadcast_message(self, message: AgentMessage) -> bool:
        """
        Broadcast message to all agents.
        
        Args:
            message: Message to broadcast
            
        Returns:
            True if broadcast successfully
        """
        if not self._is_connected:
            logger.error("Communication manager not connected")
            return False
        
        return await self.retry_manager.execute_with_retry(
            self.a2a_broker.broadcast_message,
            f"broadcast_message_{message.message_id}",
            message
        )
    
    async def send_request_response(self, request: AgentMessage, timeout: int = 30) -> Optional[AgentMessage]:
        """
        Send request and wait for response.
        
        Args:
            request: Request message
            timeout: Timeout in seconds
            
        Returns:
            Response message if received
        """
        if not self._is_connected:
            logger.error("Communication manager not connected")
            return None
        
        return await self.a2a_broker.send_request_response(request, timeout)
    
    async def store_context(self, context: ContextData, ttl: Optional[int] = None) -> bool:
        """
        Store context in MCP store.
        
        Args:
            context: Context data to store
            ttl: Time to live in seconds
            
        Returns:
            True if stored successfully
        """
        if not self._is_connected:
            logger.error("Communication manager not connected")
            return False
        
        return await self.retry_manager.execute_with_retry(
            self.mcp_store.store_context,
            f"store_context_{context.context_id}",
            context,
            ttl
        )
    
    async def get_context(self, context_id: str) -> Optional[ContextData]:
        """
        Get context from MCP store.
        
        Args:
            context_id: Context identifier
            
        Returns:
            Context data if found
        """
        if not self._is_connected:
            logger.error("Communication manager not connected")
            return None
        
        return await self.mcp_store.get_context(context_id)
    
    async def update_context(self, context_id: str, data: Dict[str, Any], 
                           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update context in MCP store.
        
        Args:
            context_id: Context identifier
            data: Data to update
            metadata: Metadata to update
            
        Returns:
            True if updated successfully
        """
        if not self._is_connected:
            logger.error("Communication manager not connected")
            return False
        
        return await self.retry_manager.execute_with_retry(
            self.mcp_store.update_context,
            f"update_context_{context_id}",
            context_id,
            data,
            metadata
        )
    
    async def create_workflow(self, workflow_name: str, tasks: List[WorkflowTask], 
                            context_id: Optional[str] = None) -> Optional[str]:
        """
        Create and execute workflow.
        
        Args:
            workflow_name: Name of the workflow
            tasks: List of tasks in the workflow
            context_id: Associated context ID
            
        Returns:
            Workflow ID if created successfully
        """
        if not self._is_connected:
            logger.error("Communication manager not connected")
            return None
        
        try:
            workflow = await self.acp_orchestrator.create_workflow(
                workflow_name, tasks, context_id
            )
            
            task_id = await self.acp_orchestrator.execute_workflow(workflow.workflow_id)
            logger.info(f"Created and executed workflow {workflow.workflow_id}: {task_id}")
            
            return workflow.workflow_id
            
        except Exception as e:
            logger.error(f"Failed to create workflow: {e}")
            return None
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow status.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Workflow status information
        """
        return await self.acp_orchestrator.get_workflow_status(workflow_id)
    
    def register_message_handler(self, message_type: MessageType, handler: Callable) -> None:
        """
        Register message handler.
        
        Args:
            message_type: Type of message to handle
            handler: Async function to handle the message
        """
        self.a2a_broker.register_handler(message_type, handler)
    
    def register_task_handler(self, task_name: str, handler: Callable) -> None:
        """
        Register task handler.
        
        Args:
            task_name: Name of the task
            handler: Async function to handle the task
        """
        self.acp_orchestrator.register_task_handler(task_name, handler)
    
    def register_routing_rule(self, message_type: MessageType, agents: List[AgentType]) -> None:
        """
        Register custom routing rule.
        
        Args:
            message_type: Type of message to route
            agents: List of agents to route to
        """
        self.router.register_routing_rule(message_type, agents)
    
    async def route_message(self, message: AgentMessage) -> bool:
        """
        Route message using router.
        
        Args:
            message: Message to route
            
        Returns:
            True if routed successfully
        """
        return await self.router.route_message(message)
    
    async def _health_check_loop(self) -> None:
        """Periodic health check loop"""
        while self._is_connected:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                if not self._is_connected:
                    break
                
                # Perform health checks
                mcp_healthy = self.mcp_store._redis is not None
                a2a_healthy = not (self.a2a_broker._connection and self.a2a_broker._connection.is_closed)
                
                if not mcp_healthy:
                    logger.warning("MCP store connection unhealthy, attempting reconnect")
                    try:
                        await self.mcp_store.connect()
                    except Exception as e:
                        logger.error(f"Failed to reconnect MCP store: {e}")
                
                if not a2a_healthy:
                    logger.warning("A2A broker connection unhealthy, attempting reconnect")
                    try:
                        await self.a2a_broker.connect(self._agent_type)
                        await self.a2a_broker.start_consuming()
                    except Exception as e:
                        logger.error(f"Failed to reconnect A2A broker: {e}")
                
                # Clean up expired contexts
                if mcp_healthy:
                    cleaned = await self.mcp_store.cleanup_expired_contexts()
                    if cleaned > 0:
                        logger.info(f"Cleaned up {cleaned} expired contexts")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.
        
        Returns:
            Dictionary with system status information
        """
        try:
            # Get component health
            mcp_stats = await self.mcp_store.get_context_stats()
            a2a_stats = await self.a2a_broker.get_queue_stats()
            acp_metrics = await self.acp_orchestrator.get_metrics()
            routing_stats = await self.router.get_routing_stats()
            retry_stats = self.retry_manager.get_retry_stats()
            
            return {
                "agent_type": self._agent_type.value if self._agent_type else None,
                "connected": self._is_connected,
                "timestamp": datetime.utcnow().isoformat(),
                "mcp": {
                    "status": "healthy" if self.mcp_store._redis else "unhealthy",
                    "stats": mcp_stats
                },
                "a2a": {
                    "status": "healthy" if not (self.a2a_broker._connection and self.a2a_broker._connection.is_closed) else "unhealthy",
                    "stats": a2a_stats
                },
                "acp": {
                    "status": "healthy",  # Simplified check
                    "metrics": acp_metrics
                },
                "routing": routing_stats,
                "retry": retry_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }