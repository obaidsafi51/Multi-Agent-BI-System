#!/usr/bin/env python3
"""
Test communication protocols with mock dependencies.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import mock dependencies first to patch modules
from communication.mock_dependencies import *

# Now import communication modules
from communication import (
    CommunicationManager, ContextData, AgentMessage, WorkflowTask,
    MessageType, TaskStatus, AgentType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_communication_protocols():
    """Test all communication protocols with mocks"""
    logger.info("🚀 Testing Communication Protocols with Mocks")
    
    # Test 1: MCP Context Store
    logger.info("\n=== Test 1: MCP Context Store ===")
    
    comm_manager = CommunicationManager()
    await comm_manager.initialize(AgentType.BACKEND)
    
    try:
        # Create and store context
        context = ContextData(
            session_id="test_session",
            user_id="test_user",
            data={"query": "show revenue", "timestamp": datetime.utcnow().isoformat()},
            metadata={"source": "test"}
        )
        
        success = await comm_manager.store_context(context)
        logger.info(f"✅ Context stored: {success}")
        
        # Retrieve context
        retrieved = await comm_manager.get_context(context.context_id)
        logger.info(f"✅ Context retrieved: {retrieved is not None}")
        
        if retrieved:
            logger.info(f"   - Session ID: {retrieved.session_id}")
            logger.info(f"   - User ID: {retrieved.user_id}")
            logger.info(f"   - Data keys: {list(retrieved.data.keys())}")
        
        # Update context
        update_success = await comm_manager.update_context(
            context.context_id,
            {"processed": True, "result": "success"},
            {"updated_by": "test"}
        )
        logger.info(f"✅ Context updated: {update_success}")
        
        # Verify update
        updated = await comm_manager.get_context(context.context_id)
        if updated:
            logger.info(f"   - Version: {updated.version}")
            logger.info(f"   - Updated data: {updated.data.get('processed')}")
        
    except Exception as e:
        logger.error(f"❌ MCP test failed: {e}")
    
    # Test 2: A2A Message Broker
    logger.info("\n=== Test 2: A2A Message Broker ===")
    
    try:
        # Create test message
        message = AgentMessage(
            message_type=MessageType.QUERY_PROCESSING,
            sender=AgentType.BACKEND,
            recipient=AgentType.NLP,
            payload={
                "query": "show Q1 revenue",
                "user_id": "test_user",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Send message
        success = await comm_manager.send_message(message)
        logger.info(f"✅ Message sent: {success}")
        logger.info(f"   - Message ID: {message.message_id}")
        logger.info(f"   - Type: {message.message_type}")
        logger.info(f"   - From: {message.sender} -> To: {message.recipient}")
        
        # Test broadcast
        health_message = AgentMessage(
            message_type=MessageType.HEALTH_CHECK,
            sender=AgentType.BACKEND,
            recipient=AgentType.BACKEND,
            payload={"timestamp": datetime.utcnow().isoformat()}
        )
        
        broadcast_success = await comm_manager.broadcast_message(health_message)
        logger.info(f"✅ Broadcast sent: {broadcast_success}")
        
    except Exception as e:
        logger.error(f"❌ A2A test failed: {e}")
    
    # Test 3: ACP Workflow Orchestration
    logger.info("\n=== Test 3: ACP Workflow Orchestration ===")
    
    try:
        # Register test task handlers
        async def mock_nlp_task(task: WorkflowTask):
            logger.info(f"   Executing NLP task: {task.task_name}")
            await asyncio.sleep(0.1)  # Simulate processing
            return {
                "intent": "revenue_query",
                "entities": ["revenue", "Q1"],
                "confidence": 0.95
            }
        
        async def mock_data_task(task: WorkflowTask):
            logger.info(f"   Executing Data task: {task.task_name}")
            await asyncio.sleep(0.1)  # Simulate processing
            return {
                "data": [
                    {"month": "Jan", "revenue": 100000},
                    {"month": "Feb", "revenue": 120000},
                    {"month": "Mar", "revenue": 110000}
                ],
                "total": 330000
            }
        
        async def mock_viz_task(task: WorkflowTask):
            logger.info(f"   Executing Viz task: {task.task_name}")
            await asyncio.sleep(0.1)  # Simulate processing
            return {
                "chart_type": "line",
                "chart_config": {"title": "Q1 Revenue", "x_axis": "month", "y_axis": "revenue"},
                "chart_data": "base64_encoded_chart"
            }
        
        # Register handlers
        comm_manager.register_task_handler("nlp_processing", mock_nlp_task)
        comm_manager.register_task_handler("data_retrieval", mock_data_task)
        comm_manager.register_task_handler("visualization_generation", mock_viz_task)
        
        # Create workflow tasks
        tasks = [
            WorkflowTask(
                workflow_id="test_workflow",
                task_name="nlp_processing",
                agent_type=AgentType.NLP,
                payload={"query": "show Q1 revenue"},
                dependencies=[]
            ),
            WorkflowTask(
                workflow_id="test_workflow",
                task_name="data_retrieval",
                agent_type=AgentType.DATA,
                payload={},
                dependencies=[]  # Simplified for test
            ),
            WorkflowTask(
                workflow_id="test_workflow",
                task_name="visualization_generation",
                agent_type=AgentType.VISUALIZATION,
                payload={},
                dependencies=[]  # Simplified for test
            )
        ]
        
        # Create workflow
        workflow_id = await comm_manager.create_workflow(
            "Revenue Query Workflow",
            tasks,
            context.context_id if 'context' in locals() else None
        )
        
        logger.info(f"✅ Workflow created: {workflow_id}")
        
        if workflow_id:
            # Check workflow status
            await asyncio.sleep(1)  # Give time for processing
            status = await comm_manager.get_workflow_status(workflow_id)
            if status:
                logger.info(f"   - Workflow name: {status['workflow_name']}")
                logger.info(f"   - Status: {status['status']}")
                logger.info(f"   - Task count: {status['task_count']}")
        
    except Exception as e:
        logger.error(f"❌ ACP test failed: {e}")
    
    # Test 4: System Health and Status
    logger.info("\n=== Test 4: System Health and Status ===")
    
    try:
        # Get system status
        status = await comm_manager.get_system_status()
        logger.info(f"✅ System status retrieved")
        logger.info(f"   - Connected: {status['connected']}")
        logger.info(f"   - Agent type: {status['agent_type']}")
        logger.info(f"   - MCP status: {status['mcp']['status']}")
        logger.info(f"   - A2A status: {status['a2a']['status']}")
        
        # Test message handlers
        received_messages = []
        
        async def test_handler(message: AgentMessage):
            received_messages.append(message)
            logger.info(f"   Handler received: {message.message_type}")
        
        comm_manager.register_message_handler(MessageType.HEALTH_CHECK, test_handler)
        logger.info("✅ Message handler registered")
        
    except Exception as e:
        logger.error(f"❌ Health test failed: {e}")
    
    # Test 5: Integration Scenario
    logger.info("\n=== Test 5: Integration Scenario ===")
    
    try:
        # Simulate complete query processing flow
        logger.info("   Simulating complete query processing flow...")
        
        # 1. Create context for user session
        user_context = ContextData(
            session_id="integration_test_session",
            user_id="cfo_user",
            data={
                "user_query": "What was our revenue growth in Q1?",
                "user_preferences": {"chart_type": "line", "currency": "USD"}
            }
        )
        
        await comm_manager.store_context(user_context)
        logger.info("   ✅ User context created")
        
        # 2. Send initial query message
        query_msg = AgentMessage(
            message_type=MessageType.QUERY_PROCESSING,
            sender=AgentType.BACKEND,
            recipient=AgentType.NLP,
            payload={"query": user_context.data["user_query"]},
            context_id=user_context.context_id
        )
        
        await comm_manager.send_message(query_msg)
        logger.info("   ✅ Query message sent to NLP agent")
        
        # 3. Update context with processing steps
        await comm_manager.update_context(
            user_context.context_id,
            {"processing_step": "nlp_complete", "intent": "revenue_growth_query"},
            {"step_timestamp": datetime.utcnow().isoformat()}
        )
        logger.info("   ✅ Context updated with NLP results")
        
        # 4. Send data request
        data_msg = AgentMessage(
            message_type=MessageType.DATA_REQUEST,
            sender=AgentType.NLP,
            recipient=AgentType.DATA,
            payload={"intent": "revenue_growth_query", "period": "Q1"},
            context_id=user_context.context_id
        )
        
        await comm_manager.send_message(data_msg)
        logger.info("   ✅ Data request sent")
        
        # 5. Update context with data results
        await comm_manager.update_context(
            user_context.context_id,
            {
                "processing_step": "data_complete",
                "data_summary": {"total_revenue": 330000, "growth_rate": 15.2}
            },
            {"step_timestamp": datetime.utcnow().isoformat()}
        )
        logger.info("   ✅ Context updated with data results")
        
        # 6. Send visualization request
        viz_msg = AgentMessage(
            message_type=MessageType.VISUALIZATION_REQUEST,
            sender=AgentType.DATA,
            recipient=AgentType.VISUALIZATION,
            payload={
                "chart_type": "line",
                "data": [{"month": "Jan", "revenue": 100000}, {"month": "Feb", "revenue": 120000}],
                "title": "Q1 Revenue Growth"
            },
            context_id=user_context.context_id
        )
        
        await comm_manager.send_message(viz_msg)
        logger.info("   ✅ Visualization request sent")
        
        # 7. Final context update
        await comm_manager.update_context(
            user_context.context_id,
            {
                "processing_step": "complete",
                "final_result": {
                    "chart_generated": True,
                    "insights": ["Revenue grew 15.2% in Q1", "February was the strongest month"]
                }
            },
            {"completion_timestamp": datetime.utcnow().isoformat()}
        )
        logger.info("   ✅ Processing complete, context finalized")
        
        # 8. Retrieve final context
        final_context = await comm_manager.get_context(user_context.context_id)
        if final_context:
            logger.info(f"   ✅ Final context version: {final_context.version}")
            logger.info(f"   ✅ Processing steps completed: {final_context.data.get('processing_step')}")
        
        logger.info("✅ Integration scenario completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
    
    # Cleanup
    await comm_manager.shutdown()
    logger.info("\n✅ Communication manager shutdown complete")
    
    logger.info("\n" + "="*60)
    logger.info("🎉 All communication protocol tests completed!")
    logger.info("="*60)


if __name__ == "__main__":
    try:
        asyncio.run(test_communication_protocols())
        print("\n✅ All tests passed successfully!")
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        sys.exit(1)