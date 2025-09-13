# Multi-Agent BI System - Current Architecture Diagram

## System Overview

This diagram shows the complete multi-agent BI system with all services now operational (similar to your reference diagram but updated to reflect current state).

## Architecture Flow

### 🎯 Main Data Flow

```
User → Frontend → Backend → [NLP + Data + Viz Agents] → TiDB MCP Server → TiDB Cloud
```

### 🔄 Supporting Infrastructure

- **Redis Cache**: Used by all agents and backend for performance
- **RabbitMQ**: Pub/Sub messaging between agents for coordination

## Service Status Update

✅ **All services are now running** (vs your original diagram showing "Viz Agent (Missing)")

| Service         | Status     | Port       | Description                          |
| --------------- | ---------- | ---------- | ------------------------------------ |
| Frontend        | ✅ Healthy | 3000       | React web interface                  |
| Backend         | ✅ Healthy | 8001       | FastAPI orchestrator                 |
| NLP Agent       | ✅ Healthy | 8002       | Query understanding & SQL generation |
| Data Agent      | ✅ Healthy | 8004       | SQL execution & data processing      |
| Viz Agent       | ✅ Running | 8003       | Chart generation & visualization     |
| TiDB MCP Server | ✅ Healthy | 8000       | Database interface with MCP protocol |
| Redis           | ✅ Healthy | 6379       | Distributed caching                  |
| RabbitMQ        | ✅ Healthy | 5672/15672 | Message queue & management           |

## Key Differences from Original Diagram

### ✅ Fixed Issues

1. **Viz Agent**: No longer missing - now built and running
2. **Data Agent**: Added as a new service for SQL execution
3. **Infrastructure**: Added Redis and RabbitMQ for proper multi-agent coordination
4. **Backend Integration**: Fixed MCP client integration for database operations

### 🔧 Architecture Improvements

- **Separation of Concerns**: Each agent has specific responsibilities
- **Caching Layer**: Redis provides distributed caching for all services
- **Message Queue**: RabbitMQ enables reliable async communication
- **Health Monitoring**: All services have proper health checks

## Data Processing Workflow

1. **Query Input**: User enters natural language query in frontend
2. **Orchestration**: Backend coordinates the multi-agent workflow
3. **NLP Processing**: NLP agent understands query and generates SQL
4. **Data Execution**: Data agent executes SQL via MCP server
5. **Visualization**: Viz agent creates charts and graphs
6. **Result Display**: Backend aggregates results and sends to frontend

## Technical Implementation

### MCP Integration

- Backend uses MCP client to communicate with TiDB MCP Server
- Proper async methods for database discovery and operations
- Fixed response format handling

### Agent Communication

- All agents use Redis for session storage and caching
- RabbitMQ provides pub/sub messaging for coordination
- Docker networking enables service discovery

### Performance Optimizations

- Redis caching reduces database load
- Async processing prevents blocking operations
- Health checks ensure system reliability

This architecture now provides a complete, scalable, and maintainable multi-agent BI system with all components operational and properly integrated.
