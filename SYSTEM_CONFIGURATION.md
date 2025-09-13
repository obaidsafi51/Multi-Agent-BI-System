# Multi-Agent BI System - Standardized Configuration

# This file documents the standardized configuration for all system components

## Environment Variables - Standardized Naming Convention

### Backend Configuration

BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
REDIS_URL=redis://localhost:6379
FRONTEND_URL=http://frontend:3000
LOCALHOST_FRONTEND_URL=http://localhost:3000

### Database Configuration

TIDB_HOST=gateway01.us-west-2.prod.aws.tidbcloud.com
TIDB_PORT=4000
TIDB_USER=your_username
TIDB_PASSWORD=your_password
TIDB_DATABASE=Agentic_BI
USE_MCP_CLIENT=true

### MCP Server Configuration

MCP_SERVER_URL=http://tidb-mcp-server:8001
MCP_SERVER_WS_URL=ws://tidb-mcp-server:8001/ws

### Agent Configuration

# NLP Agent

NLP_AGENT_URL=http://nlp-agent:8001
NLP_AGENT_WS_URL=ws://nlp-agent:8011
NLP_AGENT_USE_WS=true
KIMI_API_KEY=your_kimi_api_key

# Data Agent

DATA_AGENT_URL=http://data-agent:8002
DATA_AGENT_WS_URL=ws://data-agent:8012
DATA_AGENT_USE_WS=true

# Viz Agent

VIZ_AGENT_URL=http://viz-agent:8003
VIZ_AGENT_WS_URL=ws://viz-agent:8013
VIZ_AGENT_USE_WS=true

### WebSocket Configuration

ENABLE_WEBSOCKETS=true
WEBSOCKET_HOST=0.0.0.0

# Agent-specific WebSocket ports

# NLP Agent WebSocket: 8011

# Data Agent WebSocket: 8012

# Viz Agent WebSocket: 8013

### Agent HTTP Ports (standardized)

# Backend HTTP: 8000

# NLP Agent HTTP: 8001

# Data Agent HTTP: 8002

# Viz Agent HTTP: 8003

### Performance and Reliability

ENVIRONMENT=production # Options: development, staging, production

## Standardized Message Types

### WebSocket Message Types

- heartbeat / ping -> heartbeat_response
- test_message -> test_response
- health_check -> health_check_response
- stats -> stats_response

### Agent-Specific Message Types

#### NLP Agent

- nlp_query -> nlp_query_response
- classify -> classification_response

#### Data Agent

- sql_query -> sql_query_response
- data_query -> data_query_response

#### Viz Agent

- visualization_request -> visualization_response
- generate_chart -> chart_generation_response
- export_chart -> chart_export_response

## Standardized Response Formats

All agents use the same base response structure defined in shared/models/workflow.py:

- AgentResponse (base class)
- NLPResponse (extends AgentResponse)
- DataQueryResponse (extends AgentResponse)
- VisualizationResponse (extends AgentResponse)

### Required Fields in All Responses

- success: boolean
- agent_metadata: AgentMetadata object
- error: ErrorResponse object (when success=false)

### Agent Metadata Structure

- agent_name: string
- agent_version: string
- processing_time_ms: integer
- operation_id: string
- status: "success" | "error" | "warning"

### Error Response Structure

- error_type: string
- message: string
- recovery_action: string
- suggestions: array of strings

## API Endpoint Standardization

### Backend Endpoints

- GET /health - System health check
- POST /api/query - Main query processing endpoint
- GET /api/database/list - List available databases
- POST /api/database/select - Select database and initialize schema
- GET /api/database/test - Test database connectivity

### Agent Endpoints (HTTP)

- GET /health - Agent health check
- GET /status - Agent status and metrics
- POST /process - Main processing endpoint (NLP Agent)
- POST /execute - SQL execution endpoint (Data Agent)
- POST /visualize - Visualization creation endpoint (Viz Agent)

### WebSocket Paths

All agents accept WebSocket connections on both:

- / (root path)
- /ws (explicit WebSocket path)

## Circuit Breaker Configuration

### Default Settings

- failure_threshold: 3-5 (varies by agent)
- recovery_timeout: 30-120 seconds (varies by criticality)
- timeout: 30-120 seconds (varies by operation complexity)

### Agent-Specific Circuit Breakers

- NLP Agent: 5 failures, 60s recovery, 30s timeout
- Data Agent: 5 failures, 120s recovery, 120s timeout
- Viz Agent: 3 failures, 45s recovery, 45s timeout

## Retry Configuration

### Default Retry Patterns

- max_attempts: 2-3 (varies by operation)
- base_delay: 1-2 seconds
- max_delay: 30-60 seconds
- exponential_backoff: true

## Logging Standards

### Log Levels

- ERROR: System failures, circuit breaker trips, unrecoverable errors
- WARN: Fallback activations, validation failures, recoverable issues
- INFO: Normal operations, successful requests, connection events
- DEBUG: Detailed tracing, performance metrics, development info

### Log Format

%(asctime)s - %(name)s - %(levelname)s - %(message)s

## Health Check Standards

### Response Structure

```json
{
  "status": "healthy" | "degraded" | "unhealthy",
  "timestamp": "ISO-8601 timestamp",
  "version": "agent version",
  "uptime": "seconds since start",
  "connections": "connection info object",
  "performance_metrics": "metrics object"
}
```

### Status Definitions

- healthy: All systems operational
- degraded: Some functionality limited but core operations work
- unhealthy: Critical failures, service unavailable

## Migration Path (Phase 1 -> Phase 2)

### Current State (Phase 1)

- HTTP communication with WebSocket fallback
- Individual agent WebSocket servers
- Backend orchestration via HTTP with WebSocket manager

### Future State (Phase 2)

- WebSocket-first communication
- HTTP fallback only for critical failures
- Real-time bidirectional communication
- Enhanced performance monitoring

### Migration Process

1. Enable WebSocket servers on all agents (ENABLE_WEBSOCKETS=true)
2. Test WebSocket connectivity via /api/agent/stats
3. Migrate agents individually via /api/agent/{name}/migrate-websocket
4. Monitor and rollback if needed via /api/agent/{name}/rollback-http
5. Disable HTTP endpoints once WebSocket is stable

## Troubleshooting Guide

### Common Issues

#### WebSocket Connection Failures

- Check ENABLE_WEBSOCKETS=true
- Verify port configuration (8011, 8012, 8013)
- Check firewall/network connectivity
- Review agent logs for startup errors

#### Response Format Mismatches

- All responses validated through backend validation functions
- Legacy format auto-conversion implemented
- Check shared/models/workflow.py for required fields

#### Circuit Breaker Trips

- Check /api/orchestration/metrics for breaker status
- Use /api/orchestration/circuit-breakers/reset to reset
- Review agent health via /api/health/agents

#### Environment Variable Issues

- Use standardized naming convention
- Check .env files in each component
- Verify Docker environment variable passing

### Debugging Commands

```bash
# Check agent health
curl http://backend:8000/api/health/agents

# Check WebSocket connectivity
curl http://backend:8000/api/agent/stats

# Check circuit breaker status
curl http://backend:8000/api/orchestration/metrics

# Test database connectivity
curl http://backend:8000/api/database/test

# Reset circuit breakers
curl -X GET http://backend:8000/api/orchestration/circuit-breakers/reset
```

## Performance Benchmarks

### Target Response Times

- NLP Processing: < 2 seconds
- Data Query Execution: < 5 seconds
- Visualization Generation: < 3 seconds
- Total Query Processing: < 10 seconds

### Throughput Targets

- Concurrent queries: 10+
- Cache hit rate: > 70%
- System availability: > 99.5%

### Resource Limits

- Memory usage per agent: < 512MB
- CPU usage per agent: < 50%
- Database connections: < 10 per agent

This configuration ensures consistent, reliable communication across all system components.
