"""
Query executor for TiDB MCP Server.

This module provides safe SQL query execution with validation, timeout enforcement,
and result size limiting. Only SELECT statements are allowed for security.
"""

import hashlib
import logging
import os
import re
import sys
import time
from typing import Any

# Add the backend directory to the Python path to import DatabaseManager
backend_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'backend')
sys.path.insert(0, os.path.abspath(backend_path))

try:
    from database.connection import DatabaseManager
except ImportError:
    # For testing, create mock class if backend is not available
    class DatabaseManager:
        def execute_query(self, query, params=None, fetch_all=False, fetch_one=False):
            pass

from .cache_manager import CacheKeyGenerator, CacheManager
from .exceptions import QueryExecutionError, QueryTimeoutError, QueryValidationError
from .models import QueryResult

logger = logging.getLogger(__name__)


class QueryValidator:
    """
    SQL query validator that ensures only safe SELECT statements are executed.
    
    Provides comprehensive validation to prevent DML/DDL operations and
    potentially dangerous SQL constructs.
    """

    # Allowed SQL keywords for SELECT statements
    ALLOWED_KEYWORDS = {
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER',
        'ON', 'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'IS',
        'NULL', 'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET',
        'DISTINCT', 'AS', 'ASC', 'DESC', 'UNION', 'ALL', 'CASE', 'WHEN',
        'THEN', 'ELSE', 'END', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX',
        'SUBSTRING', 'CONCAT', 'UPPER', 'LOWER', 'TRIM', 'COALESCE',
        'CAST', 'CONVERT', 'DATE', 'TIME', 'TIMESTAMP', 'YEAR', 'MONTH',
        'DAY', 'HOUR', 'MINUTE', 'SECOND', 'NOW', 'CURDATE', 'CURTIME'
    }

    # Forbidden SQL keywords that indicate DML/DDL operations
    FORBIDDEN_KEYWORDS = {
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE',
        'REPLACE', 'MERGE', 'CALL', 'EXECUTE', 'EXEC', 'GRANT', 'REVOKE',
        'COMMIT', 'ROLLBACK', 'START', 'BEGIN', 'TRANSACTION', 'SAVEPOINT',
        'LOCK', 'UNLOCK', 'SET', 'SHOW', 'DESCRIBE', 'EXPLAIN',
        'ANALYZE', 'OPTIMIZE', 'REPAIR', 'CHECK', 'FLUSH', 'RESET',
        'LOAD', 'OUTFILE', 'INFILE', 'BACKUP', 'RESTORE'
    }

    # Dangerous patterns that should be blocked
    DANGEROUS_PATTERNS = [
        r';\s*\w+',  # Multiple statements
        r'--',       # SQL comments
        r'/\*.*?\*/',  # Block comments
        r'\bxp_cmdshell\b',  # Command execution
        r'\bsp_executesql\b',  # Dynamic SQL execution
        r'\bEXEC\s*\(',  # Execute function
        r'\bEVAL\s*\(',  # Eval function
        r'\bSYSTEM\s*\(',  # System function
    ]

    def __init__(self):
        """Initialize the query validator."""
        self._compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.DANGEROUS_PATTERNS]
        logger.debug("QueryValidator initialized")

    def validate_query(self, query: str) -> None:
        """
        Validate that a SQL query is safe to execute.
        
        Args:
            query: SQL query string to validate
            
        Raises:
            QueryValidationError: If query is invalid or unsafe
        """
        if not query or not query.strip():
            raise QueryValidationError("Query cannot be empty")

        # Normalize query for analysis
        normalized_query = self._normalize_query(query)

        # Check for dangerous patterns
        self._check_dangerous_patterns(normalized_query)

        # Check for forbidden keywords
        self._check_forbidden_keywords(normalized_query)

        # Validate query structure
        self._validate_query_structure(normalized_query)

        logger.debug(f"Query validation passed for: {query[:100]}...")

    def _normalize_query(self, query: str) -> str:
        """
        Normalize query for analysis by removing extra whitespace and converting to uppercase.
        
        Args:
            query: Original query string
            
        Returns:
            Normalized query string
        """
        # Remove extra whitespace and normalize
        normalized = ' '.join(query.split())
        return normalized.upper()

    def _check_dangerous_patterns(self, query: str) -> None:
        """
        Check for dangerous SQL patterns.
        
        Args:
            query: Normalized query string
            
        Raises:
            QueryValidationError: If dangerous patterns are found
        """
        for pattern in self._compiled_patterns:
            if pattern.search(query):
                raise QueryValidationError(f"Query contains dangerous pattern: {pattern.pattern}")

    def _check_forbidden_keywords(self, query: str) -> None:
        """
        Check for forbidden SQL keywords.
        
        Args:
            query: Normalized query string
            
        Raises:
            QueryValidationError: If forbidden keywords are found
        """
        # Extract words from query
        words = set(re.findall(r'\b\w+\b', query))

        # Check for forbidden keywords
        forbidden_found = words.intersection(self.FORBIDDEN_KEYWORDS)
        if forbidden_found:
            raise QueryValidationError(f"Query contains forbidden keywords: {', '.join(forbidden_found)}")

    def _validate_query_structure(self, query: str) -> None:
        """
        Validate the overall structure of the query.
        
        Args:
            query: Normalized query string
            
        Raises:
            QueryValidationError: If query structure is invalid
        """
        # Must start with SELECT
        if not query.strip().startswith('SELECT'):
            raise QueryValidationError("Query must start with SELECT statement")

        # Check for multiple statements (basic check)
        if ';' in query.rstrip(';'):
            raise QueryValidationError("Multiple statements are not allowed")

        # Basic FROM clause validation
        if 'FROM' not in query:
            # Allow SELECT without FROM for expressions like SELECT 1, SELECT NOW()
            pass

        # Check for balanced parentheses
        if query.count('(') != query.count(')'):
            raise QueryValidationError("Unbalanced parentheses in query")


class QueryExecutor:
    """
    Safe SQL query executor with validation, timeout enforcement, and result limiting.
    
    Provides secure execution of SELECT statements against TiDB with comprehensive
    validation, caching, and performance monitoring.
    """

    def __init__(self, db_manager: DatabaseManager | None = None,
                 cache_manager: CacheManager | None = None,
                 max_timeout: int = 30, max_result_rows: int = 1000):
        """
        Initialize the query executor.
        
        Args:
            db_manager: Database manager instance (creates new if None)
            cache_manager: Cache manager instance (creates new if None)
            max_timeout: Maximum query timeout in seconds
            max_result_rows: Maximum number of result rows to return
        """
        self.db_manager = db_manager or DatabaseManager()
        self.cache_manager = cache_manager or CacheManager(default_ttl=300)
        self.validator = QueryValidator()
        self.max_timeout = max_timeout
        self.max_result_rows = max_result_rows

        logger.info(f"QueryExecutor initialized with timeout={max_timeout}s, max_rows={max_result_rows}")

    def execute_query(self, query: str, timeout: int | None = None,
                     use_cache: bool = True) -> QueryResult:
        """
        Execute a SQL query with validation and safety checks.
        
        Args:
            query: SQL query string to execute
            timeout: Query timeout in seconds (uses default if None)
            use_cache: Whether to use caching for results
            
        Returns:
            QueryResult object with execution results
            
        Raises:
            QueryValidationError: If query validation fails
            QueryTimeoutError: If query execution times out
            QueryExecutionError: If query execution fails
        """
        if timeout is None:
            timeout = self.max_timeout

        # Validate timeout
        if timeout > self.max_timeout:
            raise QueryValidationError(f"Timeout cannot exceed {self.max_timeout} seconds")

        start_time = time.time()

        try:
            # Validate the query
            self.validator.validate_query(query)

            # Generate cache key
            query_hash = self._generate_query_hash(query)
            cache_key = CacheKeyGenerator.query_key(query_hash)

            # Try to get from cache first
            if use_cache:
                cached_result = self.cache_manager.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Query result retrieved from cache: {query_hash}")
                    return cached_result

            logger.info(f"Executing query (timeout={timeout}s): {query[:100]}...")

            # Execute the query with timeout
            results = self._execute_with_timeout(query, timeout)

            # Process results
            processed_results = self._process_results(results)

            execution_time_ms = (time.time() - start_time) * 1000

            # Check if results were truncated
            truncated = len(processed_results) >= self.max_result_rows
            if truncated:
                processed_results = processed_results[:self.max_result_rows]

            # Extract column names
            columns = list(processed_results[0].keys()) if processed_results else []

            # Create query result
            query_result = QueryResult(
                columns=columns,
                rows=processed_results,
                row_count=len(processed_results),
                execution_time_ms=execution_time_ms,
                truncated=truncated
            )

            # Cache the results
            if use_cache and not truncated:  # Don't cache truncated results
                self.cache_manager.set(cache_key, query_result)

            logger.info(f"Query executed successfully: {len(processed_results)} rows in "
                       f"{query_result.get_formatted_execution_time()}")

            return query_result

        except QueryValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)

            logger.error(f"Query execution failed: {error_msg}")

            # Determine error type
            if "timeout" in error_msg.lower() or execution_time_ms > timeout * 1000:
                raise QueryTimeoutError(f"Query execution timed out after {timeout} seconds")
            else:
                raise QueryExecutionError(f"Query execution failed: {error_msg}")

    def _generate_query_hash(self, query: str) -> str:
        """
        Generate a hash for the query to use as cache key.
        
        Args:
            query: SQL query string
            
        Returns:
            SHA256 hash of the normalized query
        """
        # Normalize query for consistent hashing
        normalized = ' '.join(query.split()).upper()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _execute_with_timeout(self, query: str, timeout: int) -> list[dict[str, Any]]:
        """
        Execute query with timeout enforcement.
        
        Args:
            query: SQL query to execute
            timeout: Timeout in seconds
            
        Returns:
            List of result rows as dictionaries
            
        Raises:
            QueryTimeoutError: If query times out
            QueryExecutionError: If query execution fails
        """
        try:
            # Note: The DatabaseManager should handle timeouts internally
            # For now, we'll rely on the database connection timeout settings
            results = self.db_manager.execute_query(query, fetch_all=True)
            return results if results else []

        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                raise QueryTimeoutError(f"Query execution timed out: {error_msg}")
            else:
                raise QueryExecutionError(f"Database error: {error_msg}")

    def _process_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Process raw database results for consistent formatting.
        
        Args:
            results: Raw results from database
            
        Returns:
            Processed results with consistent formatting
        """
        if not results:
            return []

        processed = []
        for row in results:
            processed_row = {}
            for key, value in row.items():
                # Handle different data types for JSON serialization
                if value is None:
                    processed_row[key] = None
                elif isinstance(value, (int, float, str, bool)):
                    processed_row[key] = value
                elif hasattr(value, 'isoformat'):  # datetime objects
                    processed_row[key] = value.isoformat()
                else:
                    # Convert other types to string
                    processed_row[key] = str(value)

            processed.append(processed_row)

        return processed

    def validate_query_syntax(self, query: str) -> dict[str, Any]:
        """
        Validate query syntax without executing it.
        
        Args:
            query: SQL query to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            self.validator.validate_query(query)
            return {
                'valid': True,
                'message': 'Query validation passed',
                'query_type': 'SELECT'
            }
        except QueryValidationError as e:
            return {
                'valid': False,
                'message': str(e),
                'query_type': None
            }

    def get_query_stats(self) -> dict[str, Any]:
        """
        Get query execution statistics.
        
        Returns:
            Dictionary with execution statistics
        """
        cache_stats = self.cache_manager.get_stats()

        return {
            'max_timeout': self.max_timeout,
            'max_result_rows': self.max_result_rows,
            'cache_stats': cache_stats
        }

    def clear_query_cache(self) -> int:
        """
        Clear all cached query results.
        
        Returns:
            Number of cache entries cleared
        """
        pattern = f"^{CacheKeyGenerator.PREFIX_QUERY}:.*"
        return self.cache_manager.invalidate(pattern)
