# Docker Compose Merge Summary

## What Was Done

Successfully merged two separate Docker Compose files into one unified configuration:

### Before:

- **Main project**: `/docker-compose.yml` (Frontend, Backend, Agents, Redis, RabbitMQ)
- **TiDB MCP Server**: `/tidb-mcp-server/docker-compose.yml` (TiDB MCP Server, Redis)

### After:

- **Single file**: `/docker-compose.yml` (All services in one stack)
- **Backup**: `/tidb-mcp-server/docker-compose.yml.backup` (Original file preserved)

## Services Now Available in Single Stack

1. **frontend** - Next.js frontend (port 3000)
2. **backend** - FastAPI gateway (port 8000)
3. **nlp-agent** - NLP processing agent
4. **data-agent** - TiDB data integration agent
5. **viz-agent** - Visualization agent (port 8003)
6. **tidb-mcp-server** - TiDB MCP server (NEW)
7. **redis** - Redis cache and message store (port 6379)
8. **rabbitmq** - Message broker (ports 5672, 15672)

## Key Benefits

✅ **Single Network**: All services now share the `ai-cfo-network`  
✅ **Unified Environment**: One `.env` file for all services  
✅ **Simplified Deployment**: One `docker compose up` command  
✅ **Service Discovery**: All services can communicate via service names  
✅ **Resource Management**: Consolidated resource limits and monitoring

## Environment Variables Added

Added to `.env.example` for TiDB MCP Server:

```bash
# TiDB SSL Configuration
TIDB_SSL_CA=
TIDB_SSL_VERIFY_CERT=true
TIDB_SSL_VERIFY_IDENTITY=true

# MCP Server Configuration
MCP_SERVER_NAME=tidb-mcp-server
MCP_SERVER_VERSION=0.1.0
MCP_MAX_CONNECTIONS=10
MCP_REQUEST_TIMEOUT=30

# Cache Configuration
CACHE_ENABLED=true
CACHE_TTL_SECONDS=300
CACHE_MAX_SIZE=1000

# Security Configuration
MAX_QUERY_TIMEOUT=30
MAX_SAMPLE_ROWS=100
RATE_LIMIT_RPM=60

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# SSL Certificate Path
SSL_CERT_PATH=
```

## Usage

```bash
# Build all services
docker compose build

# Start all services
docker compose up -d

# View logs for specific service
docker compose logs tidb-mcp-server

# Scale specific service
docker compose up -d --scale tidb-mcp-server=2

# Stop all services
docker compose down
```

## Health Checks

- **tidb-mcp-server**: Configuration validation check
- **redis**: Redis ping check
- **rabbitmq**: RabbitMQ diagnostics check

## Network Communication

All services can now communicate via:

- `http://backend:8000` - Backend API
- `http://tidb-mcp-server:8080` - MCP Server (if exposed)
- `redis://redis:6379` - Redis cache
- `amqp://guest:guest@rabbitmq:5672/` - RabbitMQ broker
