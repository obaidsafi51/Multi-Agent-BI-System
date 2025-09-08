# Schema Management Migration Guide

## Overview

The AI CFO BI Agent has successfully migrated from static schema management to dynamic MCP-based schema management. This document outlines the changes made and provides guidance for developers working with the new system.

## What Changed

### Removed Components

1. **Static Schema Files**

   - `backend/database/schema.sql` - Removed
   - `config/tidb-init.sql` - Removed
   - `backend/database/migrations.py` - Removed

2. **Static Validation Classes**

   - Original `DataValidator` and `FinancialDataValidator` - Replaced with MCP-based versions
   - Static validation imports - Updated to use MCP schema management

3. **Hardcoded Schema References**
   - Removed direct table name dependencies in validation logic
   - Replaced with dynamic schema discovery through MCP server

### New Components

1. **MCP Schema Management**

   - `MCPSchemaManager` - Core schema management using MCP server
   - `EnhancedMCPClient` - Extended MCP client for schema operations
   - `DynamicDataValidator` - Real-time schema-based validation

2. **Enhanced Validation System**

   - `EnhancedDataValidator` - MCP-based data validation
   - `EnhancedFinancialDataValidator` - MCP-based financial validation
   - Dynamic validation configuration and fallback mechanisms

3. **Backward Compatibility Layer**
   - `MCPIntegratedDataValidator` - Drop-in replacement for legacy validation
   - `MCPIntegratedFinancialDataValidator` - MCP-integrated financial validation
   - Legacy API compatibility with deprecation warnings

## Migration Benefits

### Before (Static Schema)

- Manual schema maintenance
- Static SQL files requiring updates
- Hardcoded validation rules
- Schema drift potential
- Manual migration scripts

### After (MCP-Based)

- Real-time schema discovery
- Automatic schema validation
- Dynamic constraint checking
- Live schema information
- No manual migrations needed

## Usage Examples

### Basic MCP Schema Manager

```python
from backend.schema_management import MCPSchemaManager, MCPSchemaConfig

# Initialize MCP schema manager
config = MCPSchemaConfig.from_env()
schema_manager = MCPSchemaManager(config)

# Connect to MCP server
await schema_manager.connect()

# Discover databases
databases = await schema_manager.discover_databases()

# Get table schema
schema = await schema_manager.get_table_schema("ai_cfo_bi", "financial_overview")
```

### Enhanced Data Validation

```python
from backend.schema_management.enhanced_data_validator import EnhancedDataValidator

# Create validator with MCP integration
validator = EnhancedDataValidator(schema_manager)

# Validate data against real-time schema
result = await validator.validate_data_with_schema(
    data={"revenue": 1000000, "period_date": "2024-01-01"},
    database="ai_cfo_bi",
    table="financial_overview"
)

if result.is_valid:
    print("Data is valid!")
else:
    for error in result.errors:
        print(f"Error: {error.field} - {error.message}")
```

### Backward Compatible Validation

```python
from backend.database.validation import MCPIntegratedDataValidator

# Drop-in replacement for legacy DataValidator
validator = MCPIntegratedDataValidator(schema_manager)

# Use existing validation methods
validated_data = await validator.validate_with_schema(
    data, "ai_cfo_bi", "financial_overview"
)
```

### Database Operations with MCP

```python
from backend.database.connection import get_database

# Get database manager with MCP integration
db = get_database()

# Execute query using MCP server
results = await db.execute_query_mcp(
    "SELECT * FROM financial_overview WHERE period_date > %s",
    {"period_date": "2024-01-01"}
)

# Get sample data
sample_data = await db.get_sample_data_mcp("ai_cfo_bi", "financial_overview", limit=10)
```

## Configuration

### Environment Variables

The system requires the following environment variables for MCP integration:

```bash
# MCP Server Connection
MCP_SERVER_URL=http://localhost:8000
MCP_SERVER_TIMEOUT=30
MCP_CONNECTION_TIMEOUT=10
MCP_MAX_RETRIES=3

# Schema Management
MCP_SCHEMA_CACHE_TTL=300
MCP_SCHEMA_CACHE_SIZE=1000
MCP_FALLBACK_ENABLED=true

# Validation Configuration
VALIDATION_STRICT_MODE=false
VALIDATION_ENABLE_TYPES=true
VALIDATION_ENABLE_CONSTRAINTS=true
VALIDATION_ENABLE_RELATIONSHIPS=true
VALIDATION_ALLOW_UNKNOWN_COLUMNS=false
VALIDATION_FALLBACK_TO_STATIC=true
```

### Docker Compose

The docker-compose.yml has been updated to include MCP configuration:

```yaml
environment:
  # MCP Schema Management Configuration
  MCP_SERVER_URL: "http://tidb-mcp-server:8000"
  MCP_SERVER_TIMEOUT: "30"
  MCP_CONNECTION_TIMEOUT: "10"
  MCP_MAX_RETRIES: "3"

  # Schema Validation Configuration
  MCP_SCHEMA_CACHE_TTL: "300"
  MCP_SCHEMA_CACHE_SIZE: "1000"
  MCP_FALLBACK_ENABLED: "true"
```

## Troubleshooting

### Common Issues

1. **MCP Server Not Available**

   - Symptom: "MCP schema management not available" warnings
   - Solution: Ensure tidb-mcp-server is running and accessible
   - Fallback: System will use basic validation if configured

2. **Schema Cache Issues**

   - Symptom: Outdated schema information
   - Solution: Clear cache or restart MCP server

   ```python
   await schema_manager.refresh_schema_cache()
   ```

3. **Validation Errors**
   - Symptom: Dynamic validation failures
   - Debug: Check MCP server logs and schema manager status
   ```python
   health_status = await schema_manager.health_check()
   cache_stats = schema_manager.get_cache_stats()
   ```

### Health Checks

Monitor MCP integration health:

```python
from backend.database.connection import mcp_health_check, get_mcp_cache_stats

# Check MCP server connectivity
is_healthy = await mcp_health_check()

# Get cache statistics
cache_stats = get_mcp_cache_stats()
print(f"Cache hit rate: {cache_stats['basic_stats']['hit_rate']:.2%}")
```

### Logging

Enable detailed MCP logging:

```python
import logging
logging.getLogger("backend.schema_management").setLevel(logging.DEBUG)
logging.getLogger("backend.database.connection").setLevel(logging.DEBUG)
```

## Performance Considerations

1. **Schema Caching**

   - Schema information is cached to reduce MCP server calls
   - Default TTL: 5 minutes
   - Automatic invalidation on schema changes

2. **Connection Pooling**

   - MCP connections are pooled and reused
   - Automatic reconnection on failures
   - Health checks prevent stale connections

3. **Fallback Mechanisms**
   - Basic validation when MCP unavailable
   - Graceful degradation with warnings
   - Configurable fallback behavior

## Best Practices

1. **Always Use Async Methods**

   ```python
   # Good
   result = await validator.validate_data_with_schema(data, db, table)

   # Avoid - synchronous methods are deprecated
   result = validator.validate_sync(data, table)
   ```

2. **Handle MCP Unavailability**

   ```python
   try:
       schema = await schema_manager.get_table_schema(db, table)
   except Exception as e:
       logger.warning(f"MCP unavailable: {e}")
       # Use fallback logic
   ```

3. **Monitor Cache Performance**

   ```python
   stats = get_mcp_cache_stats()
   if stats and stats['basic_stats']['hit_rate'] < 0.8:
       logger.warning("Low cache hit rate, consider increasing cache size")
   ```

4. **Use Factory Functions**

   ```python
   from backend.database.validation import create_mcp_data_validator

   validator = create_mcp_data_validator(schema_manager)
   ```

## Future Enhancements

1. **Real-time Schema Updates**

   - WebSocket integration for live schema changes
   - Automatic cache invalidation on DDL operations

2. **Advanced Validation Rules**

   - Business logic validation through MCP
   - Custom constraint definitions

3. **Schema Evolution Tracking**

   - Schema version management
   - Migration history through MCP

4. **Performance Optimizations**
   - Bulk validation operations
   - Parallel schema discovery
   - Intelligent caching strategies

## Support

For issues related to MCP schema management:

1. Check MCP server logs: `docker-compose logs tidb-mcp-server`
2. Verify configuration: `scripts/validate-mcp-config.sh`
3. Test connectivity: Use health check endpoints
4. Review this migration guide for common solutions

The migration to MCP-based schema management provides a more robust, flexible, and maintainable approach to database schema operations while maintaining backward compatibility for existing code.
