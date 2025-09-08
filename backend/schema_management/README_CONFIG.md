# MCP Schema Management Configuration

This document describes the configuration system for MCP (Model Context Protocol) schema management in the AI CFO BI Agent.

## Overview

The MCP schema management system replaces static schema files with dynamic schema discovery through the TiDB MCP server. This configuration system provides:

- **Dynamic Schema Discovery**: Real-time schema information from the MCP server
- **Configurable Validation**: Flexible data validation rules
- **Health Monitoring**: Built-in health checks for MCP server connectivity
- **Fallback Mechanisms**: Graceful degradation when MCP server is unavailable

## Configuration Classes

### MCPSchemaConfig

Main configuration class for MCP server connectivity and behavior.

```python
from backend.schema_management.config import MCPSchemaConfig

# Load from environment variables
config = MCPSchemaConfig.from_env()

# Or create manually
config = MCPSchemaConfig(
    mcp_server_url="http://tidb-mcp-server:8000",
    connection_timeout=30,
    request_timeout=60,
    max_retries=3,
    retry_delay=1.0,
    cache_ttl=300,
    enable_caching=True,
    fallback_enabled=True
)
```

### SchemaValidationConfig

Configuration for schema validation behavior.

```python
from backend.schema_management.config import SchemaValidationConfig

# Load from environment variables
config = SchemaValidationConfig.from_env()

# Or create manually
config = SchemaValidationConfig(
    strict_mode=False,
    validate_types=True,
    validate_constraints=True,
    validate_relationships=True,
    allow_unknown_columns=False
)
```

## Environment Variables

### Required Variables

These variables must be set for the system to function:

```bash
# TiDB Connection (required for MCP server)
TIDB_HOST=your-tidb-host
TIDB_USER=your-username
TIDB_PASSWORD=your-password
TIDB_DATABASE=your-database
```

### MCP Configuration Variables

```bash
# MCP Server Configuration
TIDB_MCP_SERVER_URL=http://tidb-mcp-server:8000  # Default: http://tidb-mcp-server:8000
MCP_CONNECTION_TIMEOUT=30                         # Default: 30 seconds
MCP_REQUEST_TIMEOUT=60                           # Default: 60 seconds
MCP_MAX_RETRIES=3                                # Default: 3
MCP_RETRY_DELAY=1.0                              # Default: 1.0 seconds
MCP_CACHE_TTL=300                                # Default: 300 seconds (5 minutes)
MCP_ENABLE_CACHING=true                          # Default: true
MCP_FALLBACK_ENABLED=true                        # Default: true
```

### Schema Validation Variables

```bash
# Schema Validation Configuration
SCHEMA_STRICT_MODE=false                         # Default: false
SCHEMA_VALIDATE_TYPES=true                       # Default: true
SCHEMA_VALIDATE_CONSTRAINTS=true                 # Default: true
SCHEMA_VALIDATE_RELATIONSHIPS=true               # Default: true
SCHEMA_ALLOW_UNKNOWN_COLUMNS=false               # Default: false
```

## Configuration Validation

### Automatic Validation

All configuration classes include automatic validation:

```python
# This will raise ValueError if configuration is invalid
config = MCPSchemaConfig.from_env()
```

### Manual Validation

Use the validation utilities for comprehensive checks:

```python
from backend.schema_management.validate_config import (
    validate_environment_variables,
    validate_configurations
)

# Check environment variables
env_results = validate_environment_variables()
if not env_results["valid"]:
    print(f"Missing variables: {env_results['missing_required']}")

# Check configuration loading
config_results = validate_configurations()
if not config_results["mcp_config"]["valid"]:
    print(f"MCP config error: {config_results['mcp_config']['error']}")
```

### Command Line Validation

Use the provided scripts for validation:

```bash
# Validate configuration
python backend/test_mcp_config.py

# Full environment validation
./scripts/validate-mcp-config.sh
```

## Health Checks

### MCP Server Health Monitoring

```python
from backend.schema_management.health_check import MCPHealthChecker

config = MCPSchemaConfig.from_env()
checker = MCPHealthChecker(config)

# Check current health
health = await checker.check_health()
print(f"Status: {health['status']}")

# Wait for server to become healthy
is_healthy = await checker.wait_for_healthy(max_wait_seconds=60)
```

### Docker Health Checks

The system includes Docker health checks for:

- **Backend Service**: Validates MCP server connectivity
- **Data Agent**: Validates basic functionality
- **TiDB MCP Server**: Validates server availability

## Usage Examples

### Basic Configuration Loading

```python
from backend.schema_management.config import load_mcp_config, load_validation_config

# Load configurations
mcp_config = load_mcp_config()
validation_config = load_validation_config()

print(f"MCP Server: {mcp_config.mcp_server_url}")
print(f"Strict Mode: {validation_config.strict_mode}")
```

### Health Check Integration

```python
from backend.schema_management.health_check import check_mcp_server_health

# Simple health check
health = await check_mcp_server_health()
if health["status"] == "healthy":
    print("MCP server is ready")
else:
    print(f"MCP server issue: {health.get('error')}")
```

### Configuration in Docker

The Docker Compose configuration automatically includes all MCP environment variables:

```yaml
environment:
  # MCP Schema Management Configuration
  - TIDB_MCP_SERVER_URL=http://tidb-mcp-server:8000
  - MCP_CONNECTION_TIMEOUT=${MCP_CONNECTION_TIMEOUT:-30}
  - MCP_REQUEST_TIMEOUT=${MCP_REQUEST_TIMEOUT:-60}
  # ... other variables
```

## Troubleshooting

### Common Issues

1. **Invalid MCP Server URL**

   ```
   Error: Invalid MCP server URL format
   Solution: Ensure URL includes protocol (http:// or https://)
   ```

2. **Connection Timeout**

   ```
   Error: Timeout after 30s
   Solution: Increase MCP_CONNECTION_TIMEOUT or check server availability
   ```

3. **Missing Environment Variables**
   ```
   Error: Missing required environment variables
   Solution: Set TIDB_HOST, TIDB_USER, TIDB_PASSWORD, TIDB_DATABASE
   ```

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Configuration loading will now show detailed logs
config = MCPSchemaConfig.from_env()
```

### Validation Scripts

Run comprehensive validation:

```bash
# Test configuration loading
python backend/test_mcp_config.py

# Validate full environment
./scripts/validate-mcp-config.sh

# Check Docker configuration
docker-compose config
```

## Best Practices

1. **Environment Variables**: Always use environment variables for configuration
2. **Validation**: Validate configuration at startup
3. **Health Checks**: Monitor MCP server health regularly
4. **Fallback**: Enable fallback mechanisms for production
5. **Caching**: Use caching to reduce MCP server load
6. **Timeouts**: Set appropriate timeouts for your environment
7. **Monitoring**: Monitor configuration and health check logs

## Integration with Existing Code

The configuration system integrates seamlessly with existing backend code:

```python
# Import from backend package
from backend import load_mcp_config, load_validation_config

# Use in existing database managers
from backend.schema_management.manager import MCPSchemaManager

config = load_mcp_config()
schema_manager = MCPSchemaManager(config)
```

This configuration system provides a robust foundation for the MCP schema management migration while maintaining backward compatibility and operational reliability.
