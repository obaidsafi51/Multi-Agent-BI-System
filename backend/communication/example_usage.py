"""
Example usage of communication protocols for AI CFO BI Agent system.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from .manager import CommunicationManager
from .models import (
    ContextData, AgentMessage, WorkflowTask, MessageType, 
    TaskStatus, AgentType
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_nlp_agent():
    """Example NLP agent implementation"""
    
    # Initialize communication manager
    comm_manager = CommunicationManager()
    await comm_manager.initialize(AgentType.NLP)
    
    try:
        # Register message handlers
        async def query_processing_handler(message: AgentMessage):
            """Handle query processing messages"""
            logger.info(f"NLP Agent processing query: {message.payload.get('query')}")
            
            # Simulate NLP processing
            await asyncio.sleep(1)
            
            # Extract intent and entities
            result = {
                "intent": "revenue_query",
                "entities": ["revenue", "Q1", "2024"],
                "confidence": 0.95,
                "processed_query": message.payload.get('query')
            }
            
            # Update context with results
            if message.context_id:
                await comm_manager.update_context(
                    message.context_id,
                    {"nlp_result": result},
                    {"processed_by": "nlp_agent", "timestamp": datetime.utcnow().isoformat()}
                )
            
            # Send result to data agent
            data_message = AgentMessage(
                message_type=MessageType.DATA_REQUEST,
                sender=AgentType.NLP,
                recipient=AgentType.DATA,
                payload={
                    "intent": result["intent"],
                    "entities": result["entities"],
                    "original_query": message.payload.get('query')
                },
                context_id=message.context_id,
                correlation_id=message.correlation_id
            )
            
            await comm_manager.send_message(data_message)
            logger.info("Sent data request to Data Agent")
        
        # Register task handlers for ACP
        async def nlp_processing_task(task: WorkflowTask):
            """Handle NLP processing task in workflow"""
            logger.info(f"Executing NLP task: {task.task_name}")
            
            query = task.payload.get('query', '')
            
            # Simulate processing
            await asyncio.sleep(1)
            
            return {
                "intent": "revenue_query",
                "entities": ["revenue", "Q1"],
                "confidence": 0.95,
                "processed_query": query
            }
        
        # Register handlers
        comm_manager.register_message_handler(MessageType.QUERY_PROCESSING, query_processing_handler)
        comm_manager.register_task_handler("nlp_processing", nlp_processing_task)
        
        logger.info("NLP Agent initialized and ready")
        
        # Keep agent running
        while True:
            await asyncio.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("Shutting down NLP Agent")
    finally:
        await comm_manager.shutdown()


async def example_data_agent():
    """Example Data agent implementation"""
    
    # Initialize communication manager
    comm_manager = CommunicationManager()
    await comm_manager.initialize(AgentType.DATA)
    
    try:
        # Register message handlers
        async def data_request_handler(message: AgentMessage):
            """Handle data request messages"""
            logger.info(f"Data Agent processing request: {message.payload.get('intent')}")
            
            # Simulate database query
            await asyncio.sleep(2)
            
            # Mock data results
            data_result = {
                "data": [
                    {"month": "Jan", "revenue": 100000},
                    {"month": "Feb", "revenue": 120000},
                    {"month": "Mar", "revenue": 110000}
                ],
                "total_revenue": 330000,
                "query_metadata": {
                    "execution_time_ms": 150,
                    "rows_returned": 3
                }
            }
            
            # Update context with results
            if message.context_id:
                await comm_manager.update_context(
                    message.context_id,
                    {"data_result": data_result},
                    {"processed_by": "data_agent", "timestamp": datetime.utcnow().isoformat()}
                )
            
            # Send result to visualization agent
            viz_message = AgentMessage(
                message_type=MessageType.VISUALIZATION_REQUEST,
                sender=AgentType.DATA,
                recipient=AgentType.VISUALIZATION,
                payload={
                    "data": data_result["data"],
                    "chart_type": "line",
                    "title": "Q1 Revenue Trend"
                },
                context_id=message.context_id,
                correlation_id=message.correlation_id
            )
            
            await comm_manager.send_message(viz_message)
            logger.info("Sent visualization request to Viz Agent")
        
        # Register task handlers
        async def data_retrieval_task(task: WorkflowTask):
            """Handle data retrieval task in workflow"""
            logger.info(f"Executing Data task: {task.task_name}")
            
            # Simulate database query
            await asyncio.sleep(1)
            
            return {
                "data": [
                    {"month": "Jan", "revenue": 100000},
                    {"month": "Feb", "revenue": 120000},
                    {"month": "Mar", "revenue": 110000}
                ],
                "total_revenue": 330000
            }
        
        # Register handlers
        comm_manager.register_message_handler(MessageType.DATA_REQUEST, data_request_handler)
        comm_manager.register_task_handler("data_retrieval", data_retrieval_task)
        
        logger.info("Data Agent initialized and ready")
        
        # Keep agent running
        while True:
            await asyncio.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("Shutting down Data Agent")
    finally:
        await comm_manager.shutdown()


async def example_backend_orchestrator():
    """Example backend orchestrator that coordinates query processing"""
    
    # Initialize communication manager
    comm_manager = CommunicationManager()
    await comm_manager.initialize(AgentType.BACKEND)
    
    try:
        logger.info("Backend Orchestrator initialized")
        
        # Example 1: Direct message routing
        await example_direct_messaging(comm_manager)
        
        # Example 2: Workflow orchestration
        await example_workflow_orchestration(comm_manager)
        
        # Example 3: Context management
        await example_context_management(comm_manager)
        
        # Example 4: Health monitoring
        await example_health_monitoring(comm_manager)
        
    except Exception as e:
        logger.error(f"Error in backend orchestrator: {e}")
    finally:
        await comm_manager.shutdown()


async def example_direct_messaging(comm_manager: CommunicationManager):
    """Example of direct A2A messaging"""
    logger.info("=== Example 1: Direct Messaging ===")
    
    # Create context for the query
    context = ContextData(
        session_id="example_session_1",
        user_id="example_user",
        data={"original_query": "Show me Q1 revenue"}
    )
    
    await comm_manager.store_context(context)
    
    # Send query to NLP agent
    query_message = AgentMessage(
        message_type=MessageType.QUERY_PROCESSING,
        sender=AgentType.BACKEND,
        recipient=AgentType.NLP,
        payload={
            "query": "Show me Q1 revenue",
            "user_id": "example_user"
        },
        context_id=context.context_id
    )
    
    success = await comm_manager.send_message(query_message)
    logger.info(f"Query message sent: {success}")
    
    # Wait for processing
    await asyncio.sleep(5)
    
    # Check updated context
    updated_context = await comm_manager.get_context(context.context_id)
    if updated_context:
        logger.info(f"Context updated with: {list(updated_context.data.keys())}")


async def example_workflow_orchestration(comm_manager: CommunicationManager):
    """Example of ACP workflow orchestration"""
    logger.info("=== Example 2: Workflow Orchestration ===")
    
    # Create context
    context = ContextData(
        session_id="example_session_2",
        user_id="example_user",
        data={"workflow_query": "Generate revenue dashboard"}
    )
    
    await comm_manager.store_context(context)
    
    # Define workflow tasks
    tasks = [
        WorkflowTask(
            workflow_id="revenue_dashboard_workflow",
            task_name="nlp_processing",
            agent_type=AgentType.NLP,
            payload={"query": "Generate revenue dashboard"},
            dependencies=[]
        ),
        WorkflowTask(
            workflow_id="revenue_dashboard_workflow",
            task_name="data_retrieval",
            agent_type=AgentType.DATA,
            payload={},
            dependencies=[]  # Will be set by orchestrator
        ),
        WorkflowTask(
            workflow_id="revenue_dashboard_workflow",
            task_name="visualization_generation",
            agent_type=AgentType.VISUALIZATION,
            payload={},
            dependencies=[]  # Will be set by orchestrator
        )
    ]
    
    # Create and execute workflow
    workflow_id = await comm_manager.create_workflow(
        "Revenue Dashboard Generation",
        tasks,
        context.context_id
    )
    
    if workflow_id:
        logger.info(f"Workflow created: {workflow_id}")
        
        # Monitor workflow status
        for i in range(10):
            await asyncio.sleep(2)
            status = await comm_manager.get_workflow_status(workflow_id)
            if status:
                logger.info(f"Workflow status: {status['status']}")
                if status['status'] in [TaskStatus.SUCCESS, TaskStatus.FAILURE]:
                    break


async def example_context_management(comm_manager: CommunicationManager):
    """Example of MCP context management"""
    logger.info("=== Example 3: Context Management ===")
    
    # Create context with initial data
    context = ContextData(
        session_id="example_session_3",
        user_id="example_user",
        data={
            "conversation_history": [],
            "user_preferences": {"chart_type": "line", "color_scheme": "blue"}
        },
        metadata={"created_by": "backend"}
    )
    
    await comm_manager.store_context(context)
    logger.info(f"Created context: {context.context_id}")
    
    # Simulate conversation updates
    for i in range(3):
        await comm_manager.update_context(
            context.context_id,
            {
                "conversation_history": [f"Message {i+1}: Query about revenue"],
                "last_activity": datetime.utcnow().isoformat()
            },
            {"update_count": i + 1}
        )
        
        await asyncio.sleep(1)
    
    # Retrieve final context
    final_context = await comm_manager.get_context(context.context_id)
    if final_context:
        logger.info(f"Final context version: {final_context.version}")
        logger.info(f"Context data keys: {list(final_context.data.keys())}")


async def example_health_monitoring(comm_manager: CommunicationManager):
    """Example of system health monitoring"""
    logger.info("=== Example 4: Health Monitoring ===")
    
    # Get system status
    status = await comm_manager.get_system_status()
    logger.info(f"System status: {status['connected']}")
    logger.info(f"MCP status: {status['mcp']['status']}")
    logger.info(f"A2A status: {status['a2a']['status']}")
    
    # Broadcast health check
    health_message = AgentMessage(
        message_type=MessageType.HEALTH_CHECK,
        sender=AgentType.BACKEND,
        recipient=AgentType.BACKEND,  # Will be broadcast
        payload={"timestamp": datetime.utcnow().isoformat()}
    )
    
    success = await comm_manager.broadcast_message(health_message)
    logger.info(f"Health check broadcast: {success}")


async def run_example_system():
    """Run example system with multiple agents"""
    logger.info("Starting example AI CFO BI Agent communication system")
    
    # Start agents concurrently
    tasks = [
        asyncio.create_task(example_nlp_agent()),
        asyncio.create_task(example_data_agent()),
        asyncio.create_task(example_backend_orchestrator())
    ]
    
    try:
        # Run for a limited time for demo
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=60)
    except asyncio.TimeoutError:
        logger.info("Example completed")
    except KeyboardInterrupt:
        logger.info("Example interrupted")
    finally:
        # Cancel all tasks
        for task in tasks:
            task.cancel()
        
        # Wait for cleanup
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    # Run the example
    asyncio.run(run_example_system())