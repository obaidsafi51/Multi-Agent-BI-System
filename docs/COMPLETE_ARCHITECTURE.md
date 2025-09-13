# Complete Multi-Agent BI System Architecture

## System Overview

This is a complete multi-agent Business Intelligence system with specialized agents for NLP processing, data analysis, and visualization, orchestrated through a FastAPI backend and connected to TiDB via MCP (Model Context Protocol).

## Service Status ✅ All Services Running

```
NAME                     SERVICE           STATUS                    PORTS
agenticbi-frontend-1     frontend          Up 4 hours (healthy)      3000->3000
agenticbi-backend-1      backend           Up 50 minutes (healthy)   8001->8001
agenticbi-nlp-agent-1    nlp-agent         Up 4 hours (healthy)      8002->8001, 8012->8012
agenticbi-data-agent-1   data-agent        Up 39 minutes (healthy)   8004->8004
agenticbi-viz-agent-1    viz-agent         Up 6 minutes              8003->8003
tidb-mcp-server          tidb-mcp-server   Up 4 hours (healthy)      8000->8000
agenticbi-redis-1        redis             Up 4 hours (healthy)      6379->6379
agenticbi-rabbitmq-1     rabbitmq          Up 4 hours (healthy)      5672->5672, 15672->15672
```

## Architecture Layers

### 1. Frontend Layer (Port 3000)

- **Next.js Frontend**: React-based web interface
- **Purpose**: User interaction, query input, results display
- **Dependencies**: Backend API (8001)

### 2. Backend Layer (Port 8001)

- **FastAPI Backend**: Main orchestration service
- **Purpose**: API gateway, agent coordination, MCP client
- **Key Endpoints**:
  - `/api/databases` - List databases via MCP
  - `/api/select-database` - Select database and get schema
  - `/api/query` - Process NL queries through agents
- **Dependencies**: All agents + TiDB MCP Server

### 3. Agent Layer (Ports 8002, 8003, 8004)

- **NLP Agent (8002)**: Natural language processing
  - Purpose: Query understanding, SQL generation
  - Features: Advanced caching, context management
- **Data Agent (8004)**: Data processing and analysis
  - Purpose: Execute queries, data transformation
  - Features: Database connections, result processing
- **Viz Agent (8003)**: Visualization generation
  - Purpose: Chart creation, data visualization
  - Features: Plotly/matplotlib integration

### 4. Data Layer

- **TiDB MCP Server (8000)**: Database interface
  - Purpose: MCP protocol implementation for TiDB
  - Features: Database discovery, schema management
- **Redis Cache (6379)**: Distributed caching
  - Purpose: Session storage, query caching
  - Used by: All agents for performance optimization

### 5. Messaging Layer

- **RabbitMQ (5672, 15672)**: Message queue
  - Purpose: Pub/sub communication between agents
  - Features: Reliable message delivery, management UI

## Data Flow Architecture

### Query Processing Flow

1. **Frontend** → User enters natural language query
2. **Backend** → Receives query, coordinates agent workflow
3. **NLP Agent** → Processes query, generates SQL
4. **Data Agent** → Executes SQL via MCP server
5. **Viz Agent** → Creates visualizations from results
6. **Backend** → Aggregates results, returns to frontend
7. **Frontend** → Displays results and visualizations

### Database Operations Flow

1. **Frontend** → Requests database list on load
2. **Backend** → Uses MCP client to discover databases
3. **TiDB MCP Server** → Returns available databases
4. **Backend** → Caches results in Redis
5. **Frontend** → User selects database
6. **Backend** → Fetches schema via MCP, caches in Redis

## Key Integrations Fixed

### ✅ Backend MCP Integration

- Fixed `backend/main.py` database endpoints
- Updated `backend/mcp_client.py` with proper async methods
- Resolved response format mismatches

### ✅ Agent Communication

- All agents use Redis for caching
- RabbitMQ for async messaging between agents
- Proper health check implementations

### ✅ Missing Services Built

- Data Agent: Built and healthy (39 minutes uptime)
- Viz Agent: Built and running (6 minutes uptime)

## Performance Optimizations

### Caching Strategy

- **Redis**: Session data, query results, schema cache
- **NLP Agent**: Advanced query pattern caching
- **Backend**: Database list and schema caching

### Load Distribution

- **Horizontal scaling**: Multiple agent instances possible
- **Async processing**: Non-blocking agent communication
- **Health monitoring**: All services have health checks

## Network Architecture

```
External Traffic → Frontend (3000)
                     ↓
                Backend (8001) ←→ Redis (6379)
                     ↓
    ┌────────────────┼────────────────┐
    ↓                ↓                ↓
NLP Agent      Data Agent      Viz Agent
  (8002)         (8004)         (8003)
    ↓                ↓                ↓
    └────────── RabbitMQ (5672) ─────┘
                     ↑
                TiDB MCP Server (8000)
                     ↓
                TiDB Cloud Database
```

## Security & Reliability

### Health Monitoring

- All services implement `/health` endpoints
- Docker health checks every 30 seconds
- Service dependency management

### Error Handling

- Graceful degradation when agents unavailable
- Proper error propagation through layers
- Retry mechanisms for network operations

### Configuration Management

- Environment-based configuration
- Secure credential management
- Service discovery through Docker networking

## Next Steps for Optimization

1. **Load Testing**: Verify performance under concurrent users
2. **Monitoring**: Add logging and metrics collection
3. **Security**: Implement authentication and authorization
4. **Scalability**: Container orchestration with Kubernetes
5. **CI/CD**: Automated testing and deployment pipelines

## Service Dependencies

```
Frontend depends on: Backend
Backend depends on: NLP Agent, Data Agent, Viz Agent, TiDB MCP Server, Redis
All Agents depend on: Redis, RabbitMQ
TiDB MCP Server depends on: TiDB Cloud Database
```

This architecture provides a robust, scalable, and maintainable multi-agent BI system with proper separation of concerns and optimized data flow.
