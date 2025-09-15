# Communication Protocols Implementation

This module implements the three communication protocols for the AGENT BI system:

- **MCP (Model Context Protocol)**: Redis-based context store with JSON serialization and session management
- **A2A (Agent-to-Agent Protocol)**: RabbitMQ message broker with topic exchanges and routing
- **ACP (Agent Communication Protocol)**: Celery workflow orchestrator with task queues and error handling

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Context   │    │  A2A Message    │    │ ACP Workflow    │
│     Store       │    │    Broker       │    │  Orchestrator   │
│   (Redis)       │    │  (RabbitMQ)     │    │   (Celery)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Communication   │
                    │    Manager      │
                    │  (Coordinator)  │
                    └─────────────────┘
```

## Components

### 1. MCP Context Store (`mcp.py`)

Redis-based context store for sharing state across agents.

**Features:**

- JSON serialization of context data
- Session and user-based context indexing
- TTL-based context expiration
- Version control for conflict resolution
- Automatic cleanup of expired contexts

**Usage:**

```python
from communication import MCPContextStore, ContextData

# Initialize store
mcp_store = MCPContextStore("redis://localhost:6379")
await mcp_store.connect()

# Store context
context = ContextData(
    session_id="user_session_123",
    user_id="cfo_user",
    data={"query": "show revenue", "results": [...]},
    metadata={"source": "nlp_agent"}
)
await mcp_store.store_context(context)

# Retrieve context
retrieved = await mcp_store.get_context(context.context_id)

# Update context
await mcp_store.update_context(
    context.context_id,
    {"processed": True},
    {"updated_by": "data_agent"}
)
```

### 2. A2A Message Broker (`a2a.py`)

RabbitMQ-based message broker for direct agent communication.

**Features:**

- Topic-based message routing
- Request-response patterns
- Message broadcasting
- Automatic retry mechanisms
- Dead letter queue handling

**Usage:**

```python
from communication import A2AMessageBroker, AgentMessage, MessageType, AgentType

# Initialize broker
a2a_broker = A2AMessageBroker("amqp://guest:guest@localhost:5672/")
await a2a_broker.connect(AgentType.BACKEND)

# Register message handler
async def query_handler(message: AgentMessage):
    print(f"Received query: {message.payload['query']}")

a2a_broker.register_handler(MessageType.QUERY_PROCESSING, query_handler)

# Send message
message = AgentMessage(
    message_type=MessageType.QUERY_PROCESSING,
    sender=AgentType.BACKEND,
    recipient=AgentType.NLP,
    payload={"query": "show Q1 revenue"}
)
await a2a_broker.send_message(message)

# Start consuming
await a2a_broker.start_consuming()
```

### 3. ACP Workflow Orchestrator (`acp.py`)

Celery-based workflow orchestrator for complex multi-agent tasks.

**Features:**

- Task dependency management
- Parallel and sequential execution
- Automatic retry with exponential backoff
- Workflow status monitoring
- Error handling and recovery

**Usage:**

```python
from communication import ACPOrchestrator, WorkflowTask, AgentType

# Initialize orchestrator
acp_orchestrator = ACPOrchestrator(
    broker_url="redis://localhost:6379/1",
    backend_url="redis://localhost:6379/2"
)

# Register task handler
async def nlp_processing_task(task: WorkflowTask):
    query = task.payload.get('query')
    # Process query...
    return {"intent": "revenue_query", "entities": ["revenue", "Q1"]}

acp_orchestrator.register_task_handler("nlp_processing", nlp_processing_task)

# Create workflow
tasks = [
    WorkflowTask(
        workflow_id="query_workflow",
        task_name="nlp_processing",
        agent_type=AgentType.NLP,
        payload={"query": "show Q1 revenue"},
        dependencies=[]
    ),
    WorkflowTask(
        workflow_id="query_workflow",
        task_name="data_retrieval",
        agent_type=AgentType.DATA,
        payload={},
        dependencies=["nlp_task_id"]
    )
]

workflow = await acp_orchestrator.create_workflow("Query Processing", tasks)
await acp_orchestrator.execute_workflow(workflow.workflow_id)
```

### 4. Message Router (`router.py`)

Intelligent message routing and transformation between protocols.

**Features:**

- Message type-based routing rules
- Message transformation pipelines
- Protocol bridging (A2A ↔ ACP)
- Context-aware routing
- Health check broadcasting

**Usage:**

```python
from communication import MessageRouter

router = MessageRouter(mcp_store, a2a_broker, acp_orchestrator)

# Route message
await router.route_message(message)

# Transform and route
await router.transform_and_route(message, "query_to_workflow")

# Broadcast health check
health_results = await router.broadcast_health_check()
```

### 5. Communication Manager (`manager.py`)

High-level coordinator that manages all communication protocols.

**Features:**

- Unified interface for all protocols
- Automatic connection management
- Health monitoring and reconnection
- Configuration management
- Graceful shutdown handling

**Usage:**

```python
from communication import CommunicationManager, AgentType

# Initialize manager
comm_manager = CommunicationManager()
await comm_manager.initialize(AgentType.BACKEND)

# Use unified interface
await comm_manager.send_message(message)
await comm_manager.store_context(context)
workflow_id = await comm_manager.create_workflow("My Workflow", tasks)

# Get system status
status = await comm_manager.get_system_status()

# Shutdown
await comm_manager.shutdown()
```

## Data Models

### Core Models (`models.py`)

- **ContextData**: Session and user context with versioning
- **AgentMessage**: Inter-agent messages with routing metadata
- **WorkflowTask**: Task definitions with dependencies
- **WorkflowDefinition**: Complete workflow specifications
- **HealthCheckResponse**: Agent health status information

### Enums

- **MessageType**: Types of messages (QUERY_PROCESSING, DATA_REQUEST, etc.)
- **TaskStatus**: Task execution states (PENDING, RUNNING, SUCCESS, etc.)
- **AgentType**: Agent identifiers (NLP, DATA, VISUALIZATION, etc.)

## Configuration

### Environment Variables

```bash
# Redis (MCP Context Store)
REDIS_URL=redis://localhost:6379

# RabbitMQ (A2A Message Broker)
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Celery (ACP Orchestrator)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_BACKEND_URL=redis://localhost:6379/2
```

### Docker Compose Integration

The protocols integrate with the existing docker-compose.yml:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  rabbitmq:
    image: rabbitmq:3-management-alpine
    ports: ["5672:5672", "15672:15672"]

  backend:
    environment:
      - REDIS_URL=redis://redis:6379
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
```

## Error Handling and Fault Tolerance

### Retry Mechanisms

- **Exponential Backoff**: Automatic retry with increasing delays
- **Circuit Breaker**: Prevent cascade failures
- **Dead Letter Queues**: Handle permanently failed messages
- **Health Checks**: Monitor and recover from failures

### Error Types

1. **Connection Errors**: Redis/RabbitMQ connectivity issues
2. **Message Errors**: Malformed or undeliverable messages
3. **Task Errors**: Workflow task execution failures
4. **Context Errors**: Context corruption or expiration

## Testing

### Unit Tests (`tests/test_communication.py`)

Comprehensive test suite covering:

- MCP context store operations
- A2A message broker functionality
- ACP workflow orchestration
- Message routing and transformation
- Error handling and recovery

### Integration Tests

- End-to-end query processing workflows
- Cross-agent communication scenarios
- Context persistence across agents
- Health monitoring and recovery

### Running Tests

```bash
# With pytest (requires dependencies)
pytest tests/test_communication.py -v

# With mock dependencies
python test_communication_simple.py

# Integration test with mocks
python test_communication_with_mocks.py
```

## Performance Considerations

### Scalability

- **Horizontal Scaling**: Multiple agent instances with load balancing
- **Connection Pooling**: Efficient Redis and RabbitMQ connections
- **Message Batching**: Reduce network overhead
- **Context Caching**: Minimize Redis round trips

### Monitoring

- **Message Throughput**: Track messages per second
- **Context Usage**: Monitor context store size and TTL
- **Task Execution**: Workflow completion times
- **Error Rates**: Failed message and task percentages

## Security

### Authentication

- Redis AUTH for context store access
- RabbitMQ user credentials for message broker
- TLS encryption for production deployments

### Data Protection

- Context data encryption at rest
- Message payload validation
- Access control for sensitive operations

## Examples

See `example_usage.py` for complete examples of:

- Multi-agent query processing workflow
- Context sharing across agents
- Error handling and recovery
- Health monitoring and status reporting

## Dependencies

```toml
dependencies = [
    "redis>=5.0.1",           # MCP context store
    "aio-pika>=9.3.1",        # A2A message broker
    "celery>=5.3.4",          # ACP workflow orchestrator
    "kombu>=5.3.4",           # Celery message transport
    "pydantic>=2.8.0",        # Data models and validation
]
```

## Future Enhancements

- **Message Encryption**: End-to-end encryption for sensitive data
- **Advanced Routing**: ML-based intelligent message routing
- **Workflow Templates**: Reusable workflow patterns
- **Metrics Dashboard**: Real-time monitoring interface
- **Multi-tenancy**: Isolated contexts per organization
