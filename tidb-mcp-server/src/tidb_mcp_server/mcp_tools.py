"""
MCP tools for Universal MCP Server.

This module implements MCP tool functions for database operations, LLM services,
and other AI-powered tools. All tools follow MCP specification and include proper
parameter validation and error handling.
"""

import logging
from typing import Any

from fastmcp import FastMCP

from .cache_manager import CacheManager
from .exceptions import (
    QueryExecutionError,
    QueryTimeoutError,
    QueryValidationError,
    TiDBMCPServerError,
)
from .query_executor import QueryExecutor
from .schema_inspector import SchemaInspector
from .schema_intelligence import (
    SchemaIntelligenceEngine, 
    get_schema_intelligence,
    initialize_schema_intelligence,
    discover_business_mappings_impl,
    analyze_query_intent_impl, 
    suggest_schema_optimizations_impl,
    get_schema_intelligence_stats_impl,
    learn_from_successful_mapping_impl
)

logger = logging.getLogger(__name__)

# Global instances (will be initialized by the server)
_schema_inspector: SchemaInspector | None = None
_query_executor: QueryExecutor | None = None
_cache_manager: CacheManager | None = None
_mcp_server: FastMCP | None = None
_schema_intelligence: SchemaIntelligenceEngine | None = None


def initialize_tools(schema_inspector: SchemaInspector,
                    query_executor: QueryExecutor,
                    cache_manager: CacheManager,
                    mcp_server: FastMCP,
                    config: Any) -> None:
    """
    Initialize the MCP tools with required dependencies.
    
    Args:
        schema_inspector: SchemaInspector instance
        query_executor: QueryExecutor instance
        cache_manager: CacheManager instance
        mcp_server: FastMCP server instance
        config: Server configuration for tool enablement
    """
    global _schema_inspector, _query_executor, _cache_manager, _mcp_server, _schema_intelligence
    _schema_inspector = schema_inspector
    _query_executor = query_executor
    _cache_manager = cache_manager
    _mcp_server = mcp_server
    
    # Initialize schema intelligence engine
    _schema_intelligence = initialize_schema_intelligence(
        schema_inspector=schema_inspector,
        query_executor=query_executor,
        cache_manager=cache_manager
    )
    
    # Initialize LLM tools if enabled
    if config.llm_tools_enabled:
        from .llm_tools import initialize_llm_tools
        llm_config = config.get_llm_config()
        initialize_llm_tools(llm_config, cache_manager)
    
    logger.info(f"MCP tools initialized (database: {config.database_tools_enabled}, llm: {config.llm_tools_enabled}, schema_intelligence: True)")


def _ensure_initialized() -> None:
    """Ensure tools are initialized before use."""
    global _schema_inspector, _query_executor, _cache_manager, _mcp_server, _schema_intelligence
    
    if not all([_schema_inspector, _query_executor, _cache_manager, _mcp_server]):
        # Auto-initialize if not already done
        try:
            logger.info("Auto-initializing MCP tools...")
            
            from .query_executor import QueryExecutor
            from .schema_inspector import SchemaInspector
            from .cache_manager import CacheManager
            
            # Create instances directly (without MCP server dependency for now)
            _query_executor = QueryExecutor()
            _schema_inspector = SchemaInspector()
            _cache_manager = CacheManager()
            _mcp_server = None  # Will be set when properly initialized
            
            # Initialize schema intelligence
            _schema_intelligence = initialize_schema_intelligence(
                schema_inspector=_schema_inspector,
                query_executor=_query_executor,
                cache_manager=_cache_manager
            )
            
            logger.info("MCP tools auto-initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to auto-initialize MCP tools: {e}")
            raise RuntimeError(f"MCP tools not initialized and auto-initialization failed: {e}")


def discover_databases() -> list[dict[str, Any]]:
    """
    Discover all accessible databases in the TiDB instance.
    
    Returns a list of databases with their metadata including name, charset,
    collation, and accessibility status. System databases are filtered out.
    
    Returns:
        List of database information dictionaries
        
    Raises:
        Exception: If database discovery fails
    """
    _ensure_initialized()

    try:
        logger.info("Discovering databases via MCP tool")

        databases = _schema_inspector.get_databases()

        # Convert to MCP-compatible format
        result = []
        for db in databases:
            db_info = {
                "name": db.name,
                "charset": db.charset,
                "collation": db.collation,
                "accessible": db.accessible
            }
            result.append(db_info)

        logger.info(f"Discovered {len(result)} databases ({sum(1 for db in result if db['accessible'])} accessible)")
        return result

    except Exception as e:
        logger.error(f"Database discovery failed: {e}")
        raise TiDBMCPServerError(f"Failed to discover databases: {str(e)}")


def discover_tables(database: str) -> list[dict[str, Any]]:
    """
    Discover all tables in a specific database.
    
    Returns detailed information about tables including name, type, engine,
    row count, size, and comments.
    
    Args:
        database: Name of the database to inspect
        
    Returns:
        List of table information dictionaries
        
    Raises:
        Exception: If table discovery fails or database doesn't exist
    """
    _ensure_initialized()

    if not database or not database.strip():
        raise ValueError("Database name is required and cannot be empty")

    try:
        logger.info(f"Discovering tables in database '{database}' via MCP tool")

        tables = _schema_inspector.get_tables(database)

        # Convert to MCP-compatible format
        result = []
        for table in tables:
            table_info = {
                "name": table.name,
                "type": table.type,
                "engine": table.engine,
                "rows": table.rows,
                "size_mb": table.size_mb,
                "comment": table.comment
            }
            result.append(table_info)

        logger.info(f"Discovered {len(result)} tables in database '{database}'")
        return result

    except Exception as e:
        logger.error(f"Table discovery failed for database '{database}': {e}")
        raise TiDBMCPServerError(f"Failed to discover tables in database '{database}': {str(e)}")


def get_table_schema(database: str, table: str) -> dict[str, Any]:
    """
    Get detailed schema information for a specific table.
    
    Returns comprehensive schema information including columns with their
    data types, constraints, indexes, primary keys, and foreign keys.
    
    Args:
        database: Name of the database
        table: Name of the table
        
    Returns:
        Dictionary with complete table schema information
        
    Raises:
        Exception: If schema retrieval fails or table doesn't exist
    """
    _ensure_initialized()

    if not database or not database.strip():
        raise ValueError("Database name is required and cannot be empty")

    if not table or not table.strip():
        raise ValueError("Table name is required and cannot be empty")

    try:
        logger.info(f"Getting schema for table '{database}.{table}' via MCP tool")

        schema = _schema_inspector.get_table_schema(database, table)

        # Convert to MCP-compatible format
        result = {
            "database": schema.database,
            "table": schema.table,
            "columns": [],
            "indexes": [],
            "primary_keys": schema.primary_keys,
            "foreign_keys": schema.foreign_keys
        }

        # Convert columns
        for column in schema.columns:
            column_info = {
                "name": column.name,
                "data_type": column.data_type,
                "is_nullable": column.is_nullable,
                "default_value": column.default_value,
                "is_primary_key": column.is_primary_key,
                "is_foreign_key": column.is_foreign_key,
                "comment": column.comment
            }
            result["columns"].append(column_info)

        # Convert indexes
        for index in schema.indexes:
            index_info = {
                "name": index.name,
                "columns": index.columns,
                "is_unique": index.is_unique,
                "index_type": index.index_type
            }
            result["indexes"].append(index_info)

        logger.info(f"Retrieved schema for table '{database}.{table}' with "
                   f"{len(result['columns'])} columns, {len(result['indexes'])} indexes")
        return result

    except Exception as e:
        logger.error(f"Schema retrieval failed for table '{database}.{table}': {e}")
        raise TiDBMCPServerError(f"Failed to get schema for table '{database}.{table}': {str(e)}")


def get_sample_data(database: str, table: str, limit: int = 10,
                   masked_columns: list[str] | None = None) -> dict[str, Any]:
    """
    Get sample data from a specific table.
    
    Returns sample rows from the table with configurable row limits and
    optional column masking for sensitive data protection.
    
    Args:
        database: Name of the database
        table: Name of the table
        limit: Number of sample rows to return (1-100, default 10)
        masked_columns: Optional list of column names to mask
        
    Returns:
        Dictionary with sample data and metadata
        
    Raises:
        Exception: If sample data retrieval fails or parameters are invalid
    """
    _ensure_initialized()

    if not database or not database.strip():
        raise ValueError("Database name is required and cannot be empty")

    if not table or not table.strip():
        raise ValueError("Table name is required and cannot be empty")

    if not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("Limit must be an integer between 1 and 100")

    if masked_columns is None:
        masked_columns = []

    if not isinstance(masked_columns, list):
        raise ValueError("Masked columns must be a list of column names")

    try:
        logger.info(f"Getting sample data for table '{database}.{table}' "
                   f"(limit={limit}, masked_columns={masked_columns}) via MCP tool")

        sample_result = _schema_inspector.get_sample_data(
            database=database,
            table=table,
            limit=limit,
            masked_columns=masked_columns
        )

        # Convert to MCP-compatible format
        result = {
            "database": sample_result.database,
            "table": sample_result.table,
            "columns": sample_result.columns,
            "rows": sample_result.rows,
            "row_count": sample_result.row_count,
            "total_table_rows": sample_result.total_table_rows,
            "execution_time_ms": sample_result.execution_time_ms,
            "sampling_method": sample_result.sampling_method,
            "masked_columns": sample_result.masked_columns,
            "success": sample_result.is_successful()
        }

        if sample_result.error:
            result["error"] = sample_result.error

        logger.info(f"Retrieved {sample_result.row_count} sample rows for table '{database}.{table}' "
                   f"in {sample_result.get_formatted_execution_time()}")
        return result

    except Exception as e:
        logger.error(f"Sample data retrieval failed for table '{database}.{table}': {e}")
        raise TiDBMCPServerError(f"Failed to get sample data for table '{database}.{table}': {str(e)}")


def execute_query(query: str, timeout: int | None = None, use_cache: bool = True) -> dict[str, Any]:
    """
    Execute a read-only SQL query against the database.
    
    Executes SELECT statements with comprehensive validation, timeout enforcement,
    and result size limiting. Only SELECT statements are allowed for security.
    
    Args:
        query: SQL SELECT query to execute
        timeout: Query timeout in seconds (uses server default if None)
        use_cache: Whether to use caching for query results
        
    Returns:
        Dictionary with query results and execution metadata
        
    Raises:
        Exception: If query validation or execution fails
    """
    _ensure_initialized()

    if not query or not query.strip():
        raise ValueError("Query is required and cannot be empty")

    if timeout is not None and (not isinstance(timeout, int) or timeout <= 0):
        raise ValueError("Timeout must be a positive integer")

    if not isinstance(use_cache, bool):
        raise ValueError("use_cache must be a boolean")

    try:
        logger.info(f"Executing query via MCP tool (timeout={timeout}, use_cache={use_cache}): "
                   f"{query[:100]}...")

        query_result = _query_executor.execute_query(
            query=query,
            timeout=timeout,
            use_cache=use_cache
        )

        # Convert to MCP-compatible format
        result = {
            "columns": query_result.columns,
            "rows": query_result.rows,
            "row_count": query_result.row_count,
            "execution_time_ms": query_result.execution_time_ms,
            "truncated": query_result.truncated,
            "success": query_result.is_successful()
        }

        if query_result.error:
            result["error"] = query_result.error

        logger.info(f"Query executed successfully: {query_result.row_count} rows in "
                   f"{query_result.get_formatted_execution_time()}")
        return result

    except (QueryValidationError, QueryTimeoutError, QueryExecutionError) as e:
        logger.error(f"Query execution failed: {e}")
        # Return structured error response for MCP
        return {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": 0,
            "truncated": False,
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
    except Exception as e:
        logger.error(f"Unexpected error during query execution: {e}")
        raise TiDBMCPServerError(f"Query execution failed: {str(e)}")


def validate_query(query: str) -> dict[str, Any]:
    """
    Validate a SQL query without executing it.
    
    Performs comprehensive validation to check if a query is safe to execute,
    including syntax validation and security checks.
    
    Args:
        query: SQL query to validate
        
    Returns:
        Dictionary with validation results
        
    Raises:
        Exception: If validation process fails
    """
    _ensure_initialized()

    if not query or not query.strip():
        raise ValueError("Query is required and cannot be empty")

    try:
        logger.info(f"Validating query via MCP tool: {query[:100]}...")

        validation_result = _query_executor.validate_query_syntax(query)

        logger.info(f"Query validation completed: valid={validation_result['valid']}")
        return validation_result

    except Exception as e:
        logger.error(f"Query validation failed: {e}")
        raise TiDBMCPServerError(f"Query validation failed: {str(e)}")


def get_server_stats() -> dict[str, Any]:
    """
    Get server statistics and performance metrics.
    
    Returns comprehensive statistics about cache performance, query execution,
    and server health for monitoring and debugging purposes.
    
    Returns:
        Dictionary with server statistics
        
    Raises:
        Exception: If statistics retrieval fails
    """
    _ensure_initialized()

    try:
        logger.debug("Getting server statistics via MCP tool")

        # Get cache statistics
        cache_stats = _cache_manager.get_stats()

        # Get query executor statistics
        query_stats = _query_executor.get_query_stats()

        # Get schema inspector cache statistics
        schema_cache_stats = _schema_inspector.get_cache_stats()

        result = {
            "cache": cache_stats,
            "query_executor": query_stats,
            "schema_cache": schema_cache_stats,
            "server_status": "healthy"
        }

        logger.debug("Server statistics retrieved successfully")
        return result

    except Exception as e:
        logger.error(f"Failed to get server statistics: {e}")
        raise TiDBMCPServerError(f"Failed to get server statistics: {str(e)}")


def clear_cache(cache_type: str = "all") -> dict[str, Any]:
    """
    Clear cached data to force fresh retrieval.
    
    Allows selective or complete cache clearing for troubleshooting
    or when fresh data is required.
    
    Args:
        cache_type: Type of cache to clear ("all", "queries", "schema", "tables", "databases")
        
    Returns:
        Dictionary with cache clearing results
        
    Raises:
        Exception: If cache clearing fails
    """
    _ensure_initialized()

    valid_cache_types = ["all", "queries", "schema", "tables", "databases"]
    if cache_type not in valid_cache_types:
        raise ValueError(f"Invalid cache_type. Must be one of: {valid_cache_types}")

    try:
        logger.info(f"Clearing cache via MCP tool: {cache_type}")

        cleared_count = 0

        if cache_type == "all":
            _cache_manager.clear()
            cleared_count = "all"
        elif cache_type == "queries":
            cleared_count = _query_executor.clear_query_cache()
        elif cache_type in ["schema", "tables", "databases"]:
            # Use schema inspector's cache invalidation
            if cache_type == "databases":
                cleared_count = _schema_inspector.invalidate_cache()
            elif cache_type == "tables":
                cleared_count = _schema_inspector.invalidate_cache()
            elif cache_type == "schema":
                cleared_count = _schema_inspector.invalidate_cache()

        result = {
            "cache_type": cache_type,
            "cleared_entries": cleared_count,
            "success": True
        }

        logger.info(f"Cache cleared successfully: {cache_type} ({cleared_count} entries)")
        return result

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise TiDBMCPServerError(f"Failed to clear cache: {str(e)}")


def discover_business_mappings(
    business_terms: list[str] | None = None,
    databases: list[str] | None = None,
    confidence_threshold: float = 0.6
) -> dict[str, Any]:
    """
    Discover mappings between business terms and database schema elements.
    
    Uses semantic analysis to map business terminology to actual database
    tables and columns, helping users understand what data is available.
    
    Args:
        business_terms: List of business terms to map (if None, uses common terms)
        databases: List of databases to analyze (if None, analyzes all)
        confidence_threshold: Minimum confidence score for mappings (0.0 to 1.0)
        
    Returns:
        Dictionary with discovered business mappings
        
    Raises:
        Exception: If business mapping discovery fails
    """
    _ensure_initialized()
    
    if not _schema_intelligence:
        raise TiDBMCPServerError("Schema intelligence engine not initialized")
    
    if confidence_threshold < 0.0 or confidence_threshold > 1.0:
        raise ValueError("Confidence threshold must be between 0.0 and 1.0")
    
    if business_terms is not None and not isinstance(business_terms, list):
        raise ValueError("Business terms must be a list of strings")
    
    if databases is not None and not isinstance(databases, list):
        raise ValueError("Databases must be a list of strings")
    
    try:
        import asyncio
        logger.info(f"Discovering business mappings (terms: {business_terms}, databases: {databases})")
        
        # Run async function in sync context
        try:
            loop = asyncio.get_event_loop()
            mappings = loop.run_until_complete(
                _schema_intelligence.discover_business_mappings(
                    business_terms=business_terms,
                    databases=databases,
                    confidence_threshold=confidence_threshold
                )
            )
        except RuntimeError:
            # No event loop, create one
            mappings = asyncio.run(
                _schema_intelligence.discover_business_mappings(
                    business_terms=business_terms,
                    databases=databases,
                    confidence_threshold=confidence_threshold
                )
            )
        
        result = {
            "mappings": [mapping.to_dict() for mapping in mappings],
            "total_mappings": len(mappings),
            "confidence_threshold": confidence_threshold,
            "business_terms_analyzed": business_terms or "default_terms",
            "databases_analyzed": databases or "all_databases"
        }
        
        logger.info(f"Discovered {len(mappings)} business mappings")
        return result
        
    except Exception as e:
        logger.error(f"Business mappings discovery failed: {e}")
        raise TiDBMCPServerError(f"Failed to discover business mappings: {str(e)}")


def analyze_query_intent(
    natural_language_query: str,
    context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Analyze natural language query to extract intent and suggest mappings.
    
    Processes user queries to understand what they're looking for and
    suggests appropriate database schema elements to query.
    
    Args:
        natural_language_query: Natural language query from user
        context: Optional context information (user preferences, history)
        
    Returns:
        Dictionary with analyzed query intent and suggested mappings
        
    Raises:
        Exception: If query intent analysis fails
    """
    _ensure_initialized()
    
    if not _schema_intelligence:
        raise TiDBMCPServerError("Schema intelligence engine not initialized")
    
    if not natural_language_query or not natural_language_query.strip():
        raise ValueError("Natural language query is required and cannot be empty")
    
    if context is not None and not isinstance(context, dict):
        raise ValueError("Context must be a dictionary")
    
    try:
        import asyncio
        logger.info(f"Analyzing query intent: {natural_language_query[:100]}...")
        
        # Run async function in sync context
        try:
            loop = asyncio.get_event_loop()
            intent = loop.run_until_complete(
                _schema_intelligence.analyze_query_intent(
                    natural_language_query=natural_language_query,
                    context=context or {}
                )
            )
        except RuntimeError:
            # No event loop, create one
            intent = asyncio.run(
                _schema_intelligence.analyze_query_intent(
                    natural_language_query=natural_language_query,
                    context=context or {}
                )
            )
        
        result = intent.to_dict()
        
        logger.info(f"Query intent analyzed: type={intent.intent_type}, confidence={intent.confidence_score:.2f}")
        return result
        
    except Exception as e:
        logger.error(f"Query intent analysis failed: {e}")
        raise TiDBMCPServerError(f"Failed to analyze query intent: {str(e)}")


def suggest_schema_optimizations(
    database: str | None = None,
    query_patterns: list[str] | None = None,
    performance_threshold: float = 0.5
) -> dict[str, Any]:
    """
    Suggest schema optimizations based on usage patterns and performance.
    
    Analyzes database schema and suggests improvements like indexes,
    partitioning, or denormalization for better query performance.
    
    Args:
        database: Target database (if None, analyzes all databases)
        query_patterns: Common query patterns to optimize for
        performance_threshold: Minimum impact threshold for suggestions (0.0 to 1.0)
        
    Returns:
        Dictionary with schema optimization suggestions
        
    Raises:
        Exception: If schema optimization analysis fails
    """
    _ensure_initialized()
    
    if not _schema_intelligence:
        raise TiDBMCPServerError("Schema intelligence engine not initialized")
    
    if performance_threshold < 0.0 or performance_threshold > 1.0:
        raise ValueError("Performance threshold must be between 0.0 and 1.0")
    
    if database is not None and not isinstance(database, str):
        raise ValueError("Database must be a string")
    
    if query_patterns is not None and not isinstance(query_patterns, list):
        raise ValueError("Query patterns must be a list of strings")
    
    try:
        import asyncio
        logger.info(f"Generating schema optimization suggestions (db: {database}, threshold: {performance_threshold})")
        
        # Run async function in sync context
        try:
            loop = asyncio.get_event_loop()
            optimizations = loop.run_until_complete(
                _schema_intelligence.suggest_schema_optimizations(
                    database=database,
                    query_patterns=query_patterns,
                    performance_threshold=performance_threshold
                )
            )
        except RuntimeError:
            # No event loop, create one
            optimizations = asyncio.run(
                _schema_intelligence.suggest_schema_optimizations(
                    database=database,
                    query_patterns=query_patterns,
                    performance_threshold=performance_threshold
                )
            )
        
        result = {
            "optimizations": [opt.to_dict() for opt in optimizations],
            "total_suggestions": len(optimizations),
            "performance_threshold": performance_threshold,
            "target_database": database or "all_databases",
            "optimization_types": list(set(opt.optimization_type for opt in optimizations))
        }
        
        logger.info(f"Generated {len(optimizations)} schema optimization suggestions")
        return result
        
    except Exception as e:
        logger.error(f"Schema optimization analysis failed: {e}")
        raise TiDBMCPServerError(f"Failed to suggest schema optimizations: {str(e)}")


def get_schema_intelligence_stats() -> dict[str, Any]:
    """
    Get statistics about schema intelligence operations.
    
    Returns performance metrics and usage statistics for the schema
    intelligence engine to help monitor its effectiveness.
    
    Returns:
        Dictionary with schema intelligence statistics
        
    Raises:
        Exception: If statistics retrieval fails
    """
    _ensure_initialized()
    
    if not _schema_intelligence:
        raise TiDBMCPServerError("Schema intelligence engine not initialized")
    
    try:
        logger.debug("Getting schema intelligence statistics")
        
        stats = _schema_intelligence.get_intelligence_stats()
        
        result = {
            "schema_intelligence_stats": stats,
            "engine_initialized": True,
            "available_features": [
                "business_mappings",
                "query_intent_analysis", 
                "schema_optimizations"
            ]
        }
        
        logger.debug("Schema intelligence statistics retrieved successfully")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get schema intelligence statistics: {e}")
        raise TiDBMCPServerError(f"Failed to get schema intelligence statistics: {str(e)}")


def learn_from_successful_mapping(
    business_term: str,
    database_name: str,
    table_name: str,
    column_name: str | None = None,
    success_score: float = 1.0
) -> dict[str, Any]:
    """
    Learn from successful mappings to improve future suggestions.
    
    Provides feedback to the schema intelligence engine about successful
    business term mappings to improve future recommendations.
    
    Args:
        business_term: Business term that was successfully mapped
        database_name: Database name of successful mapping
        table_name: Table name of successful mapping
        column_name: Column name of successful mapping (optional)
        success_score: Score indicating mapping success (0.0 to 1.0)
        
    Returns:
        Dictionary with learning operation results
        
    Raises:
        Exception: If learning operation fails
    """
    _ensure_initialized()
    
    if not _schema_intelligence:
        raise TiDBMCPServerError("Schema intelligence engine not initialized")
    
    if not business_term or not business_term.strip():
        raise ValueError("Business term is required and cannot be empty")
    
    if not database_name or not database_name.strip():
        raise ValueError("Database name is required and cannot be empty")
    
    if not table_name or not table_name.strip():
        raise ValueError("Table name is required and cannot be empty")
    
    if success_score < 0.0 or success_score > 1.0:
        raise ValueError("Success score must be between 0.0 and 1.0")
    
    try:
        from .schema_intelligence import BusinessMapping
        
        logger.info(f"Learning from successful mapping: {business_term} -> {database_name}.{table_name}.{column_name}")
        
        # Create mapping object
        mapping = BusinessMapping(
            business_term=business_term,
            schema_element_type='column' if column_name else 'table',
            database_name=database_name,
            table_name=table_name,
            column_name=column_name,
            confidence_score=0.8,  # Base confidence for learned mappings
            mapping_type='learned'
        )
        
        # Learn from the mapping
        _schema_intelligence.learn_from_successful_mapping(
            business_term=business_term,
            mapping=mapping,
            success_score=success_score
        )
        
        result = {
            "learning_successful": True,
            "business_term": business_term,
            "mapped_element": f"{database_name}.{table_name}" + (f".{column_name}" if column_name else ""),
            "success_score": success_score
        }
        
        logger.info("Successful mapping learned and stored")
        return result
        
    except Exception as e:
        logger.error(f"Failed to learn from successful mapping: {e}")
        raise TiDBMCPServerError(f"Failed to learn from successful mapping: {str(e)}")


def _with_error_handling_and_rate_limiting(func, tool_name: str):
    """
    Wrapper function to add error handling and rate limiting to MCP tools.
    
    Args:
        func: The original tool function
        tool_name: Name of the tool for logging
        
    Returns:
        Wrapped function with error handling and rate limiting
    """
    def wrapper(*args, **kwargs):
        import time
        from .rate_limiter import RateLimiter
        from .exceptions import RateLimitError, TiDBMCPServerError
        
        start_time = time.time()
        request_id = f"req_{int(start_time * 1000000)}"
        
        logger.info(
            f"Processing MCP tool request: {tool_name}",
            extra={
                "request_id": request_id,
                "tool_name": tool_name,
                "args": args,
                "kwargs": kwargs
            }
        )
        
        try:
            # Note: Rate limiting would be implemented here if we had access to the rate limiter
            # For now, we'll rely on the server-level rate limiting
            
            # Execute the tool function
            result = func(*args, **kwargs)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                f"MCP tool request completed successfully: {tool_name}",
                extra={
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "execution_time_ms": execution_time_ms,
                    "success": True
                }
            )
            
            return result
            
        except TiDBMCPServerError as e:
            execution_time_ms = (time.time() - start_time) * 1000
            
            logger.error(
                f"TiDB MCP Server error in tool {tool_name}: {e}",
                extra={
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "execution_time_ms": execution_time_ms,
                    "error_type": type(e).__name__,
                    "error_code": getattr(e, 'error_code', 'UNKNOWN')
                }
            )
            
            # Return error response in a format that MCP can handle
            return {
                "error": {
                    "code": getattr(e, 'error_code', 'SERVER_ERROR'),
                    "message": str(e),
                    "request_id": request_id,
                    "tool_name": tool_name
                }
            }
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            
            logger.exception(
                f"Unexpected error in tool {tool_name}: {e}",
                extra={
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "execution_time_ms": execution_time_ms,
                    "error_type": "unexpected"
                }
            )
            
            # Return error response in a format that MCP can handle
            return {
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                    "tool_name": tool_name
                }
            }
    
    return wrapper


def register_all_tools() -> None:
    """Register all MCP tools with the FastMCP server."""
    if not _mcp_server:
        raise RuntimeError("MCP server not initialized")

    # Register database tools
    @_mcp_server.tool()
    def discover_databases_tool() -> list[dict[str, Any]]:
        """Discover all accessible databases in the TiDB instance."""
        return _with_error_handling_and_rate_limiting(discover_databases, "discover_databases")()

    @_mcp_server.tool()
    def discover_tables_tool(database: str) -> list[dict[str, Any]]:
        """Discover all tables in a specific database."""
        return _with_error_handling_and_rate_limiting(discover_tables, "discover_tables")(database)

    @_mcp_server.tool()
    def get_table_schema_tool(database: str, table: str) -> dict[str, Any]:
        """Get detailed schema information for a specific table."""
        return _with_error_handling_and_rate_limiting(get_table_schema, "get_table_schema")(database, table)

    @_mcp_server.tool()
    def get_sample_data_tool(database: str, table: str, limit: int = 10,
                           masked_columns: list[str] | None = None) -> dict[str, Any]:
        """Get sample data from a specific table."""
        return _with_error_handling_and_rate_limiting(get_sample_data, "get_sample_data")(database, table, limit, masked_columns)

    @_mcp_server.tool()
    def execute_query_tool(query: str, timeout: int | None = None, use_cache: bool = True) -> dict[str, Any]:
        """Execute a read-only SQL query against the database."""
        return _with_error_handling_and_rate_limiting(execute_query, "execute_query")(query, timeout, use_cache)

    @_mcp_server.tool()
    def validate_query_tool(query: str) -> dict[str, Any]:
        """Validate a SQL query without executing it."""
        return _with_error_handling_and_rate_limiting(validate_query, "validate_query")(query)

    @_mcp_server.tool()
    def get_server_stats_tool() -> dict[str, Any]:
        """Get server statistics and performance metrics."""
        return _with_error_handling_and_rate_limiting(get_server_stats, "get_server_stats")()

    @_mcp_server.tool()
    def clear_cache_tool(cache_type: str = "all") -> dict[str, Any]:
        """Clear cached data to force fresh retrieval."""
        return _with_error_handling_and_rate_limiting(clear_cache, "clear_cache")(cache_type)

    # Register Schema Intelligence tools (sync wrappers for HTTP API compatibility)
    @_mcp_server.tool()
    def discover_business_mappings_tool(
        business_terms: list[str] | None = None,
        databases: list[str] | None = None,
        confidence_threshold: float = 0.6
    ) -> dict[str, Any]:
        """Discover mappings between business terms and database schema elements."""
        try:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(
                    discover_business_mappings_impl(business_terms, databases, confidence_threshold)
                )
            except RuntimeError:
                # No event loop, create one
                result = asyncio.run(
                    discover_business_mappings_impl(business_terms, databases, confidence_threshold)
                )
            return result
        except Exception as e:
            logger.error(f"Business mappings discovery failed: {e}")
            return {"error": str(e), "mappings": [], "total_mappings": 0}

    @_mcp_server.tool()
    def analyze_query_intent_tool(
        natural_language_query: str,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Analyze natural language query to extract intent and suggest mappings."""
        try:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(
                    analyze_query_intent_impl(natural_language_query, context)
                )
            except RuntimeError:
                # No event loop, create one
                result = asyncio.run(
                    analyze_query_intent_impl(natural_language_query, context)
                )
            return result
        except Exception as e:
            logger.error(f"Query intent analysis failed: {e}")
            return {"error": str(e), "intent_type": "unknown", "confidence_score": 0.0}

    @_mcp_server.tool()
    def suggest_schema_optimizations_tool(
        database: str | None = None,
        query_patterns: list[str] | None = None,
        performance_threshold: float = 0.5
    ) -> dict[str, Any]:
        """Suggest schema optimizations based on usage patterns and performance."""
        try:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(
                    suggest_schema_optimizations_impl(database, query_patterns, performance_threshold)
                )
            except RuntimeError:
                # No event loop, create one
                result = asyncio.run(
                    suggest_schema_optimizations_impl(database, query_patterns, performance_threshold)
                )
            return result
        except Exception as e:
            logger.error(f"Schema optimization analysis failed: {e}")
            return {"error": str(e), "optimizations": [], "total_suggestions": 0}

    @_mcp_server.tool()
    def get_schema_intelligence_stats_tool() -> dict[str, Any]:
        """Get statistics about schema intelligence operations."""
        try:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(get_schema_intelligence_stats_impl())
            except RuntimeError:
                # No event loop, create one
                result = asyncio.run(get_schema_intelligence_stats_impl())
            return result
        except Exception as e:
            logger.error(f"Schema intelligence stats failed: {e}")
            return {"error": str(e), "engine_initialized": False}

    @_mcp_server.tool()
    def learn_from_successful_mapping_tool(
        business_term: str,
        database_name: str,
        table_name: str,
        column_name: str | None = None,
        success_score: float = 1.0
    ) -> dict[str, Any]:
        """Learn from successful mappings to improve future suggestions."""
        try:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(
                    learn_from_successful_mapping_impl(business_term, database_name, table_name, column_name, success_score)
                )
            except RuntimeError:
                # No event loop, create one
                result = asyncio.run(
                    learn_from_successful_mapping_impl(business_term, database_name, table_name, column_name, success_score)
                )
            return result
        except Exception as e:
            logger.error(f"Learning from successful mapping failed: {e}")
            return {"error": str(e), "learning_successful": False}

    # Register LLM tools
    try:
        from .llm_tools import generate_text_tool, analyze_data_tool, generate_sql_tool, explain_results_tool

        @_mcp_server.tool()
        async def llm_generate_text_tool(prompt: str, system_prompt: str = None, 
                                        max_tokens: int = None, temperature: float = None,
                                        use_cache: bool = True) -> dict[str, Any]:
            """Generate text using LLM."""
            return await generate_text_tool(prompt, system_prompt, max_tokens, temperature, use_cache)

        @_mcp_server.tool()
        async def llm_analyze_data_tool(data: str, analysis_type: str = "general", 
                                       context: str = None) -> dict[str, Any]:
            """Analyze data using LLM."""
            return await analyze_data_tool(data, analysis_type, context)

        @_mcp_server.tool()
        async def llm_generate_sql_tool(natural_language_query: str, schema_info: str = None,
                                       examples: list[str] = None) -> dict[str, Any]:
            """Generate SQL query from natural language."""
            return await generate_sql_tool(natural_language_query, schema_info, examples)

        @_mcp_server.tool()
        async def llm_explain_results_tool(query: str, results: list[dict[str, Any]], 
                                          context: str = None) -> dict[str, Any]:
            """Explain query results in natural language."""
            return await explain_results_tool(query, results, context)

        logger.info("LLM tools registered successfully")
        
    except ImportError as e:
        logger.warning(f"LLM tools not available: {e}")

    logger.info("All available MCP tools registered successfully")


# List of all available MCP tools for registration
MCP_TOOLS = [
    discover_databases,
    discover_tables,
    get_table_schema,
    get_sample_data,
    execute_query,
    validate_query,
    get_server_stats,
    clear_cache,
    # Schema Intelligence Tools
    discover_business_mappings_impl,
    analyze_query_intent_impl,
    suggest_schema_optimizations_impl,
    get_schema_intelligence_stats_impl,
    learn_from_successful_mapping_impl
]
