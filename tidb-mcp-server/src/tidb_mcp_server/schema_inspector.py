"""
Schema inspector for TiDB MCP Server.

This module provides database schema discovery and metadata extraction capabilities
using the existing DatabaseManager from the backend. It includes caching for
performance optimization and proper error handling.
"""

import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
import sys
import os

# Add the backend directory to the Python path to import DatabaseManager
backend_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'backend')
sys.path.insert(0, os.path.abspath(backend_path))

try:
    from database.connection import DatabaseManager, DatabaseConfig
except ImportError:
    # For testing, create mock classes if backend is not available
    class DatabaseManager:
        def execute_query(self, query, params=None, fetch_all=False, fetch_one=False):
            pass
    
    class DatabaseConfig:
        pass
from .models import DatabaseInfo, TableInfo, TableSchema, ColumnInfo, IndexInfo, SampleDataResult
from .cache_manager import CacheManager, CacheKeyGenerator

logger = logging.getLogger(__name__)


class SchemaInspector:
    """
    Database schema inspector that provides discovery and metadata extraction.
    
    Uses the existing DatabaseManager from backend/database/connection.py for
    database operations and integrates with CacheManager for performance optimization.
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None, cache_manager: Optional[CacheManager] = None):
        """
        Initialize the schema inspector.
        
        Args:
            db_manager: Database manager instance (creates new if None)
            cache_manager: Cache manager instance (creates new if None)
        """
        self.db_manager = db_manager or DatabaseManager()
        self.cache_manager = cache_manager or CacheManager(default_ttl=300)  # 5 minutes default TTL
        
        logger.info("SchemaInspector initialized")
    
    def get_databases(self) -> List[DatabaseInfo]:
        """
        Retrieve list of accessible databases from INFORMATION_SCHEMA.SCHEMATA.
        
        Filters out system databases and databases the user doesn't have access to.
        Results are cached for performance.
        
        Returns:
            List of DatabaseInfo objects for accessible databases
            
        Raises:
            Exception: If database query fails
        """
        cache_key = CacheKeyGenerator.databases_key()
        
        # Try to get from cache first
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            logger.debug("Retrieved databases from cache")
            return cached_result
        
        try:
            logger.info("Querying databases from INFORMATION_SCHEMA.SCHEMATA")
            
            # Query INFORMATION_SCHEMA.SCHEMATA for database information
            query = """
                SELECT 
                    SCHEMA_NAME as name,
                    DEFAULT_CHARACTER_SET_NAME as charset,
                    DEFAULT_COLLATION_NAME as collation
                FROM INFORMATION_SCHEMA.SCHEMATA 
                WHERE SCHEMA_NAME NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
                ORDER BY SCHEMA_NAME
            """
            
            results = self.db_manager.execute_query(query, fetch_all=True)
            
            databases = []
            for row in results:
                # Test accessibility by trying to query the database
                accessible = self._test_database_access(row['name'])
                
                database_info = DatabaseInfo(
                    name=row['name'],
                    charset=row['charset'],
                    collation=row['collation'],
                    accessible=accessible
                )
                databases.append(database_info)
            
            # Cache the results
            self.cache_manager.set(cache_key, databases)
            
            logger.info(f"Retrieved {len(databases)} databases ({sum(1 for db in databases if db.accessible)} accessible)")
            return databases
            
        except Exception as e:
            logger.error(f"Failed to retrieve databases: {e}")
            raise
    
    def get_tables(self, database: str) -> List[TableInfo]:
        """
        Retrieve table information from INFORMATION_SCHEMA.TABLES for a specific database.
        
        Args:
            database: Database name to query tables for
            
        Returns:
            List of TableInfo objects for tables in the database
            
        Raises:
            Exception: If database query fails or database doesn't exist
        """
        cache_key = CacheKeyGenerator.tables_key(database)
        
        # Try to get from cache first
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Retrieved tables for database '{database}' from cache")
            return cached_result
        
        try:
            logger.info(f"Querying tables for database '{database}' from INFORMATION_SCHEMA.TABLES")
            
            # Query INFORMATION_SCHEMA.TABLES for table information
            query = """
                SELECT 
                    TABLE_NAME as name,
                    TABLE_TYPE as type,
                    ENGINE as engine,
                    TABLE_ROWS as rows,
                    ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as size_mb,
                    TABLE_COMMENT as comment
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME
            """
            
            results = self.db_manager.execute_query(query, params=(database,), fetch_all=True)
            
            tables = []
            for row in results:
                table_info = TableInfo(
                    name=row['name'],
                    type=row['type'],
                    engine=row['engine'] or 'Unknown',
                    rows=row['rows'],
                    size_mb=row['size_mb'],
                    comment=row['comment'] or ''
                )
                tables.append(table_info)
            
            # Cache the results
            self.cache_manager.set(cache_key, tables)
            
            logger.info(f"Retrieved {len(tables)} tables for database '{database}'")
            return tables
            
        except Exception as e:
            logger.error(f"Failed to retrieve tables for database '{database}': {e}")
            raise
    
    def get_table_schema(self, database: str, table: str) -> TableSchema:
        """
        Retrieve detailed schema information for a specific table.
        
        Queries INFORMATION_SCHEMA.COLUMNS, INFORMATION_SCHEMA.STATISTICS, and
        INFORMATION_SCHEMA.KEY_COLUMN_USAGE to build complete table schema.
        
        Args:
            database: Database name
            table: Table name
            
        Returns:
            TableSchema object with complete schema information
            
        Raises:
            Exception: If database query fails or table doesn't exist
        """
        cache_key = CacheKeyGenerator.schema_key(database, table)
        
        # Try to get from cache first
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Retrieved schema for table '{database}.{table}' from cache")
            return cached_result
        
        try:
            logger.info(f"Querying schema for table '{database}.{table}'")
            
            # Get column information
            columns = self._get_column_info(database, table)
            
            # Get index information
            indexes = self._get_index_info(database, table)
            
            # Get primary key and foreign key information
            primary_keys, foreign_keys = self._get_key_constraints(database, table)
            
            # Update column info with key information
            for column in columns:
                column.is_primary_key = column.name in primary_keys
                column.is_foreign_key = any(fk.get('column_name') == column.name for fk in foreign_keys)
            
            # Create table schema object
            table_schema = TableSchema(
                database=database,
                table=table,
                columns=columns,
                indexes=indexes,
                primary_keys=primary_keys,
                foreign_keys=foreign_keys
            )
            
            # Cache the results
            self.cache_manager.set(cache_key, table_schema)
            
            logger.info(f"Retrieved schema for table '{database}.{table}' with {len(columns)} columns, {len(indexes)} indexes")
            return table_schema
            
        except Exception as e:
            logger.error(f"Failed to retrieve schema for table '{database}.{table}': {e}")
            raise
    
    def _get_column_info(self, database: str, table: str) -> List[ColumnInfo]:
        """
        Retrieve column information from INFORMATION_SCHEMA.COLUMNS.
        
        Args:
            database: Database name
            table: Table name
            
        Returns:
            List of ColumnInfo objects
        """
        query = """
            SELECT 
                COLUMN_NAME as name,
                DATA_TYPE as data_type,
                IS_NULLABLE as is_nullable,
                COLUMN_DEFAULT as default_value,
                COLUMN_COMMENT as comment
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        
        results = self.db_manager.execute_query(query, params=(database, table), fetch_all=True)
        
        columns = []
        for row in results:
            column_info = ColumnInfo(
                name=row['name'],
                data_type=row['data_type'],
                is_nullable=row['is_nullable'] == 'YES',
                default_value=row['default_value'],
                comment=row['comment'] or ''
            )
            columns.append(column_info)
        
        return columns
    
    def _get_index_info(self, database: str, table: str) -> List[IndexInfo]:
        """
        Retrieve index information from INFORMATION_SCHEMA.STATISTICS.
        
        Args:
            database: Database name
            table: Table name
            
        Returns:
            List of IndexInfo objects
        """
        query = """
            SELECT 
                INDEX_NAME as name,
                COLUMN_NAME as column_name,
                NON_UNIQUE as non_unique,
                INDEX_TYPE as index_type,
                SEQ_IN_INDEX as seq_in_index
            FROM INFORMATION_SCHEMA.STATISTICS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """
        
        results = self.db_manager.execute_query(query, params=(database, table), fetch_all=True)
        
        # Group columns by index name
        index_groups = {}
        for row in results:
            index_name = row['name']
            if index_name not in index_groups:
                index_groups[index_name] = {
                    'columns': [],
                    'is_unique': row['non_unique'] == 0,  # NON_UNIQUE = 0 means unique
                    'index_type': row['index_type'] or 'BTREE'
                }
            index_groups[index_name]['columns'].append(row['column_name'])
        
        # Create IndexInfo objects
        indexes = []
        for index_name, index_data in index_groups.items():
            index_info = IndexInfo(
                name=index_name,
                columns=index_data['columns'],
                is_unique=index_data['is_unique'],
                index_type=index_data['index_type']
            )
            indexes.append(index_info)
        
        return indexes
    
    def _get_key_constraints(self, database: str, table: str) -> tuple[List[str], List[Dict[str, str]]]:
        """
        Retrieve primary key and foreign key constraint information.
        
        Args:
            database: Database name
            table: Table name
            
        Returns:
            Tuple of (primary_keys, foreign_keys)
        """
        # Get primary key information
        pk_query = """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
            WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = %s 
                AND CONSTRAINT_NAME = 'PRIMARY'
            ORDER BY ORDINAL_POSITION
        """
        
        pk_results = self.db_manager.execute_query(pk_query, params=(database, table), fetch_all=True)
        primary_keys = [row['COLUMN_NAME'] for row in pk_results]
        
        # Get foreign key information
        fk_query = """
            SELECT 
                kcu.COLUMN_NAME as column_name,
                kcu.CONSTRAINT_NAME as constraint_name,
                kcu.REFERENCED_TABLE_SCHEMA as referenced_database,
                kcu.REFERENCED_TABLE_NAME as referenced_table,
                kcu.REFERENCED_COLUMN_NAME as referenced_column
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc 
                ON kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME 
                AND kcu.TABLE_SCHEMA = tc.TABLE_SCHEMA
            WHERE kcu.TABLE_SCHEMA = %s 
                AND kcu.TABLE_NAME = %s 
                AND tc.CONSTRAINT_TYPE = 'FOREIGN KEY'
            ORDER BY kcu.ORDINAL_POSITION
        """
        
        fk_results = self.db_manager.execute_query(fk_query, params=(database, table), fetch_all=True)
        
        foreign_keys = []
        for row in fk_results:
            foreign_key = {
                'column_name': row['column_name'],
                'constraint_name': row['constraint_name'],
                'referenced_database': row['referenced_database'],
                'referenced_table': row['referenced_table'],
                'referenced_column': row['referenced_column']
            }
            foreign_keys.append(foreign_key)
        
        return primary_keys, foreign_keys
    
    def _test_database_access(self, database: str) -> bool:
        """
        Test if a database is accessible by attempting a simple query.
        
        Args:
            database: Database name to test access for
    
        Returns:
            True if database is accessible, False otherwise
        """
        try:
            # Simple query to test database access
            query = "SELECT 1 FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s LIMIT 1"
            self.db_manager.execute_query(query, params=(database,), fetch_one=True)
            return True
        except Exception as e:
            logger.debug(f"Database '{database}' is not accessible: {e}")
            return False
    
    def invalidate_cache(self, database: Optional[str] = None, table: Optional[str] = None) -> int:
        """
        Invalidate cached schema information.
        
        Args:
            database: Optional database name to invalidate (invalidates all if None)
            table: Optional table name to invalidate (requires database)
            
        Returns:
            Number of cache entries invalidated
        """
        if table and not database:
            raise ValueError("Database name is required when invalidating table cache")
        
        if database and table:
            # Invalidate specific table schema
            pattern = CacheKeyGenerator.schema_pattern(database, table)
        elif database:
            # Invalidate all cache entries for a database
            patterns = [
                CacheKeyGenerator.tables_pattern(database),
                CacheKeyGenerator.schema_pattern(database),
                CacheKeyGenerator.sample_data_pattern(database)
            ]
            total_invalidated = 0
            for pattern in patterns:
                total_invalidated += self.cache_manager.invalidate(pattern)
            return total_invalidated
        else:
            # Invalidate all schema-related cache entries
            patterns = [
                CacheKeyGenerator.database_pattern(),
                CacheKeyGenerator.tables_pattern(),
                CacheKeyGenerator.schema_pattern(),
                CacheKeyGenerator.sample_data_pattern()
            ]
            total_invalidated = 0
            for pattern in patterns:
                total_invalidated += self.cache_manager.invalidate(pattern)
            return total_invalidated
        
        return self.cache_manager.invalidate(pattern)
    
    def get_sample_data(self, database: str, table: str, limit: int = 10, 
                       masked_columns: Optional[List[str]] = None) -> 'SampleDataResult':
        """
        Retrieve sample data from a table with configurable row limits and column masking.
        
        Uses TABLESAMPLE for large tables with fallback to LIMIT with ORDER BY for consistent results.
        Supports column masking for sensitive data protection.
        
        Args:
            database: Database name
            table: Table name
            limit: Number of sample rows (1-100, default 10)
            masked_columns: Optional list of column names to mask
            
        Returns:
            SampleDataResult object with sample data and metadata
            
        Raises:
            ValueError: If limit is outside valid range (1-100)
            Exception: If database query fails or table doesn't exist
        """
        # Validate limit parameter
        if not 1 <= limit <= 100:
            raise ValueError(f"Sample limit must be between 1 and 100, got {limit}")
        
        # Initialize masked columns list
        if masked_columns is None:
            masked_columns = []
        
        cache_key = CacheKeyGenerator.sample_data_key(database, table, limit)
        
        # Try to get from cache first (only if no column masking)
        if not masked_columns:
            cached_result = self.cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Retrieved sample data for table '{database}.{table}' from cache")
                return cached_result
        
        start_time = time.time()
        
        try:
            logger.info(f"Retrieving sample data for table '{database}.{table}' (limit: {limit})")
            
            # First, get table row count and column information
            table_info = self._get_table_row_count(database, table)
            total_rows = table_info.get('row_count', 0)
            
            # Get column names for the table
            columns_info = self._get_column_info(database, table)
            all_columns = [col.name for col in columns_info]
            
            if not all_columns:
                raise Exception(f"Table '{database}.{table}' has no columns or does not exist")
            
            # Determine sampling method based on table size
            sampling_method, query = self._build_sample_query(
                database, table, all_columns, limit, total_rows, masked_columns
            )
            
            # Execute the sample query
            results = self.db_manager.execute_query(query, fetch_all=True)
            
            # Process results and apply column masking
            processed_rows = self._process_sample_rows(results, masked_columns)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Create sample data result
            sample_result = SampleDataResult(
                database=database,
                table=table,
                columns=all_columns,
                rows=processed_rows,
                row_count=len(processed_rows),
                total_table_rows=total_rows,
                execution_time_ms=execution_time_ms,
                sampling_method=sampling_method,
                masked_columns=masked_columns.copy()
            )
            
            # Cache the results only if no column masking was applied
            if not masked_columns:
                self.cache_manager.set(cache_key, sample_result)
            
            logger.info(f"Retrieved {len(processed_rows)} sample rows for table '{database}.{table}' "
                       f"using {sampling_method} in {sample_result.get_formatted_execution_time()}")
            
            return sample_result
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            logger.error(f"Failed to retrieve sample data for table '{database}.{table}': {error_msg}")
            
            # Return error result with available information
            return SampleDataResult(
                database=database,
                table=table,
                columns=[],
                rows=[],
                row_count=0,
                total_table_rows=None,
                execution_time_ms=execution_time_ms,
                sampling_method='ERROR',
                masked_columns=masked_columns.copy() if masked_columns else [],
                error=error_msg
            )
    
    def _get_table_row_count(self, database: str, table: str) -> Dict[str, Any]:
        """
        Get approximate row count for a table from INFORMATION_SCHEMA.
        
        Args:
            database: Database name
            table: Table name
            
        Returns:
            Dictionary with table statistics
        """
        query = """
            SELECT 
                TABLE_ROWS as row_count,
                ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as size_mb
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        """
        
        result = self.db_manager.execute_query(query, params=(database, table), fetch_one=True)
        
        if result:
            return {
                'row_count': result.get('row_count', 0) or 0,
                'size_mb': result.get('size_mb', 0) or 0
            }
        else:
            return {'row_count': 0, 'size_mb': 0}
    
    def _build_sample_query(self, database: str, table: str, columns: List[str], 
                           limit: int, total_rows: int, masked_columns: List[str]) -> tuple[str, str]:
        """
        Build the appropriate sample query based on table size and requirements.
        
        Args:
            database: Database name
            table: Table name
            columns: List of column names
            limit: Number of rows to sample
            total_rows: Total number of rows in table
            masked_columns: List of columns to mask
            
        Returns:
            Tuple of (sampling_method, query_string)
        """
        # Build column selection with masking
        column_selections = []
        for col in columns:
            if col in masked_columns:
                # Mask sensitive columns with placeholder values
                column_selections.append(f"'***MASKED***' as `{col}`")
            else:
                column_selections.append(f"`{col}`")
        
        column_list = ", ".join(column_selections)
        table_ref = f"`{database}`.`{table}`"
        
        # Choose sampling strategy based on table size
        if total_rows == 0:
            # Empty table - just return basic query
            sampling_method = "LIMIT_EMPTY"
            query = f"SELECT {column_list} FROM {table_ref} LIMIT {limit}"
            
        elif total_rows > 10000:
            # Large table - try TABLESAMPLE first, fallback to random sampling
            try:
                # TiDB supports TABLESAMPLE SYSTEM
                sampling_method = "TABLESAMPLE"
                # Calculate sample percentage to get approximately the desired number of rows
                sample_percent = min(100, max(0.1, (limit / total_rows) * 100 * 2))  # 2x for safety
                query = f"""
                    SELECT {column_list} 
                    FROM {table_ref} 
                    TABLESAMPLE SYSTEM ({sample_percent}) 
                    LIMIT {limit}
                """
            except:
                # Fallback to random sampling with ORDER BY RAND()
                sampling_method = "LIMIT_RANDOM"
                query = f"""
                    SELECT {column_list} 
                    FROM {table_ref} 
                    ORDER BY RAND() 
                    LIMIT {limit}
                """
        else:
            # Small to medium table - use ORDER BY with primary key or first column for consistency
            sampling_method = "LIMIT_ORDER_BY"
            # Try to order by primary key for consistency, fallback to first column
            order_column = columns[0] if columns else "*"
            query = f"""
                SELECT {column_list} 
                FROM {table_ref} 
                ORDER BY `{order_column}` 
                LIMIT {limit}
            """
        
        return sampling_method, query
    
    def _process_sample_rows(self, raw_rows: List[Dict[str, Any]], 
                           masked_columns: List[str]) -> List[Dict[str, Any]]:
        """
        Process raw database rows and apply any additional masking if needed.
        
        Args:
            raw_rows: Raw rows from database query
            masked_columns: List of columns that should be masked
            
        Returns:
            Processed rows with masking applied
        """
        if not raw_rows:
            return []
        
        processed_rows = []
        for row in raw_rows:
            processed_row = {}
            for key, value in row.items():
                if key in masked_columns:
                    # Additional masking for sensitive data types
                    processed_row[key] = self._mask_sensitive_value(value)
                else:
                    # Convert datetime objects to strings for JSON serialization
                    if isinstance(value, datetime):
                        processed_row[key] = value.isoformat()
                    else:
                        processed_row[key] = value
            processed_rows.append(processed_row)
        
        return processed_rows
    
    def _mask_sensitive_value(self, value: Any) -> str:
        """
        Apply appropriate masking to sensitive values based on their type.
        
        Args:
            value: Original value to mask
            
        Returns:
            Masked string representation
        """
        if value is None:
            return None
        
        # Convert to string for analysis
        str_value = str(value)
        
        # Different masking strategies based on content patterns
        if '@' in str_value and '.' in str_value:
            # Looks like email
            return "***@***.***"
        elif len(str_value) >= 10 and str_value.isdigit():
            # Looks like phone number or ID
            return "***-***-****"
        elif len(str_value) >= 8:
            # Long string - show first and last characters
            return f"{str_value[:2]}***{str_value[-2:]}"
        else:
            # Short string - completely mask
            return "***MASKED***"

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring and debugging.
        
        Returns:
            Dictionary with cache statistics
        """
        return self.cache_manager.get_stats()