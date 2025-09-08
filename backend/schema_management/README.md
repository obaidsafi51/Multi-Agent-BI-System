# MCP Schema Management Foundation

This module provides the foundation for dynamic schema management using the TiDB MCP (Model Context Protocol) server. It replaces static schema files and migrations with real-time schema discovery and operations.

## Components

### Configuration (`config.py`)

- **MCPSchemaConfig**: Configuration for MCP client connections, timeouts, caching, and retry behavior
- **SchemaValidationConfig**: Configuration for schema validation behavior and strictness levels

### Models (`models.py`)

Data models for schema information:

- **DatabaseInfo**: Database metadata and accessibility
- **TableInfo**: Table metadata including size, row count, and engine
- **ColumnInfo**: Column definitions with data types, constraints, and properties
- **TableSchema**: Complete table schema with columns, indexes, and relationships
- **ValidationResult**: Results of data validation against schema
- **CacheStats**: Cache performance metrics

### Client (`client.py`)

- **BackendMCPClient**: Base MCP client with connection management and error handling
- **EnhancedMCPClient**: Extended client with schema-specific operations like discovery and validation

### Manager (`manager.py`)

- **MCPSchemaManager**: High-level interface for schema operations with caching and fallback mechanisms

## Usage

### Basic Setup

```python
from schema_management import MCPSchemaManager, MCPSchemaConfig

# Initialize with default configuration
manager = MCPSchemaManager()

# Or with custom configuration
config = MCPSchemaConfig(
    mcp_server_url="http://tidb-mcp-server:8000",
    cache_ttl=600,  # 10 minutes
    max_retries=5
)
manager = MCPSchemaManager(config)
```

### Schema Discovery

```python
# Connect to MCP server
await manager.connect()

# Discover databases
databases = await manager.discover_databases()
for db in databases:
    print(f"Database: {db.name} (accessible: {db.accessible})")

# Get tables in a database
tables = await manager.get_tables("my_database")
for table in tables:
    print(f"Table: {table.name} ({table.rows} rows)")

# Get table schema
schema = await manager.get_table_schema("my_database", "my_table")
if schema:
    print(f"Columns: {len(schema.columns)}")
    for col in schema.columns:
        print(f"  {col.name}: {col.data_type}")
```

### Cache Management

```python
# Get cache statistics
stats = manager.get_cache_stats()
print(f"Cache hit rate: {stats.hit_rate:.2%}")

# Refresh cache
await manager.refresh_schema_cache("all")
```

### Health Checking

```python
# Check MCP server health
healthy = await manager.health_check()
if healthy:
    print("MCP server is healthy")
```

## Configuration

### Environment Variables

- `TIDB_MCP_SERVER_URL`: MCP server URL (default: "http://tidb-mcp-server:8000")
- `MCP_CONNECTION_TIMEOUT`: Connection timeout in seconds (default: 30)
- `MCP_REQUEST_TIMEOUT`: Request timeout in seconds (default: 60)
- `MCP_MAX_RETRIES`: Maximum retry attempts (default: 3)
- `MCP_RETRY_DELAY`: Retry delay in seconds (default: 1.0)
- `MCP_CACHE_TTL`: Cache TTL in seconds (default: 300)
- `MCP_ENABLE_CACHING`: Enable caching (default: true)
- `MCP_FALLBACK_ENABLED`: Enable fallback mechanisms (default: true)

### Validation Configuration

- `SCHEMA_STRICT_MODE`: Enable strict validation mode (default: false)
- `SCHEMA_VALIDATE_TYPES`: Validate data types (default: true)
- `SCHEMA_VALIDATE_CONSTRAINTS`: Validate constraints (default: true)
- `SCHEMA_VALIDATE_RELATIONSHIPS`: Validate relationships (default: true)
- `SCHEMA_ALLOW_UNKNOWN_COLUMNS`: Allow unknown columns (default: false)

## Error Handling

The foundation includes comprehensive error handling:

- **MCPConnectionError**: Raised when MCP server connection fails
- **MCPRequestError**: Raised when MCP requests fail
- **Automatic Retries**: Configurable retry logic with exponential backoff
- **Fallback Mechanisms**: Graceful degradation when MCP server is unavailable
- **Cache Fallback**: Use cached data when server is temporarily unavailable

## Caching

The schema manager includes intelligent caching:

- **TTL-based Expiration**: Configurable cache expiration
- **Automatic Eviction**: LRU-style eviction when cache grows too large
- **Cache Statistics**: Performance monitoring and hit rate tracking
- **Selective Refresh**: Refresh specific cache types or all cache data

## Testing

Run the foundation tests:

```bash
python3 backend/schema_management/test_foundation.py
```

See example usage:

```bash
python3 backend/schema_management/example_usage.py
```

## Integration

This foundation is designed to integrate with:

1. **Database Layer**: Replace static schema queries with MCP-based discovery
2. **Data Validation**: Use real-time schema for dynamic validation
3. **Migration System**: Replace static migrations with MCP operations
4. **Backend Services**: Provide schema information to API endpoints

## Next Steps

After the foundation is established, the next tasks will:

1. Implement core schema discovery functionality
2. Build dynamic data validation system
3. Integrate MCP client into database layer
4. Update configuration and environment setup
5. Create comprehensive test suite
6. Remove static schema dependencies
7. Add monitoring and observability

## Requirements Satisfied

This foundation satisfies the following requirements:

- **1.1**: Dynamic schema discovery through MCP server
- **1.4**: Graceful fallback mechanisms when MCP server unavailable
- **7.1**: Comprehensive configuration options for MCP integration
