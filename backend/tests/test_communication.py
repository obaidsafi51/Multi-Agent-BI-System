"""
Integration tests for communication protocols (MCP, A2A, ACP).
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any
import redis.asyncio as redis
from unittest.mock import AsyncMock, MagicMock, patch

from backend.communication import (
    MCPContextStore, A2AMessageBroker, ACPOrchestrator, MessageRouter,
    ContextData, AgentMessage, WorkflowTask, MessageType, TaskStatus, AgentType
)


@pytest.fixture
async def redis_client():
    """Redis client fixture for testing"""
    client = redis.from_url("redis://localhost:6379/15", decode_responses=True)  # Use test DB
    yield client
    # Cleanup
    await client.flushdb()
    await client.close()


@pytest.fixture
async def mcp_store(redis_client):
    """MCP context store fixture"""
    store = MCPContextStore("redis://localhost:6379/15")
    await store.connect()
    yield store
    await store.disconnect()


@pytest.fixture
def mock_rabbitmq():
    """Mock RabbitMQ connection for testing"""
    with patch('aio_pika.connect_robust') as mock_connect:
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()
        
        mock_connect.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel
        mock_channel.declare_exchange.return_value = mock_exchange
        mock_channel.declare_queue.return_value = mock_queue
        
        yield {
            'connection': mock_connection,
            'channel': mock_channel,
            'exchange': mock_exchange,
            'queue': mock_queue
        }


@pytest.fixture
async def a2a_broker(mock_rabbitmq):
    """A2A message broker fixture"""
    broker = A2AMessageBroker("amqp://guest:guest@localhost:5672/")
    await broker.connect(AgentType.BACKEND)
    yield broker
    await broker.disconnect()


@pytest.fixture
def mock_celery():
    """Mock Celery app for testing"""
    with patch('celery.Celery') as mock_celery_class:
        mock_app = MagicMock()
        mock_celery_class.return_value = mock_app
        
        # Mock configuration
        mock_app.conf.update = MagicMock()
        mock_app.task = MagicMock()
        mock_app.control.inspect.return_value.stats.return_value = {"worker1": {}}
        mock_app.control.inspect.return_value.active.return_value = {"worker1": []}
        
        yield mock_app


@pytest.fixture
async def acp_orchestrator(mock_celery, mcp_store, a2a_broker):
    """ACP orchestrator fixture"""
    orchestrator = ACPOrchestrator(
        broker_url="redis://localhost:6379/1",
        backend_url="redis://localhost:6379/2",
        mcp_store=mcp_store,
        a2a_broker=a2a_broker
    )
    yield orchestrator


class TestMCPContextStore:
    """Test MCP context store functionality"""
    
    async def test_store_and_retrieve_context(self, mcp_store):
        """Test storing and retrieving context data"""
        # Create test context
        context = ContextData(
            session_id="test_session",
            user_id="test_user",
            data={"query": "show revenue", "results": [1, 2, 3]},
            metadata={"source": "test"}
        )
        
        # Store context
        success = await mcp_store.store_context(context)
        assert success
        
        # Retrieve context
        retrieved = await mcp_store.get_context(context.context_id)
        assert retrieved is not None
        assert retrieved.session_id == "test_session"
        assert retrieved.user_id == "test_user"
        assert retrieved.data["query"] == "show revenue"
        assert retrieved.metadata["source"] == "test"
    
    async def test_update_context(self, mcp_store):
        """Test updating existing context"""
        # Create and store context
        context = ContextData(
            session_id="test_session",
            data={"initial": "data"}
        )
        await mcp_store.store_context(context)
        
        # Update context
        success = await mcp_store.update_context(
            context.context_id,
            {"updated": "data", "new_field": "value"},
            {"updated_by": "test"}
        )
        assert success
        
        # Verify update
        updated = await mcp_store.get_context(context.context_id)
        assert updated.data["initial"] == "data"
        assert updated.data["updated"] == "data"
        assert updated.data["new_field"] == "value"
        assert updated.metadata["updated_by"] == "test"
        assert updated.version == 2
    
    async def test_session_contexts(self, mcp_store):
        """Test retrieving contexts by session"""
        session_id = "test_session"
        
        # Create multiple contexts for same session
        contexts = []
        for i in range(3):
            context = ContextData(
                session_id=session_id,
                data={"index": i}
            )
            await mcp_store.store_context(context)
            contexts.append(context)
        
        # Retrieve session contexts
        session_contexts = await mcp_store.get_session_contexts(session_id)
        assert len(session_contexts) == 3
        
        # Verify all contexts belong to session
        for ctx in session_contexts:
            assert ctx.session_id == session_id
    
    async def test_context_expiration(self, mcp_store):
        """Test context expiration with TTL"""
        context = ContextData(
            session_id="test_session",
            data={"test": "data"}
        )
        
        # Store with short TTL
        success = await mcp_store.store_context(context, ttl=1)
        assert success
        
        # Verify context exists
        retrieved = await mcp_store.get_context(context.context_id)
        assert retrieved is not None
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Verify context expired
        expired = await mcp_store.get_context(context.context_id)
        assert expired is None
    
    async def test_delete_context(self, mcp_store):
        """Test deleting context"""
        context = ContextData(
            session_id="test_session",
            user_id="test_user",
            data={"test": "data"}
        )
        await mcp_store.store_context(context)
        
        # Verify context exists
        retrieved = await mcp_store.get_context(context.context_id)
        assert retrieved is not None
        
        # Delete context
        success = await mcp_store.delete_context(context.context_id)
        assert success
        
        # Verify context deleted
        deleted = await mcp_store.get_context(context.context_id)
        assert deleted is None


class TestA2AMessageBroker:
    """Test A2A message broker functionality"""
    
    async def test_send_message(self, a2a_broker, mock_rabbitmq):
        """Test sending message between agents"""
        message = AgentMessage(
            message_type=MessageType.QUERY_PROCESSING,
            sender=AgentType.BACKEND,
            recipient=AgentType.NLP,
            payload={"query": "show revenue"}
        )
        
        success = await a2a_broker.send_message(message)
        assert success
        
        # Verify exchange publish was called
        mock_rabbitmq['exchange'].publish.assert_called_once()
    
    async def test_broadcast_message(self, a2a_broker, mock_rabbitmq):
        """Test broadcasting message to all agents"""
        message = AgentMessage(
            message_type=MessageType.HEALTH_CHECK,
            sender=AgentType.BACKEND,
            recipient=AgentType.BACKEND,
            payload={"timestamp": datetime.utcnow().isoformat()}
        )
        
        success = await a2a_broker.broadcast_message(message)
        assert success
        
        # Verify broadcast publish was called
        mock_rabbitmq['exchange'].publish.assert_called_once()
        call_args = mock_rabbitmq['exchange'].publish.call_args
        assert call_args[1]['routing_key'] == "agent.broadcast"
    
    async def test_register_handler(self, a2a_broker):
        """Test registering message handler"""
        async def test_handler(message: AgentMessage):
            return {"processed": True}
        
        a2a_broker.register_handler(MessageType.QUERY_PROCESSING, test_handler)
        
        # Verify handler registered
        assert MessageType.QUERY_PROCESSING in a2a_broker._message_handlers
        assert a2a_broker._message_handlers[MessageType.QUERY_PROCESSING] == test_handler
    
    async def test_health_check(self, a2a_broker):
        """Test health check functionality"""
        health_response = await a2a_broker.health_check()
        
        assert health_response.agent_type == AgentType.BACKEND
        assert health_response.status in ["healthy", "unhealthy"]
        assert isinstance(health_response.details, dict)


class TestACPOrchestrator:
    """Test ACP orchestrator functionality"""
    
    async def test_create_workflow(self, acp_orchestrator):
        """Test creating workflow"""
        tasks = [
            WorkflowTask(
                workflow_id="test_workflow",
                task_name="task1",
                agent_type=AgentType.NLP,
                payload={"data": "test"}
            ),
            WorkflowTask(
                workflow_id="test_workflow",
                task_name="task2",
                agent_type=AgentType.DATA,
                payload={"data": "test"},
                dependencies=["task1"]
            )
        ]
        
        workflow = await acp_orchestrator.create_workflow(
            "test_workflow",
            tasks
        )
        
        assert workflow.workflow_name == "test_workflow"
        assert len(workflow.tasks) == 2
        assert workflow.status == TaskStatus.PENDING
    
    async def test_register_task_handler(self, acp_orchestrator):
        """Test registering task handler"""
        async def test_handler(task: WorkflowTask):
            return {"result": "success"}
        
        acp_orchestrator.register_task_handler("test_task", test_handler)
        
        # Verify handler registered
        assert "test_task" in acp_orchestrator._task_handlers
        assert acp_orchestrator._task_handlers["test_task"] == test_handler
    
    async def test_workflow_status(self, acp_orchestrator):
        """Test getting workflow status"""
        # Create workflow
        tasks = [
            WorkflowTask(
                workflow_id="test_workflow",
                task_name="task1",
                agent_type=AgentType.NLP,
                payload={"data": "test"}
            )
        ]
        
        workflow = await acp_orchestrator.create_workflow(
            "test_workflow",
            tasks
        )
        
        # Get status
        status = await acp_orchestrator.get_workflow_status(workflow.workflow_id)
        
        assert status is not None
        assert status["workflow_id"] == workflow.workflow_id
        assert status["workflow_name"] == "test_workflow"
        assert status["status"] == TaskStatus.PENDING
        assert status["task_count"] == 1


class TestMessageRouter:
    """Test message routing functionality"""
    
    @pytest.fixture
    async def message_router(self, mcp_store, a2a_broker, acp_orchestrator):
        """Message router fixture"""
        return MessageRouter(mcp_store, a2a_broker, acp_orchestrator)
    
    async def test_route_message(self, message_router, mock_rabbitmq):
        """Test routing message to appropriate agents"""
        message = AgentMessage(
            message_type=MessageType.QUERY_PROCESSING,
            sender=AgentType.BACKEND,
            recipient=AgentType.NLP,
            payload={"query": "show revenue"}
        )
        
        success = await message_router.route_message(message)
        assert success
        
        # Verify message was sent
        mock_rabbitmq['exchange'].publish.assert_called()
    
    async def test_transform_and_route(self, message_router):
        """Test transforming message and routing"""
        message = AgentMessage(
            message_type=MessageType.QUERY_PROCESSING,
            sender=AgentType.BACKEND,
            recipient=AgentType.NLP,
            payload={"query": "show revenue", "user_id": "test_user"}
        )
        
        success = await message_router.transform_and_route(message, "query_to_workflow")
        assert success
    
    async def test_broadcast_health_check(self, message_router, mock_rabbitmq):
        """Test broadcasting health check"""
        results = await message_router.broadcast_health_check()
        
        assert isinstance(results, dict)
        assert len(results) > 0
        
        # Verify broadcast was sent
        mock_rabbitmq['exchange'].publish.assert_called()
    
    async def test_routing_stats(self, message_router):
        """Test getting routing statistics"""
        stats = await message_router.get_routing_stats()
        
        assert "transformation_rules" in stats
        assert "routing_rules" in stats
        assert "registered_message_types" in stats
        assert "target_agents" in stats
        assert isinstance(stats["transformation_rules"], int)
        assert isinstance(stats["routing_rules"], int)


class TestIntegrationScenarios:
    """Test end-to-end integration scenarios"""
    
    @pytest.fixture
    async def full_system(self, mcp_store, a2a_broker, acp_orchestrator):
        """Full system integration fixture"""
        router = MessageRouter(mcp_store, a2a_broker, acp_orchestrator)
        
        # Register test handlers
        async def nlp_handler(task: WorkflowTask):
            return {"intent": "revenue_query", "entities": ["revenue", "Q1"]}
        
        async def data_handler(task: WorkflowTask):
            return {"data": [{"month": "Jan", "revenue": 100000}]}
        
        async def viz_handler(task: WorkflowTask):
            return {"chart_type": "line", "chart_data": "base64_encoded"}
        
        acp_orchestrator.register_task_handler("nlp_processing", nlp_handler)
        acp_orchestrator.register_task_handler("data_retrieval", data_handler)
        acp_orchestrator.register_task_handler("visualization_generation", viz_handler)
        
        return {
            'mcp_store': mcp_store,
            'a2a_broker': a2a_broker,
            'acp_orchestrator': acp_orchestrator,
            'router': router
        }
    
    async def test_query_processing_workflow(self, full_system):
        """Test complete query processing workflow"""
        # Create context
        context = ContextData(
            session_id="test_session",
            user_id="test_user",
            data={"query": "show Q1 revenue"}
        )
        await full_system['mcp_store'].store_context(context)
        
        # Create query message
        query_message = AgentMessage(
            message_type=MessageType.QUERY_PROCESSING,
            sender=AgentType.BACKEND,
            recipient=AgentType.NLP,
            payload={
                "query": "show Q1 revenue",
                "user_id": "test_user"
            },
            context_id=context.context_id
        )
        
        # Process through workflow
        success = await full_system['router'].transform_and_route(
            query_message, 
            "query_to_workflow"
        )
        assert success
        
        # Verify context was updated
        updated_context = await full_system['mcp_store'].get_context(context.context_id)
        assert updated_context is not None
    
    async def test_error_handling_and_retry(self, full_system):
        """Test error handling and retry mechanisms"""
        # Register failing handler
        async def failing_handler(task: WorkflowTask):
            if task.retry_count < 2:
                raise Exception("Simulated failure")
            return {"result": "success_after_retry"}
        
        full_system['acp_orchestrator'].register_task_handler("failing_task", failing_handler)
        
        # Create task that will fail initially
        task = WorkflowTask(
            workflow_id="test_workflow",
            task_name="failing_task",
            agent_type=AgentType.NLP,
            payload={"data": "test"},
            max_retries=3
        )
        
        workflow = await full_system['acp_orchestrator'].create_workflow(
            "error_test_workflow",
            [task]
        )
        
        # Execute workflow (would normally handle retries)
        task_id = await full_system['acp_orchestrator'].execute_workflow(workflow.workflow_id)
        assert task_id is not None
    
    async def test_context_persistence_across_agents(self, full_system):
        """Test context persistence across agent communications"""
        # Create context with initial data
        context = ContextData(
            session_id="test_session",
            user_id="test_user",
            data={"step": "initial"}
        )
        await full_system['mcp_store'].store_context(context)
        
        # Simulate agent updating context
        await full_system['mcp_store'].update_context(
            context.context_id,
            {"step": "nlp_processed", "intent": "revenue_query"},
            {"processed_by": "nlp_agent"}
        )
        
        # Simulate another agent updating context
        await full_system['mcp_store'].update_context(
            context.context_id,
            {"step": "data_retrieved", "results": [1, 2, 3]},
            {"processed_by": "data_agent"}
        )
        
        # Verify final context state
        final_context = await full_system['mcp_store'].get_context(context.context_id)
        assert final_context.data["step"] == "data_retrieved"
        assert final_context.data["intent"] == "revenue_query"
        assert final_context.data["results"] == [1, 2, 3]
        assert final_context.version == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])