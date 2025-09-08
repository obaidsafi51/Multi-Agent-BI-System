# MCP Integration Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting information for MCP (Model Context Protocol) schema management integration in the AI CFO BI Agent.

## Quick Health Check

Run the following commands to check system health:

```bash
# Check MCP server status
docker-compose ps tidb-mcp-server

# Validate MCP configuration
./scripts/validate-mcp-config.sh

# Check logs
docker-compose logs -f tidb-mcp-server
docker-compose logs -f backend
```

## Common Issues and Solutions

### 1. MCP Server Connection Issues

#### Symptom

```
WARNING: MCP schema management not available - using static validation only
ERROR: Failed to connect to MCP server after 3 attempts
```

#### Possible Causes

- MCP server not running
- Network connectivity issues
- Incorrect MCP server URL
- Port conflicts

#### Solutions

1. **Check MCP Server Status**

   ```bash
   docker-compose ps tidb-mcp-server
   ```

2. **Restart MCP Server**

   ```bash
   docker-compose restart tidb-mcp-server
   ```

3. **Verify Configuration**

   ```bash
   # Check environment variables
   echo $MCP_SERVER_URL
   echo $MCP_SERVER_TIMEOUT

   # Validate configuration
   ./scripts/validate-mcp-config.sh
   ```

4. **Test Direct Connection**

   ```bash
   curl -X GET http://localhost:8000/health
   ```

5. **Check Port Availability**
   ```bash
   netstat -tulpn | grep 8000
   lsof -i :8000
   ```

### 2. Schema Discovery Failures

#### Symptom

```
ERROR: MCP schema discovery failed for database 'ai_cfo_bi': Failed to discover tables
WARNING: Using fallback table discovery
```

#### Possible Causes

- Database connection issues
- Insufficient permissions
- TiDB server unavailable
- Schema cache corruption

#### Solutions

1. **Check Database Connection**

   ```python
   from backend.database.connection import test_tidb_connection

   if test_tidb_connection():
       print("Database connection OK")
   else:
       print("Database connection failed")
   ```

2. **Verify Database Permissions**

   ```sql
   SHOW GRANTS FOR CURRENT_USER();
   SELECT USER(), CURRENT_USER();
   ```

3. **Clear Schema Cache**

   ```python
   from backend.database.connection import refresh_schema_cache

   await refresh_schema_cache("all")
   ```

4. **Check TiDB Server Status**
   ```bash
   docker-compose ps tidb
   docker-compose logs tidb
   ```

### 3. Validation Failures

#### Symptom

```
ERROR: Dynamic validation failed: Table ai_cfo_bi.financial_overview not found
WARNING: Fallback validation warning: {warning message}
```

#### Possible Causes

- Table doesn't exist
- Schema information outdated
- MCP server cache issues
- Database schema changes

#### Solutions

1. **Verify Table Existence**

   ```sql
   USE ai_cfo_bi;
   SHOW TABLES;
   DESCRIBE financial_overview;
   ```

2. **Refresh Schema Information**

   ```python
   from backend.schema_management import MCPSchemaManager

   # Refresh specific table schema
   await schema_manager.refresh_schema_cache("table")

   # Get fresh table information
   tables = await schema_manager.get_tables("ai_cfo_bi")
   print([table.name for table in tables])
   ```

3. **Check Cache Statistics**

   ```python
   from backend.database.connection import get_mcp_cache_stats

   stats = get_mcp_cache_stats()
   if stats:
       print(f"Cache hit rate: {stats['basic_stats']['hit_rate']:.2%}")
       print(f"Total entries: {stats['basic_stats']['total_entries']}")
   ```

### 4. Performance Issues

#### Symptom

```
WARNING: MCP operation took 10.5s to complete
WARNING: Low cache hit rate: 45%
```

#### Possible Causes

- Network latency
- Large dataset discovery
- Insufficient cache configuration
- Resource constraints

#### Solutions

1. **Optimize Cache Settings**

   ```bash
   # Increase cache size and TTL
   export MCP_SCHEMA_CACHE_SIZE=2000
   export MCP_SCHEMA_CACHE_TTL=600
   ```

2. **Monitor Performance**

   ```python
   import time
   from backend.schema_management import MCPSchemaManager

   start_time = time.time()
   schema = await schema_manager.get_table_schema("ai_cfo_bi", "financial_overview")
   duration = time.time() - start_time
   print(f"Schema discovery took {duration:.2f}s")
   ```

3. **Check Resource Usage**

   ```bash
   docker stats tidb-mcp-server
   docker stats backend
   ```

4. **Optimize Network Configuration**
   ```bash
   # Reduce timeout for faster failure detection
   export MCP_CONNECTION_TIMEOUT=5
   export MCP_SERVER_TIMEOUT=15
   ```

### 5. Import and Module Issues

#### Symptom

```
ImportError: No module named 'schema_management'
ModuleNotFoundError: No module named 'backend.schema_management'
```

#### Possible Causes

- Python path issues
- Missing module installation
- Import statement errors
- Virtual environment issues

#### Solutions

1. **Check Python Path**

   ```python
   import sys
   print(sys.path)

   # Add backend to path if needed
   sys.path.append('/path/to/backend')
   ```

2. **Verify Module Structure**

   ```bash
   ls -la backend/schema_management/
   ls -la backend/schema_management/__init__.py
   ```

3. **Fix Import Statements**

   ```python
   # Relative imports within backend
   from .schema_management import MCPSchemaManager

   # Absolute imports from outside
   from backend.schema_management import MCPSchemaManager
   ```

4. **Check Virtual Environment**
   ```bash
   which python
   pip list | grep schema
   ```

### 6. Configuration Issues

#### Symptom

```
ERROR: MCP schema manager is required but not provided
WARNING: MCP configuration validation failed
```

#### Possible Causes

- Missing environment variables
- Invalid configuration values
- Configuration file issues
- Environment loading problems

#### Solutions

1. **Validate Environment Variables**

   ```bash
   ./scripts/validate-mcp-config.sh
   ```

2. **Check Configuration Loading**

   ```python
   from backend.schema_management.config import MCPSchemaConfig

   try:
       config = MCPSchemaConfig.from_env()
       print("Configuration loaded successfully")
       print(f"MCP Server URL: {config.mcp_server_url}")
   except Exception as e:
       print(f"Configuration error: {e}")
   ```

3. **Set Required Variables**
   ```bash
   export MCP_SERVER_URL="http://tidb-mcp-server:8000"
   export MCP_SERVER_TIMEOUT="30"
   export MCP_FALLBACK_ENABLED="true"
   ```

## Diagnostic Commands

### MCP Server Health Check

```bash
# HTTP health check
curl -X GET http://localhost:8000/health

# Detailed status
curl -X GET http://localhost:8000/status

# MCP capabilities
curl -X POST http://localhost:8000/mcp/capabilities
```

### Schema Manager Diagnostics

```python
from backend.schema_management import MCPSchemaManager
from backend.schema_management.config import MCPSchemaConfig

# Create schema manager
config = MCPSchemaConfig.from_env()
manager = MCPSchemaManager(config)

# Test connection
connected = await manager.connect()
print(f"Connected: {connected}")

# Health check
healthy = await manager.health_check()
print(f"Healthy: {healthy}")

# Cache statistics
stats = manager.get_cache_stats()
print(f"Cache stats: {stats}")

# Detailed diagnostics
detailed_stats = manager.get_detailed_cache_stats()
print(f"Detailed cache stats: {detailed_stats}")
```

### Database Connection Diagnostics

```python
from backend.database.connection import get_database

db = get_database()

# Test basic connection
health = db.health_check()
print(f"Database health: {health}")

# Test MCP health
mcp_health = await db.mcp_health_check()
print(f"MCP health: {mcp_health}")

# Get database info
info = db.get_database_info()
print(f"Database info: {info}")

# Get MCP cache stats
cache_stats = db.get_mcp_cache_stats()
print(f"MCP cache stats: {cache_stats}")
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **MCP Server Availability**

   - Health check endpoint response time
   - Connection success rate
   - Error rate

2. **Schema Cache Performance**

   - Hit rate (should be > 80%)
   - Miss rate
   - Eviction count

3. **Validation Performance**
   - Average validation time
   - Fallback frequency
   - Error rates

### Sample Monitoring Script

```python
import asyncio
import time
from backend.database.connection import mcp_health_check, get_mcp_cache_stats

async def monitor_mcp_health():
    while True:
        try:
            # Check health
            start_time = time.time()
            is_healthy = await mcp_health_check()
            response_time = time.time() - start_time

            # Get cache stats
            cache_stats = get_mcp_cache_stats()

            print(f"Health: {is_healthy}, Response Time: {response_time:.2f}s")

            if cache_stats:
                hit_rate = cache_stats['basic_stats']['hit_rate']
                print(f"Cache Hit Rate: {hit_rate:.2%}")

                if hit_rate < 0.8:
                    print("WARNING: Low cache hit rate!")

            if response_time > 5.0:
                print("WARNING: Slow MCP response!")

        except Exception as e:
            print(f"Monitoring error: {e}")

        await asyncio.sleep(30)  # Check every 30 seconds

# Run monitoring
asyncio.run(monitor_mcp_health())
```

## Log Analysis

### Important Log Patterns

1. **MCP Connection Issues**

   ```
   ERROR: MCP connection failed (attempt X): ConnectionError
   WARNING: MCP server health check failed
   INFO: Attempting to reconnect MCP client...
   ```

2. **Schema Discovery Problems**

   ```
   ERROR: Failed to discover tables in database: timeout
   WARNING: Using fallback: returning empty table list
   INFO: Discovered X tables in database Y using fallback method
   ```

3. **Cache Performance**
   ```
   DEBUG: Cache hit for key: schema:database:table
   DEBUG: Cache miss for key: schema:database:table
   INFO: Schema cache refreshed successfully
   ```

### Log Configuration

Enable detailed logging for troubleshooting:

```python
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Enable specific loggers
logging.getLogger("backend.schema_management").setLevel(logging.DEBUG)
logging.getLogger("backend.database.connection").setLevel(logging.DEBUG)
logging.getLogger("tidb_mcp_server").setLevel(logging.DEBUG)
```

## Recovery Procedures

### 1. MCP Server Recovery

```bash
# Stop and remove containers
docker-compose stop tidb-mcp-server
docker-compose rm -f tidb-mcp-server

# Rebuild and restart
docker-compose build tidb-mcp-server
docker-compose up -d tidb-mcp-server

# Verify recovery
docker-compose ps tidb-mcp-server
curl -X GET http://localhost:8000/health
```

### 2. Schema Cache Recovery

```python
from backend.schema_management import MCPSchemaManager

# Clear all caches
await schema_manager.refresh_schema_cache("all")

# Invalidate specific patterns
await schema_manager.invalidate_cache_by_pattern("schema:*")

# Verify cache is working
stats = schema_manager.get_cache_stats()
print(f"Cache entries after reset: {stats.total_entries}")
```

### 3. Database Connection Recovery

```python
from backend.database.connection import close_database, get_database

# Reset database connections
await close_database()

# Get fresh database manager
db = get_database()

# Test connection
health = db.health_check()
print(f"Database connection recovered: {health}")
```

## Best Practices for Prevention

1. **Regular Health Checks**

   - Monitor MCP server availability
   - Check cache performance metrics
   - Validate configuration regularly

2. **Proper Error Handling**

   ```python
   try:
       schema = await schema_manager.get_table_schema(db, table)
   except Exception as e:
       logger.error(f"Schema discovery failed: {e}")
       # Use fallback logic
       schema = None
   ```

3. **Configuration Management**

   - Use environment-specific configurations
   - Validate configuration on startup
   - Monitor configuration drift

4. **Performance Optimization**

   - Set appropriate cache sizes
   - Monitor cache hit rates
   - Use connection pooling

5. **Monitoring and Alerting**
   - Set up health check alerts
   - Monitor performance metrics
   - Track error rates

## Getting Help

If you continue to experience issues:

1. **Check Recent Changes**

   - Review recent code changes
   - Check environment variable changes
   - Verify Docker compose updates

2. **Gather Information**

   - MCP server logs
   - Backend application logs
   - Configuration values
   - Error messages with stack traces

3. **Test in Isolation**

   - Test MCP server independently
   - Test database connection separately
   - Verify network connectivity

4. **Contact Support**
   - Provide diagnostic output
   - Include relevant log excerpts
   - Describe the environment and steps to reproduce

Remember: The MCP integration includes fallback mechanisms, so the system should continue to operate even when MCP is unavailable, though with reduced functionality.
