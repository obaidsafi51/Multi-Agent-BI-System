# Data Agent

## Overview
The Data Agent is a critical component of the Agentic BI system responsible for database connectivity, query generation, validation, and optimization. It transforms structured requests from the NLP Agent into optimized database queries and returns results.

## Features
- Database connection management
- SQL query generation and validation
- Performance optimization for database queries
- Cache management for query results
- MCP (Model Context Protocol) integration
- Real-time data processing via WebSockets

## Architecture
The Data Agent is built with a modular architecture:

### Core Components
- `agent.py`: Main agent orchestration
- `mcp_agent.py`: MCP protocol integration
- `mcp_client.py`: Client for MCP communication

### Database Management
- `database/connection.py`: Database connection handling

### Query Processing
- `query/generator.py`: SQL query generation
- `query/validator.py`: Query validation and security checks

### Performance
- `optimization/optimizer.py`: Query performance optimization
- `cache/manager.py`: Cache management for results

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
Configure the Data Agent through environment variables in the `.env` file:
- `DATABASE_URL`: Connection string for the database
- `DATABASE_TYPE`: Type of database (TiDB, MySQL, PostgreSQL)
- `WEBSOCKET_PORT`: Port for WebSocket communication
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `CACHE_SIZE`: Maximum size of cache
- `MCP_SERVER_URL`: URL of MCP server

## Running the Data Agent
Start the agent using:
```bash
python main.py
```

Or use Docker:
```bash
docker build -t data-agent .
docker run -p 8002:8002 --env-file .env data-agent
```

## Development
For development, you can use the development environment:
```bash
docker build -f Dockerfile.dev -t data-agent-dev .
docker run -p 8002:8002 --env-file .env data-agent-dev
```

## Testing
Run tests using pytest:
```bash
pytest
```

## API Endpoints
The Data Agent provides these main endpoints:
- `/query`: Execute a database query
- `/validate`: Validate a query without execution
- `/schema`: Get database schema information
- `/health`: Health check endpoint

## Integration with Other Components
The Data Agent communicates with:
- NLP Agent: Receives structured query requests
- MCP Server: For schema intelligence and validation
- Viz Agent: Provides data for visualization
- Database: Executes queries and retrieves results

## Best Practices
- Use parameterized queries for security
- Implement query timeouts for long-running queries
- Enable caching for repeated queries
- Set appropriate connection pool sizes
