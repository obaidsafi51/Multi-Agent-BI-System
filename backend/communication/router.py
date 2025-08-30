"""
Message routing and transformation logic for agent communication.
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import asyncio

from .models import AgentMessage, MessageType, AgentType, WorkflowTask, TaskStatus
from .mcp import MCPContextStore
from .a2a import A2AMessageBroker
from .acp import ACPOrchestrator


logger = logging.getLogger(__name__)


class MessageRouter:
    """Routes and transforms messages between communication protocols"""
    
    def __init__(self, mcp_store: MCPContextStore, a2a_broker: A2AMessageBroker, 
                 acp_orchestrator: ACPOrchestrator):
        """
        Initialize message router.
        
        Args:
            mcp_store: MCP context store
            a2a_broker: A2A message broker
            acp_orchestrator: ACP orchestrator
        """
        self.mcp_store = mcp_store
        self.a2a_broker = a2a_broker
        self.acp_orchestrator = acp_orchestrator
        self._transformation_rules: Dict[str, Callable] = {}
        self._routing_rules: Dict[MessageType, List[AgentType]] = {}
        
        # Register default transformation rules
        self._register_default_transformations()
        
        # Register default routing rules
        self._register_default_routing()
    
    def _register_default_transformations(self) -> None:
        """Register default message transformation rules"""
        
        def transform_query_to_workflow(message: AgentMessage) -> List[WorkflowTask]:
            """Transform query processing message to workflow tasks"""
            tasks = []
            
            # NLP processing task
            nlp_task = WorkflowTask(
                workflow_id=message.message_id,
                task_name="nlp_processing",
                agent_type=AgentType.NLP,
                payload=message.payload,
                dependencies=[]
            )
            tasks.append(nlp_task)
            
            # Data retrieval task (depends on NLP)
            data_task = WorkflowTask(
                workflow_id=message.message_id,
                task_name="data_retrieval",
                agent_type=AgentType.DATA,
                payload={},
                dependencies=[nlp_task.task_id]
            )
            tasks.append(data_task)
            
            # Visualization task (depends on data)
            viz_task = WorkflowTask(
                workflow_id=message.message_id,
                task_name="visualization_generation",
                agent_type=AgentType.VISUALIZATION,
                payload={},
                dependencies=[data_task.task_id]
            )
            tasks.append(viz_task)
            
            # Personalization task (can run in parallel with viz)
            personal_task = WorkflowTask(
                workflow_id=message.message_id,
                task_name="personalization_update",
                agent_type=AgentType.PERSONALIZATION,
                payload={"user_id": message.payload.get("user_id")},
                dependencies=[nlp_task.task_id]
            )
            tasks.append(personal_task)
            
            return tasks
        
        def transform_error_to_notification(message: AgentMessage) -> AgentMessage:
            """Transform error message to notification"""
            return AgentMessage(
                message_type=MessageType.ERROR_NOTIFICATION,
                sender=message.sender,
                recipient=AgentType.BACKEND,
                payload={
                    "error_type": message.payload.get("error_type", "unknown"),
                    "error_message": message.payload.get("error", "Unknown error"),
                    "original_message_id": message.message_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                correlation_id=message.correlation_id
            )
        
        self._transformation_rules["query_to_workflow"] = transform_query_to_workflow
        self._transformation_rules["error_to_notification"] = transform_error_to_notification
    
    def _register_default_routing(self) -> None:
        """Register default message routing rules"""
        self._routing_rules = {
            MessageType.QUERY_PROCESSING: [AgentType.NLP],
            MessageType.DATA_REQUEST: [AgentType.DATA],
            MessageType.VISUALIZATION_REQUEST: [AgentType.VISUALIZATION],
            MessageType.PERSONALIZATION_UPDATE: [AgentType.PERSONALIZATION],
            MessageType.ERROR_NOTIFICATION: [AgentType.BACKEND],
            MessageType.HEALTH_CHECK: [AgentType.NLP, AgentType.DATA, AgentType.VISUALIZATION, AgentType.PERSONALIZATION]
        }
    
    def register_transformation_rule(self, rule_name: str, transformer: Callable) -> None:
        """
        Register custom transformation rule.
        
        Args:
            rule_name: Name of the transformation rule
            transformer: Function to transform messages
        """
        self._transformation_rules[rule_name] = transformer
        logger.debug(f"Registered transformation rule: {rule_name}")
    
    def register_routing_rule(self, message_type: MessageType, agents: List[AgentType]) -> None:
        """
        Register custom routing rule.
        
        Args:
            message_type: Type of message to route
            agents: List of agents to route to
        """
        self._routing_rules[message_type] = agents
        logger.debug(f"Registered routing rule for {message_type}: {agents}")
    
    async def route_message(self, message: AgentMessage) -> bool:
        """
        Route message to appropriate agents.
        
        Args:
            message: Message to route
            
        Returns:
            True if routed successfully
        """
        try:
            # Get routing rules for message type
            target_agents = self._routing_rules.get(message.message_type, [])
            
            if not target_agents:
                logger.warning(f"No routing rule for message type: {message.message_type}")
                return False
            
            # Store context if available
            if message.context_id:
                await self._update_message_context(message)
            
            # Route to each target agent
            success_count = 0
            for agent in target_agents:
                routed_message = AgentMessage(
                    message_type=message.message_type,
                    sender=message.sender,
                    recipient=agent,
                    payload=message.payload,
                    context_id=message.context_id,
                    correlation_id=message.correlation_id,
                    reply_to=message.reply_to,
                    ttl=message.ttl
                )
                
                if await self.a2a_broker.send_message(routed_message):
                    success_count += 1
                else:
                    logger.error(f"Failed to route message to {agent}")
            
            logger.info(f"Routed {message.message_type} to {success_count}/{len(target_agents)} agents")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to route message: {e}")
            return False
    
    async def transform_and_route(self, message: AgentMessage, transformation_rule: str) -> bool:
        """
        Transform message and route to appropriate agents.
        
        Args:
            message: Message to transform and route
            transformation_rule: Name of transformation rule to apply
            
        Returns:
            True if transformed and routed successfully
        """
        try:
            transformer = self._transformation_rules.get(transformation_rule)
            if not transformer:
                logger.error(f"Unknown transformation rule: {transformation_rule}")
                return False
            
            # Apply transformation
            transformed = transformer(message)
            
            if isinstance(transformed, list):
                # Handle workflow tasks
                if all(isinstance(item, WorkflowTask) for item in transformed):
                    workflow = await self.acp_orchestrator.create_workflow(
                        workflow_name=f"query_processing_{message.message_id}",
                        tasks=transformed,
                        context_id=message.context_id
                    )
                    
                    await self.acp_orchestrator.execute_workflow(workflow.workflow_id)
                    return True
            elif isinstance(transformed, AgentMessage):
                # Handle transformed message
                return await self.route_message(transformed)
            
            logger.error(f"Invalid transformation result type: {type(transformed)}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to transform and route message: {e}")
            return False
    
    async def broadcast_health_check(self) -> Dict[AgentType, bool]:
        """
        Broadcast health check to all agents.
        
        Returns:
            Dictionary mapping agent types to health check results
        """
        try:
            health_message = AgentMessage(
                message_type=MessageType.HEALTH_CHECK,
                sender=AgentType.BACKEND,
                recipient=AgentType.BACKEND,  # Will be overridden in broadcast
                payload={"timestamp": datetime.utcnow().isoformat()}
            )
            
            # Broadcast health check
            await self.a2a_broker.broadcast_message(health_message)
            
            # Wait for responses (simplified - in real implementation, would collect responses)
            await asyncio.sleep(5)
            
            # Return health status for each agent
            results = {}
            for agent_type in [AgentType.NLP, AgentType.DATA, AgentType.VISUALIZATION, AgentType.PERSONALIZATION]:
                # In real implementation, would check actual responses
                results[agent_type] = True
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to broadcast health check: {e}")
            return {}
    
    async def _update_message_context(self, message: AgentMessage) -> None:
        """
        Update context store with message information.
        
        Args:
            message: Message containing context information
        """
        try:
            if not message.context_id:
                return
            
            context = await self.mcp_store.get_context(message.context_id)
            if context:
                # Update context with message information
                context_update = {
                    "last_message": {
                        "message_id": message.message_id,
                        "message_type": message.message_type.value,
                        "sender": message.sender.value,
                        "timestamp": message.timestamp.isoformat()
                    }
                }
                
                await self.mcp_store.update_context(
                    message.context_id,
                    context_update,
                    {"last_updated_by": "message_router"}
                )
            
        except Exception as e:
            logger.error(f"Failed to update message context: {e}")
    
    async def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics.
        
        Returns:
            Dictionary with routing statistics
        """
        try:
            return {
                "transformation_rules": len(self._transformation_rules),
                "routing_rules": len(self._routing_rules),
                "registered_message_types": list(self._routing_rules.keys()),
                "target_agents": list(set(
                    agent for agents in self._routing_rules.values() for agent in agents
                ))
            }
            
        except Exception as e:
            logger.error(f"Failed to get routing stats: {e}")
            return {"error": str(e)}


class RetryManager:
    """Manages retry mechanisms and fault tolerance"""
    
    def __init__(self, max_retries: int = 3, base_delay: int = 60):
        """
        Initialize retry manager.
        
        Args:
            max_retries: Maximum number of retries
            base_delay: Base delay in seconds for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._retry_counts: Dict[str, int] = {}
    
    async def execute_with_retry(self, operation: Callable, operation_id: str, 
                               *args, **kwargs) -> Any:
        """
        Execute operation with retry logic.
        
        Args:
            operation: Async operation to execute
            operation_id: Unique identifier for the operation
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Operation result
        """
        retry_count = self._retry_counts.get(operation_id, 0)
        
        while retry_count <= self.max_retries:
            try:
                result = await operation(*args, **kwargs)
                
                # Reset retry count on success
                if operation_id in self._retry_counts:
                    del self._retry_counts[operation_id]
                
                return result
                
            except Exception as e:
                retry_count += 1
                self._retry_counts[operation_id] = retry_count
                
                if retry_count > self.max_retries:
                    logger.error(f"Operation {operation_id} failed after {self.max_retries} retries: {e}")
                    raise
                
                # Calculate delay with exponential backoff
                delay = self.base_delay * (2 ** (retry_count - 1))
                logger.warning(f"Operation {operation_id} failed, retrying in {delay}s (attempt {retry_count}/{self.max_retries}): {e}")
                
                await asyncio.sleep(delay)
        
        raise Exception(f"Operation {operation_id} exceeded maximum retries")
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """
        Get retry statistics.
        
        Returns:
            Dictionary with retry statistics
        """
        return {
            "active_retries": len(self._retry_counts),
            "retry_operations": dict(self._retry_counts),
            "max_retries": self.max_retries,
            "base_delay": self.base_delay
        }