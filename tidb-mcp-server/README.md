# Universal MCP Server

A comprehensive Model Context Protocol (MCP) server that provides secure, efficient access to multiple AI tools including TiDB Cloud databases and LLM services, with comprehensive caching, performance monitoring, and rate limiting capabilities.

## Features

- **MCP Protocol Compliance**: Full support for MCP 2024-11-05 specification
- **TiDB Cloud Integration**: Native support for TiDB Cloud with SSL/TLS encryption
- **Intelligent Caching**: Multi-level caching with TTL-based expiration and LRU eviction
- **Performance Monitoring**: Real-time metrics collection and performance analysis
- **Rate Limiting**: Configurable request rate limiting to protect database resources
- **Schema Discovery**: Automatic database schema inspection and metadata extraction
- **Query Execution**: Safe SQL query execution with validation and error handling
- **Docker Support**: Production-ready containerized deployment
- **Comprehensive Testing**: Full test suite with unit, integration, and performance tests

## Quick Start

### Prerequisites

- Python 3.11 or higher
- TiDB Cloud account and database
- Docker (optional, for containerized deployment)

### Installation

#### Using uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd tidb-mcp-server

# Install dependencies
uv sync

# Install the package
uv pip install -e .
```

#### Using pip

```bash
pip install -e .
```

### Configuration

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit the `.env` file with your TiDB Cloud credentials:

```env
# TiDB Cloud Connection (Required)
TIDB_HOST=gateway01.us-west-2.prod.aws.tidbcloud.com
TIDB_PORT=4000
TIDB_USER=your_username
TIDB_PASSWORD=your_password
TIDB_DATABASE=your_database

# Optional Configuration
LOG_LEVEL=INFO
LOG_FORMAT=text
CACHE_TTL=300
CACHE_MAX_SIZE=1000
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

### Running the Server

#### Command Line

```bash
# Basic usage
tidb-mcp-server

# With custom log level
tidb-mcp-server --log-level DEBUG

# Validate configuration
tidb-mcp-server --validate-config

# Test database connection
tidb-mcp-server --check-connection
```

#### Using uv

```bash
uv run tidb-mcp-server
```

#### Docker

```bash
# Build the image
docker build -t tidb-mcp-server .

# Run with environment file
docker run --env-file .env tidb-mcp-server

# Run with docker-compose
docker-compose up
```

## MCP Tools

The server provides the following MCP tools:

### execute_query

Execute SQL queries against the TiDB database.

```json
{
  "name": "execute_query",
  "arguments": {
    "query": "SELECT * FROM users LIMIT 10",
    "limit": 100
  }
}
```

### describe_table

Get detailed information about table structure.

```json
{
  "name": "describe_table",
  "arguments": {
    "table_name": "users",
    "include_indexes": true
  }
}
```

### list_tables

List all tables and views in the database.

```json
{
  "name": "list_tables",
  "arguments": {
    "schema_name": "mydb",
    "table_type": "TABLE"
  }
}
```

### explain_query

Get execution plan for SQL queries.

```json
{
  "name": "explain_query",
  "arguments": {
    "query": "SELECT * FROM users WHERE id = 1",
    "format": "JSON"
  }
}
```

### get_sample_data

Retrieve sample data from tables.

```json
{
  "name": "get_sample_data",
  "arguments": {
    "table_name": "users",
    "limit": 10,
    "masked_columns": ["email", "phone"]
  }
}
```

## Architecture

### Core Components

- **MCP Server**: Handles MCP protocol communication and tool routing
- **Query Executor**: Executes SQL queries with validation and error handling
- **Schema Inspector**: Discovers and caches database schema information
- **Cache Manager**: Provides intelligent caching with TTL and LRU eviction
- **Rate Limiter**: Implements configurable request rate limiting
- **Performance Monitor**: Collects metrics and monitors system performance

### Caching Strategy

The server implements a multi-level caching strategy:

1. **Schema Caching**: Database metadata and table structures
2. **Query Result Caching**: Frequently accessed query results
3. **Sample Data Caching**: Table sample data for quick previews

Cache keys are automatically generated and invalidated based on schema changes.

### Performance Monitoring

Real-time performance monitoring includes:

- Response time tracking (P95, P99 percentiles)
- Error rate monitoring
- System resource usage (CPU, memory)
- Cache hit/miss ratios
- Database connection metrics

## Development

### Setup Development Environment

```bash
# Clone and setup
git clone <repository-url>
cd tidb-mcp-server
uv sync --dev

# Run tests
uv run pytest

# Run specific test categories
uv run pytest tests/test_integration.py -v
uv run pytest tests/test_performance.py -v

# Run with coverage
uv run pytest --cov=tidb_mcp_server --cov-report=html
```

### Code Quality

```bash
# Format code
uv run black src/ tests/
uv run isort src/ tests/

# Lint code
uv run ruff check src/ tests/

# Type checking
uv run mypy src/
```

### Testing

The project includes comprehensive tests:

- **Unit Tests**: Individual component testing
- **Integration Tests**: MCP protocol compliance testing
- **Performance Tests**: Response time and throughput validation
- **End-to-End Tests**: Complete workflow testing

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_mcp_client.py -v

# Run performance tests
uv run pytest tests/test_performance.py -v --tb=short
```

## Deployment

### Docker Deployment

#### Single Container

```bash
# Build image
docker build -t tidb-mcp-server .

# Run container
docker run -d \
  --name tidb-mcp-server \
  --env-file .env \
  -p 8000:8000 \
  tidb-mcp-server
```

#### Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Considerations

1. **Security**:

   - Use SSL/TLS for database connections
   - Implement proper authentication and authorization
   - Regularly rotate database credentials
   - Use secrets management for sensitive configuration

2. **Performance**:

   - Configure appropriate cache sizes based on available memory
   - Monitor and tune rate limiting settings
   - Use connection pooling for high-throughput scenarios
   - Implement proper logging and monitoring

3. **Reliability**:
   - Set up health checks and monitoring
   - Implement graceful shutdown handling
   - Use process managers (systemd, supervisor) for service management
   - Configure proper backup and disaster recovery

## Configuration Reference

### Environment Variables

| Variable              | Description                 | Default         | Required |
| --------------------- | --------------------------- | --------------- | -------- |
| `TIDB_HOST`           | TiDB Cloud host             | -               | Yes      |
| `TIDB_PORT`           | TiDB Cloud port             | 4000            | No       |
| `TIDB_USER`           | TiDB Cloud username         | -               | Yes      |
| `TIDB_PASSWORD`       | TiDB Cloud password         | -               | Yes      |
| `TIDB_DATABASE`       | TiDB Cloud database         | -               | Yes      |
| `TIDB_SSL_CA`         | SSL CA certificate path     | -               | No       |
| `MCP_SERVER_NAME`     | MCP server name             | tidb-mcp-server | No       |
| `MCP_SERVER_VERSION`  | MCP server version          | 0.1.0           | No       |
| `LOG_LEVEL`           | Logging level               | INFO            | No       |
| `LOG_FORMAT`          | Logging format (text/json)  | text            | No       |
| `CACHE_TTL`           | Cache TTL in seconds        | 300             | No       |
| `CACHE_MAX_SIZE`      | Maximum cache entries       | 1000            | No       |
| `RATE_LIMIT_REQUESTS` | Requests per window         | 100             | No       |
| `RATE_LIMIT_WINDOW`   | Rate limit window (seconds) | 60              | No       |

### Command Line Options

```
usage: tidb-mcp-server [-h] [--version]
                       [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                       [--log-format {text,json}] [--validate-config]
                       [--check-connection]

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --log-level           Set logging level
  --log-format          Set logging format
  --validate-config     Validate configuration and exit
  --check-connection    Test database connection and exit
```

## Troubleshooting

### Common Issues

1. **Connection Errors**:

   ```bash
   # Test connection
   tidb-mcp-server --check-connection

   # Check configuration
   tidb-mcp-server --validate-config
   ```

2. **Performance Issues**:

   - Monitor cache hit rates
   - Adjust cache size and TTL settings
   - Check database query performance
   - Review rate limiting configuration

3. **Memory Usage**:
   - Reduce cache size if memory usage is high
   - Monitor for memory leaks in long-running processes
   - Use appropriate Docker memory limits

### Logging

The server provides structured logging with configurable levels:

```bash
# Debug logging
tidb-mcp-server --log-level DEBUG

# JSON format for log aggregation
tidb-mcp-server --log-format json
```

### Health Checks

```bash
# Docker health check
docker run --rm tidb-mcp-server tidb-mcp-server --check-connection

# Manual health check
curl -f http://localhost:8000/health || exit 1
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints for all functions
- Write comprehensive tests
- Update documentation for new features
- Use conventional commit messages

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review existing GitHub issues
3. Create a new issue with detailed information
4. Include logs and configuration (without sensitive data)

## Changelog

### v0.1.0

- Initial release
- MCP protocol compliance
- TiDB Cloud integration
- Caching and performance monitoring
- Docker support
- Comprehensive test suite
