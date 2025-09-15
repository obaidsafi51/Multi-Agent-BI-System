# Backend

## Overview
The Backend module serves as the orchestration layer for the Agentic BI system. It coordinates communication between agents, manages WebSocket connections, processes requests through MCP (Model Context Protocol), and handles database contexts and schema knowledge.

## Features
- Central orchestration for multi-agent communication
- WebSocket connection management
- MCP client implementation for schema intelligence
- Database context management
- Logging and monitoring
- Agent communication protocols (A2A, ACP)
- Robust error handling and validation

## Architecture
The Backend is organized into several key modules:

### Core Components
- `main.py`: Application entry point
- `orchestration.py`: Multi-agent coordination
- `database_context.py`: Database connection management
- `mcp_client.py`: HTTP-based MCP client
- `websocket_mcp_client.py`: WebSocket-based MCP client
- `websocket_agent_manager.py`: Agent WebSocket connection management

### Communication
- `communication/a2a.py`: Agent-to-Agent communication
- `communication/acp.py`: Agent Communication Protocol
- `communication/mcp.py`: Model Context Protocol integration
- `communication/models.py`: Communication data models
- `communication/router.py`: Message routing
- `communication/manager.py`: Communication management

### Database
- `database/connection.py`: Database connection handling
- `database/validation.py`: Query validation
- `database/validation_mcp.py`: MCP-based validation

### Models
- `models/core.py`: Core data models
- `models/ui.py`: UI-related models
- `models/user.py`: User models

### Schema Management
- `schema_knowledge/`: Schema intelligence components
- `schema_management/`: Schema management utilities

## Setup and Installation
1. Ensure Python 3.11+ is installed
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   or
   ```bash
   uv pip install -e .
   ```

## Configuration
Configure the Backend through environment variables or the `.env` file:
- `DATABASE_URL`: Connection string for the database
- `MCP_SERVER_URL`: URL for MCP server
- `WEBSOCKET_HOST`: Host for WebSocket server
- `WEBSOCKET_PORT`: Port for WebSocket server
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `AGENT_TIMEOUT`: Timeout for agent communications
- `CACHE_ENABLED`: Enable/disable caching

You can also configure logging through `logging_config.yaml`.

## Running the Backend
Start the backend using:
```bash
python main.py
```

Or use Docker:
```bash
docker build -t agentic-bi-backend .
docker run -p 8000:8000 --env-file .env agentic-bi-backend
```

## API Endpoints
The Backend provides these main endpoints:
- `/orchestrate`: Orchestrate multi-agent workflows
- `/websocket`: WebSocket connection endpoint
- `/health`: Health check endpoint
- `/schema`: Schema management endpoint
- `/agents`: Agent management endpoints

## Integration with Other Components
The Backend integrates with:
- NLP Agent: Processes natural language queries
- Data Agent: Executes database queries
- Viz Agent: Generates visualizations
- MCP Server: Provides schema intelligence
- Frontend: Serves as the API endpoint for frontend requests

## Development and Testing
For development and testing:
```bash
# Run tests
python -m pytest

# Run with development settings
python main.py --dev

# Validate communication
python validate_communication.py
```

## Monitoring and Logging
The Backend includes comprehensive monitoring and logging:
- Structured logging to files and console
- Performance monitoring
- WebSocket connection monitoring
- Agent health monitoring

## Best Practices
- Use structured logging for easier debugging
- Implement timeouts for all external communications
- Enable schema validation for improved reliability
- Configure appropriate WebSocket connection limits
