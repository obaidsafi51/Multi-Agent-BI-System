# 🐳 Docker Deployment Guide

This guide covers the Docker deployment setup for the Multi-Agent BI System, focusing on the NLP Agent and TiDB MCP Server.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   NLP Agent     │    │ TiDB MCP Server │
│   (Next.js)     │◄───┤   (FastAPI)     │◄───┤   (FastAPI)     │
│   Port: 3000    │    │   Port: 8002    │    │   Port: 8000    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────►│    Backend      │◄─────────────┘
                         │   (FastAPI)     │
                         │   Port: 8001    │
                         └─────────────────┘
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
        ┌───────▼───────┐ ┌──────▼──────┐ ┌────────▼────────┐
        │     Redis     │ │  RabbitMQ   │ │   TiDB Cloud    │
        │   Port: 6379  │ │ Port: 5672  │ │  (External)     │
        └───────────────┘ └─────────────┘ └─────────────────┘
```

## 📁 Project Structure

```
.
├── agents/
│   └── nlp-agent/           # NLP Agent service
│       ├── Dockerfile       # Optimized production build
│       ├── .dockerignore    # Build context optimization
│       ├── src/             # Source code
│       ├── main_optimized.py # Entry point
│       └── pyproject.toml   # Dependencies
├── tidb-mcp-server/         # TiDB MCP Server service
│   ├── Dockerfile           # Optimized production build
│   ├── .dockerignore        # Build context optimization
│   ├── src/                 # Source code
│   └── pyproject.toml       # Dependencies
├── docker-compose.yml       # Multi-service orchestration
└── .env.docker.template     # Environment configuration template
```

## 🚀 Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- TiDB Cloud account and database
- KIMI API key (Moonshot AI)

### 2. Environment Setup

```bash
# Copy the environment template
cp .env.docker.template .env

# Edit the .env file with your credentials
nano .env
```

**Required Configuration:**

- `TIDB_HOST`: Your TiDB Cloud host
- `TIDB_USER`: Your TiDB username
- `TIDB_PASSWORD`: Your TiDB password
- `TIDB_DATABASE`: Your TiDB database name
- `KIMI_API_KEY`: Your KIMI API key

### 3. Build and Run

```bash
# Validate Docker builds (optional but recommended)
./validate-docker-builds.sh

# Start all services
docker-compose up --build

# Or run in background
docker-compose up --build -d
```

### 4. Verify Services

- Frontend: http://localhost:3000
- Backend API: http://localhost:8001
- NLP Agent: http://localhost:8002
- TiDB MCP Server: http://localhost:8000
- RabbitMQ Management: http://localhost:15672

## 🔧 Docker Optimizations

### NLP Agent (`agents/nlp-agent/Dockerfile`)

- **Base Image**: `python:3.11-slim` for smaller footprint
- **UV Package Manager**: Fast dependency installation
- **No Virtual Environment**: Direct system installation (Docker best practice)
- **Non-root User**: Security hardening
- **Health Checks**: Container health monitoring
- **Multi-port Support**: Main API (8001) + WebSocket (8012)

### TiDB MCP Server (`tidb-mcp-server/Dockerfile`)

- **Base Image**: `python:3.11-slim` for consistency
- **UV Package Manager**: Fast dependency installation
- **No Virtual Environment**: Direct system installation
- **Non-root User**: Security hardening
- **Health Checks**: Container health monitoring
- **WebSocket Support**: Real-time MCP communication

### Key Docker Optimizations

1. **No Virtual Environments**: Removed `.venv` usage since Docker containers provide isolation
2. **Layer Caching**: Dependencies installed before source code copy
3. **Build Context**: Optimized `.dockerignore` files
4. **Security**: Non-root users for all services
5. **Health Checks**: Built-in container health monitoring

## 📊 Service Configuration

### NLP Agent Environment Variables

```env
# Service Configuration
AGENT_ID=nlp-agent-001
AGENT_TYPE=nlp
HOST=0.0.0.0
PORT=8001

# Performance Optimizations
ENABLE_WEBSOCKETS=true
ENABLE_ADVANCED_CACHING=true
ENABLE_PARALLEL_PROCESSING=true
CONNECTION_POOL_MIN=3
CONNECTION_POOL_MAX=15
MAX_CONCURRENT_REQUESTS=10

# Cache Configuration
CACHE_TTL_SECONDS=300
CACHE_MAX_SIZE=1000
SEMANTIC_SIMILARITY_THRESHOLD=0.85

# WebSocket Configuration
WS_HEARTBEAT_INTERVAL=30
WS_RECONNECT_DELAY=5
WS_MAX_RECONNECT_ATTEMPTS=5
```

### TiDB MCP Server Environment Variables

```env
# HTTP API Configuration
USE_HTTP_API=true
ENABLE_WEBSOCKETS=true

# Cache Configuration
CACHE_ENABLED=true
CACHE_TTL_SECONDS=300
CACHE_MAX_SIZE=1000

# Security Configuration
MAX_QUERY_TIMEOUT=30
MAX_SAMPLE_ROWS=100
RATE_LIMIT_RPM=100

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## 🔍 Troubleshooting

### Common Issues

1. **Build Failures**

   ```bash
   # Check Docker daemon is running
   docker info

   # Rebuild without cache
   docker-compose build --no-cache
   ```

2. **Database Connection Issues**

   ```bash
   # Check TiDB connectivity
   docker-compose logs tidb-mcp-server

   # Verify environment variables
   docker-compose config
   ```

3. **Port Conflicts**

   ```bash
   # Check port usage
   netstat -tulpn | grep :8000

   # Stop conflicting services
   docker-compose down
   ```

### Debugging Commands

```bash
# View logs for specific service
docker-compose logs -f nlp-agent

# Execute shell in running container
docker-compose exec nlp-agent bash

# Check container health
docker-compose ps

# View resource usage
docker stats
```

## 🔄 Development Workflow

### Local Development

```bash
# Start only required services for development
docker-compose up redis rabbitmq tidb-mcp-server

# Run NLP agent locally
cd agents/nlp-agent
uv run python main_optimized.py
```

### Production Deployment

```bash
# Use production profiles
docker-compose --profile full up -d

# Monitor services
docker-compose logs -f --tail=100
```

## 📈 Performance Monitoring

### Health Check Endpoints

- NLP Agent: `GET /health`
- TiDB MCP Server: `GET /health`
- Backend: `GET /health`

### Metrics Collection

```bash
# Container metrics
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Service-specific metrics
curl http://localhost:8002/status  # NLP Agent
curl http://localhost:8000/health  # TiDB MCP Server
```

## 🔐 Security Considerations

1. **Non-root Users**: All containers run as non-root users
2. **Environment Variables**: Sensitive data via environment variables
3. **Network Isolation**: Services communicate via Docker network
4. **Resource Limits**: CPU and memory limits defined
5. **Health Checks**: Automatic unhealthy container restart

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [TiDB Cloud Documentation](https://docs.pingcap.com/tidbcloud/)
- [KIMI API Documentation](https://platform.moonshot.cn/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

🎉 **Your Multi-Agent BI System is now ready for Docker deployment!**
