# Design Document

## Overview

The TiDB Cloud MCP Server is a Model Context Protocol compliant server that provides database schema information, sample data, and query execution capabilities to Large Language Models. The server acts as a bridge between AI agents and TiDB Cloud databases, enabling intelligent SQL generation and data analysis.

The server implements the MCP specification using the Python SDK and leverages the existing TiDB connection infrastructure from the project. It exposes database metadata through MCP tools and resources, allowing LLMs to understand database structure and generate optimized queries.

## Architecture

### High-Level Architecture

The server follows a modular design with clear separation of concerns:

1. **MCP Protocol Layer**: Handles MCP message parsing, routing, and response formatting
2. **Business Logic Layer**: Implements database operations, schema inspection, and caching
3. **Data Access Layer**: Manages TiDB connections and query execution
4. **Configuration Layer**: Handles environment-based configuration and security settings

## Components and Interfaces

### 1. MCP Server Core (`mcp_server.py`)

**Purpose**: Main server implementation using FastMCP framework

**Key Responsibilities**:

- Initialize MCP server with proper capabilities
- Register tools and resources
- Handle MCP protocol lifecycle
- Manage server configuration and startup

**Interface**:

```python
class TiDBMCPServer:
    def __init__(self, config: ServerConfig)
    def start(self) -> None
    def register_tools(self) -> None
    def register_resources(self) -> None
```

### 2. Schema Inspector (`schema_inspector.py`)

**Purpose**: Provides database schema discovery and metadata extraction

**Key Responsibilities**:

- Discover databases and tables
- Extract table schemas with columns, types, constraints
- Retrieve index information
- Cache schema metadata for performance

**Interface**:

```python
class SchemaInspector:
    def get_databases(self) -> List[DatabaseInfo]
    def get_tables(self, database: str) -> List[TableInfo]
    def get_table_schema(self, database: str, table: str) -> TableSchema
    def get_sample_data(self, database: str, table: str, limit: int) -> List[Dict]
```

### 3. Query Executor (`query_executor.py`)

**Purpose**: Safely executes read-only queries against TiDB

**Key Responsibilities**:

- Validate queries for read-only operations
- Execute SELECT statements with timeouts
- Handle query results and formatting
- Implement security restrictions

**Interface**:

```python
class QueryExecutor:
    def execute_query(self, query: str) -> QueryResult
    def validate_query(self, query: str) -> bool
    def format_results(self, results: Any) -> Dict
```

### 4. MCP Tools (`mcp_tools.py`)

**Purpose**: Implements MCP tool functions for database operations

**Key Tools**:

- `discover_databases`: List available databases
- `discover_tables`: List tables in a database
- `get_table_schema`: Get detailed table structure
- `get_sample_data`: Retrieve sample rows from tables
- `execute_query`: Run read-only SQL queries

**Interface**:

```python
@mcp.tool()
def discover_databases() -> List[Dict[str, str]]

@mcp.tool()
def discover_tables(database: str) -> List[Dict[str, Any]]

@mcp.tool()
def get_table_schema(database: str, table: str) -> Dict[str, Any]

@mcp.tool()
def get_sample_data(database: str, table: str, limit: int = 10) -> Dict[str, Any]

@mcp.tool()
def execute_query(query: str) -> Dict[str, Any]
```

### 5. Configuration Manager (`config.py`)

**Purpose**: Manages server configuration and environment settings

**Key Responsibilities**:

- Load configuration from environment variables
- Validate configuration parameters
- Provide configuration to other components
- Handle security settings

**Interface**:

```python
class ServerConfig:
    tidb_config: DatabaseConfig
    cache_ttl: int
    max_sample_rows: int
    query_timeout: int
    rate_limit: int
```

### 6. Cache Manager (`cache_manager.py`)

**Purpose**: Implements caching for schema information and query results

**Key Responsibilities**:

- Cache database and table lists
- Cache table schemas
- Implement TTL-based cache expiration
- Provide cache invalidation methods

**Interface**:

```python
class CacheManager:
    def get(self, key: str) -> Optional[Any]
    def set(self, key: str, value: Any, ttl: int) -> None
    def invalidate(self, pattern: str) -> None
    def clear(self) -> None
```

## Data Models

### Database Information Model

```python
@dataclass
class DatabaseInfo:
    name: str
    charset: str
    collation: str
    accessible: bool
```

### Table Information Model

```python
@dataclass
class TableInfo:
    name: str
    type: str  # 'BASE TABLE', 'VIEW', etc.
    engine: str
    rows: Optional[int]
    size_mb: Optional[float]
    comment: str
```

### Table Schema Model

```python
@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool
    default_value: Optional[str]
    is_primary_key: bool
    is_foreign_key: bool
    comment: str

@dataclass
class IndexInfo:
    name: str
    columns: List[str]
    is_unique: bool
    index_type: str

@dataclass
class TableSchema:
    database: str
    table: str
    columns: List[ColumnInfo]
    indexes: List[IndexInfo]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, str]]
```

### Query Result Model

```python
@dataclass
class QueryResult:
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    truncated: bool
    error: Optional[str]
```

## Error Handling

### Error Categories

1. **Connection Errors**: Database connectivity issues
2. **Authentication Errors**: Invalid credentials or permissions
3. **Query Errors**: SQL syntax or execution errors
4. **Validation Errors**: Invalid parameters or unsafe queries
5. **Timeout Errors**: Operations exceeding time limits
6. **MCP Protocol Errors**: Invalid MCP messages or protocol violations

### Error Response Format

All errors follow MCP error response format:

```python
{
    "error": {
        "code": -32000,  # MCP error codes
        "message": "Human readable error message",
        "data": {
            "error_type": "connection_error",
            "details": "Additional error context"
        }
    }
}
```

## Testing Strategy

### Unit Testing

- **Component Testing**: Test each component in isolation
- **Mock Dependencies**: Use mocks for database connections and external services
- **Error Scenarios**: Test error handling and edge cases
- **Configuration Testing**: Validate configuration loading and validation

### Integration Testing

- **Database Integration**: Test with real TiDB connections
- **MCP Protocol Testing**: Validate MCP message handling
- **End-to-End Flows**: Test complete request/response cycles
- **Performance Testing**: Validate response times and resource usage

### Test Structure

```
tests/
├── unit/
│   ├── test_schema_inspector.py
│   ├── test_query_executor.py
│   ├── test_cache_manager.py
│   └── test_config.py
├── integration/
│   ├── test_mcp_server.py
│   ├── test_database_operations.py
│   └── test_tools_integration.py
└── fixtures/
    ├── sample_schemas.json
    └── test_queries.sql
```
