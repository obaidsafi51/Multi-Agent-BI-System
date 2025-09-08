"""
Database connection utilities using pure PyMySQL for TiDB Cloud.
No SQLAlchemy dependencies - pure PyMySQL implementation.
Enhanced with MCP client integration for schema operations.
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from contextlib import contextmanager, asynccontextmanager
import pymysql
from pymysql.cursors import DictCursor
from pymysql import Connection
import time
from functools import wraps

# Import MCP schema management components
try:
    from schema_management import (
        MCPSchemaManager, EnhancedMCPClient, MCPSchemaConfig,
        SchemaValidationConfig, DatabaseInfo, TableInfo, TableSchema
    )
except ImportError:
    # Fallback for when running as module
    try:
        from backend.schema_management import (
            MCPSchemaManager, EnhancedMCPClient, MCPSchemaConfig,
            SchemaValidationConfig, DatabaseInfo, TableInfo, TableSchema
        )
    except ImportError:
        # If schema management is not available, disable MCP integration
        logger.warning("Schema management module not available, MCP integration disabled")
        MCPSchemaManager = None
        EnhancedMCPClient = None
        MCPSchemaConfig = None
        SchemaValidationConfig = None
        DatabaseInfo = None
        TableInfo = None
        TableSchema = None

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration settings for TiDB Cloud compatibility"""
    
    def __init__(self):
        self.host = os.getenv("TIDB_HOST", "localhost")
        self.port = int(os.getenv("TIDB_PORT", "4000"))
        self.user = os.getenv("TIDB_USER", "root")
        self.password = os.getenv("TIDB_PASSWORD", "")
        self.database = os.getenv("TIDB_DATABASE", "ai_cfo_bi")
        
        # SSL Configuration for TiDB Cloud
        self.ssl_ca = os.getenv("TIDB_SSL_CA", os.getenv("CA_PATH"))
        self.ssl_disabled = os.getenv("TIDB_SSL_DISABLED", "false").lower() == "true"
        self.ssl_verify_cert = os.getenv("TIDB_SSL_VERIFY_CERT", "true").lower() == "true"
        self.ssl_verify_identity = os.getenv("TIDB_SSL_VERIFY_IDENTITY", "true").lower() == "true"
        
        # Query settings
        self.query_timeout = int(os.getenv("DB_QUERY_TIMEOUT", "30"))
        self.retry_attempts = int(os.getenv("DB_RETRY_ATTEMPTS", "3"))
        self.retry_delay = float(os.getenv("DB_RETRY_DELAY", "1.0"))
        
        # TiDB specific settings
        self.autocommit = os.getenv("TIDB_AUTOCOMMIT", "true").lower() == "true"
    
    @property
    def pymysql_config(self) -> Dict[str, Any]:
        """Generate PyMySQL connection configuration dict"""
        config = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "autocommit": self.autocommit,
            "cursorclass": DictCursor,
            "charset": "utf8mb4",
            "connect_timeout": self.query_timeout,
        }
        
        # Add SSL configuration for TiDB Cloud
        if not self.ssl_disabled:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            config["ssl"] = ssl_context
            
            # Legacy SSL options (for compatibility)
            if self.ssl_ca:
                config["ssl_ca"] = self.ssl_ca
            if self.ssl_verify_cert:
                config["ssl_verify_cert"] = True
            if self.ssl_verify_identity:
                config["ssl_verify_identity"] = True
        
        return config


class DatabaseManager:
    """Pure PyMySQL database manager for TiDB Cloud with MCP integration"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None, enable_mcp: bool = True):
        self.config = config or get_cached_config()
        self.enable_mcp = enable_mcp
        
        # Initialize MCP components if enabled
        self.mcp_schema_manager: Optional[MCPSchemaManager] = None
        self.mcp_client: Optional[EnhancedMCPClient] = None
        self._mcp_connected = False
        self._mcp_connection_pool_size = 3
        self._mcp_connection_attempts = 0
        self._last_mcp_health_check = 0
        self._mcp_health_check_interval = 30  # seconds
        
        if self.enable_mcp and MCPSchemaManager is not None:
            try:
                mcp_config = MCPSchemaConfig.from_env()
                self.mcp_schema_manager = MCPSchemaManager(mcp_config)
                self.mcp_client = self.mcp_schema_manager.client
                logger.info("MCP integration enabled for DatabaseManager")
            except Exception as e:
                logger.warning(f"Failed to initialize MCP integration: {e}")
                self.enable_mcp = False
        elif self.enable_mcp and MCPSchemaManager is None:
            logger.warning("MCP schema management not available, disabling MCP integration")
            self.enable_mcp = False
    
    async def connect_mcp(self) -> bool:
        """
        Connect to MCP server for schema operations with retry logic.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.enable_mcp or not self.mcp_schema_manager:
            return False
        
        max_attempts = 3
        base_delay = 1.0
        
        for attempt in range(max_attempts):
            try:
                self._mcp_connection_attempts += 1
                self._mcp_connected = await self.mcp_schema_manager.connect()
                
                if self._mcp_connected:
                    logger.info(f"Successfully connected to MCP server (attempt {attempt + 1})")
                    self._last_mcp_health_check = time.time()
                    return True
                else:
                    logger.warning(f"Failed to connect to MCP server (attempt {attempt + 1})")
                    
            except Exception as e:
                logger.error(f"MCP connection failed (attempt {attempt + 1}): {e}")
                
            # Exponential backoff for retries
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                logger.info(f"Retrying MCP connection in {delay} seconds...")
                await asyncio.sleep(delay)
        
        self._mcp_connected = False
        logger.error(f"Failed to connect to MCP server after {max_attempts} attempts")
        return False
    
    async def disconnect_mcp(self):
        """Disconnect from MCP server."""
        if self.mcp_schema_manager:
            await self.mcp_schema_manager.disconnect()
            self._mcp_connected = False
            logger.info("Disconnected from MCP server")
    
    async def mcp_health_check(self) -> bool:
        """
        Check MCP server health with caching to avoid excessive checks.
        
        Returns:
            True if MCP server is healthy, False otherwise
        """
        if not self.enable_mcp or not self.mcp_schema_manager:
            return False
        
        # Use cached health check result if recent
        current_time = time.time()
        if (current_time - self._last_mcp_health_check) < self._mcp_health_check_interval:
            return self._mcp_connected
        
        try:
            health_status = await self.mcp_schema_manager.health_check()
            self._mcp_connected = health_status
            self._last_mcp_health_check = current_time
            
            if not health_status:
                logger.warning("MCP server health check failed, will attempt reconnection")
            
            return health_status
            
        except Exception as e:
            logger.error(f"MCP health check failed: {e}")
            self._mcp_connected = False
            self._last_mcp_health_check = current_time
            return False
    
    @contextmanager
    def get_connection(self, autocommit: Optional[bool] = None):
        """Get PyMySQL connection with proper cleanup"""
        config = self.config.pymysql_config.copy()
        if autocommit is not None:
            config["autocommit"] = autocommit
        
        connection = None
        try:
            connection = pymysql.connect(**config)
            yield connection
        except Exception as e:
            if connection and not config.get("autocommit", True):
                connection.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    @asynccontextmanager
    async def get_mcp_connection(self):
        """
        Get MCP connection with automatic connection management and retry logic.
        
        Yields:
            EnhancedMCPClient: Connected MCP client
        """
        if not self.enable_mcp or not self.mcp_client:
            raise RuntimeError("MCP integration not enabled or not available")
        
        # Check health and reconnect if necessary
        if not await self.mcp_health_check():
            logger.info("MCP connection unhealthy, attempting to reconnect...")
            if not await self.connect_mcp():
                raise RuntimeError("Failed to establish MCP connection")
        
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                yield self.mcp_client
                return  # Success, exit the retry loop
                
            except Exception as e:
                logger.error(f"MCP operation failed (attempt {attempt + 1}): {e}")
                
                # If this is not the last attempt, try to reconnect
                if attempt < max_retries:
                    logger.info("Attempting to reconnect MCP client...")
                    try:
                        await self.connect_mcp()
                        if not self._mcp_connected:
                            raise RuntimeError("Reconnection failed")
                    except Exception as reconnect_error:
                        logger.error(f"MCP reconnection failed: {reconnect_error}")
                        if attempt == max_retries - 1:  # Last attempt
                            raise
                else:
                    # Last attempt failed, re-raise the original exception
                    raise
    
    def retry_on_disconnect(self, max_retries: int = None):
        """Decorator for retrying database operations on disconnect"""
        max_retries = max_retries or self.config.retry_attempts
        
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except (pymysql.Error, pymysql.MySQLError) as e:
                        last_exception = e
                        if attempt < max_retries:
                            wait_time = self.config.retry_delay * (2 ** attempt)
                            logger.warning(
                                f"Database operation failed (attempt {attempt + 1}), "
                                f"retrying in {wait_time}s: {e}"
                            )
                            time.sleep(wait_time)
                        else:
                            logger.error(f"Database operation failed after {max_retries} retries: {e}")
                
                raise last_exception
            return wrapper
        return decorator
    
    def execute_query(self, query: str, params: Tuple = None, fetch_one: bool = False, fetch_all: bool = True) -> Any:
        """Execute a query with error handling and retries"""
        @self.retry_on_disconnect()
        def _execute():
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params or ())
                    
                    # Check if query returns data (SELECT, SHOW, DESCRIBE, EXPLAIN, etc.)
                    query_upper = query.strip().upper()
                    if any(query_upper.startswith(cmd) for cmd in ['SELECT', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN', 'WITH']):
                        if fetch_one:
                            return cursor.fetchone()
                        elif fetch_all:
                            return cursor.fetchall()
                        else:
                            return cursor
                    else:
                        conn.commit()
                        return cursor.rowcount
        
        return _execute()
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """Execute many queries with error handling and retries"""
        @self.retry_on_disconnect()
        def _execute():
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(query, params_list)
                    conn.commit()
                    return cursor.rowcount
        
        return _execute()
    
    def execute_transaction(self, queries: List[Tuple[str, Tuple]]) -> bool:
        """Execute multiple queries in a transaction"""
        @self.retry_on_disconnect()
        def _execute():
            with self.get_connection(autocommit=False) as conn:
                try:
                    with conn.cursor() as cursor:
                        for query, params in queries:
                            cursor.execute(query, params or ())
                    conn.commit()
                    return True
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Transaction failed: {e}")
                    raise
        
        return _execute()
    
    def health_check(self) -> bool:
        """Check database connection health"""
        try:
            result = self.execute_query("SELECT 1 as test", fetch_one=True)
            return result and result.get("test") == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def discover_databases_mcp(self) -> List[DatabaseInfo]:
        """
        Discover databases using MCP server.
        
        Returns:
            List of database information from MCP server
        """
        if not self.enable_mcp or not self.mcp_schema_manager:
            logger.warning("MCP not enabled, falling back to direct database query")
            return await self._discover_databases_fallback()
        
        try:
            return await self.mcp_schema_manager.discover_databases()
        except Exception as e:
            logger.error(f"MCP database discovery failed: {e}")
            if self.mcp_schema_manager and self.mcp_schema_manager.mcp_config.fallback_enabled:
                logger.info("Using fallback database discovery")
                return await self._discover_databases_fallback()
            raise
    
    async def get_tables_mcp(self, database: str) -> List[TableInfo]:
        """
        Get tables using MCP server.
        
        Args:
            database: Database name
            
        Returns:
            List of table information from MCP server
        """
        if not self.enable_mcp or not self.mcp_schema_manager:
            logger.warning("MCP not enabled, falling back to direct database query")
            return await self._get_tables_fallback(database)
        
        try:
            return await self.mcp_schema_manager.get_tables(database)
        except Exception as e:
            logger.error(f"MCP table discovery failed for database {database}: {e}")
            if self.mcp_schema_manager and self.mcp_schema_manager.mcp_config.fallback_enabled:
                logger.info("Using fallback table discovery")
                return await self._get_tables_fallback(database)
            raise
    
    async def get_table_schema_mcp(self, database: str, table: str) -> Optional[TableSchema]:
        """
        Get table schema using MCP server.
        
        Args:
            database: Database name
            table: Table name
            
        Returns:
            Table schema from MCP server or None if not found
        """
        if not self.enable_mcp or not self.mcp_schema_manager:
            logger.warning("MCP not enabled, falling back to direct database query")
            return await self._get_table_schema_fallback(database, table)
        
        try:
            return await self.mcp_schema_manager.get_table_schema(database, table)
        except Exception as e:
            logger.error(f"MCP schema discovery failed for {database}.{table}: {e}")
            if self.mcp_schema_manager and self.mcp_schema_manager.mcp_config.fallback_enabled:
                logger.info("Using fallback schema discovery")
                return await self._get_table_schema_fallback(database, table)
            raise
    
    async def execute_query_mcp(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute query using MCP server with comprehensive error handling.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Query results from MCP server
        """
        if not self.enable_mcp or not self.mcp_client:
            logger.warning("MCP not enabled, falling back to direct database execution")
            # Convert dict params to tuple for direct execution
            tuple_params = tuple(params.values()) if params else None
            return self.execute_query(query, tuple_params)
        
        start_time = time.time()
        
        try:
            logger.debug(f"Executing MCP query: {query[:100]}{'...' if len(query) > 100 else ''}")
            
            async with self.get_mcp_connection() as client:
                result = await client._send_request("execute_query_tool", {
                    "query": query,
                    "params": params or {}
                })
                
                execution_time = time.time() - start_time
                
                if result and result.get('error'):
                    logger.error(f"MCP query execution failed after {execution_time:.2f}s: {result['error']}")
                    raise Exception(f"MCP query execution failed: {result['error']}")
                
                data = result.get('data', []) if result else []
                logger.debug(f"MCP query completed in {execution_time:.2f}s, returned {len(data) if isinstance(data, list) else 'N/A'} rows")
                
                return data
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"MCP query execution failed after {execution_time:.2f}s: {e}")
            
            if self.mcp_schema_manager and self.mcp_schema_manager.mcp_config.fallback_enabled:
                logger.info("Using fallback query execution")
                try:
                    tuple_params = tuple(params.values()) if params else None
                    fallback_result = self.execute_query(query, tuple_params)
                    logger.info(f"Fallback query execution successful")
                    return fallback_result
                except Exception as fallback_error:
                    logger.error(f"Fallback query execution also failed: {fallback_error}")
                    raise fallback_error
            raise
    
    async def get_sample_data_mcp(self, database: str, table: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get sample data using MCP server.
        
        Args:
            database: Database name
            table: Table name
            limit: Number of rows to retrieve
            
        Returns:
            Sample data from MCP server
        """
        if not self.enable_mcp or not self.mcp_client:
            logger.warning("MCP not enabled, falling back to direct database query")
            return await self._get_sample_data_fallback(database, table, limit)
        
        try:
            async with self.get_mcp_connection() as client:
                result = await client._send_request("get_sample_data_tool", {
                    "database": database,
                    "table": table,
                    "limit": limit
                })
                
                if result and result.get('error'):
                    raise Exception(f"MCP sample data retrieval failed: {result['error']}")
                
                return result.get('data', []) if result else []
                
        except Exception as e:
            logger.error(f"MCP sample data retrieval failed for {database}.{table}: {e}")
            if self.mcp_schema_manager and self.mcp_schema_manager.mcp_config.fallback_enabled:
                logger.info("Using fallback sample data retrieval")
                return await self._get_sample_data_fallback(database, table, limit)
            raise
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information"""
        info = {}
        try:
            # Get version
            version_result = self.execute_query("SELECT VERSION() as version", fetch_one=True)
            info["version"] = version_result["version"] if version_result else "Unknown"
            
            # Check if TiDB (handle cases where @@tidb_version is not available)
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT @@tidb_version as tidb_version")
                        tidb_result = cursor.fetchone()
                        info["tidb_version"] = tidb_result["tidb_version"] if tidb_result else None
            except pymysql.Error as e:
                logger.debug(f"TiDB version query failed: {e}")
                info["tidb_version"] = "TiDB version unavailable"
            
            # Get current database
            db_result = self.execute_query("SELECT DATABASE() as current_db", fetch_one=True)
            info["current_database"] = db_result["current_db"] if db_result else None
            
            # Get available databases
            databases = self.execute_query("SHOW DATABASES")
            info["available_databases"] = [db["Database"] for db in databases] if databases else []
            
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            info["error"] = str(e)
        
        return info
    
    # Fallback methods for when MCP is not available
    async def _discover_databases_fallback(self) -> List[DatabaseInfo]:
        """Fallback database discovery using direct SQL queries."""
        try:
            databases = self.execute_query("SHOW DATABASES")
            db_list = []
            
            for db in databases:
                db_name = db["Database"]
                # Skip system databases
                if db_name.lower() in ['information_schema', 'performance_schema', 'mysql', 'sys']:
                    continue
                
                # Get table count
                table_count_result = self.execute_query(
                    "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = %s",
                    (db_name,),
                    fetch_one=True
                )
                table_count = table_count_result["count"] if table_count_result else 0
                
                db_list.append(DatabaseInfo(
                    name=db_name,
                    charset="utf8mb4",  # Default charset
                    collation="utf8mb4_general_ci",  # Default collation
                    accessible=True,
                    table_count=table_count
                ))
            
            logger.info(f"Discovered {len(db_list)} databases using fallback method")
            return db_list
            
        except Exception as e:
            logger.error(f"Fallback database discovery failed: {e}")
            return []
    
    async def _get_tables_fallback(self, database: str) -> List[TableInfo]:
        """Fallback table discovery using direct SQL queries."""
        try:
            tables = self.execute_query(f"SHOW TABLES FROM `{database}`")
            table_list = []
            
            for table in tables:
                table_name = list(table.values())[0]  # Get table name from result
                
                # Get table info
                table_info_result = self.execute_query(
                    f"SHOW TABLE STATUS FROM `{database}` LIKE %s",
                    (table_name,),
                    fetch_one=True
                )
                
                if table_info_result:
                    # Convert data length to MB
                    data_length = table_info_result.get("Data_length", 0) or 0
                    size_mb = float(data_length) / (1024 * 1024) if data_length else 0.0
                    
                    table_list.append(TableInfo(
                        name=table_name,
                        type=table_info_result.get("Comment", "BASE TABLE"),
                        engine=table_info_result.get("Engine", "InnoDB"),
                        rows=table_info_result.get("Rows", 0) or 0,
                        size_mb=size_mb,
                        comment=table_info_result.get("Comment"),
                        created_at=table_info_result.get("Create_time"),
                        updated_at=table_info_result.get("Update_time")
                    ))
            
            logger.info(f"Discovered {len(table_list)} tables in {database} using fallback method")
            return table_list
            
        except Exception as e:
            logger.error(f"Fallback table discovery failed for database {database}: {e}")
            return []
    
    async def _get_table_schema_fallback(self, database: str, table: str) -> Optional[TableSchema]:
        """Fallback table schema discovery using direct SQL queries."""
        try:
            # Get column information
            columns_result = self.execute_query(
                "SELECT * FROM information_schema.columns WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
                (database, table)
            )
            
            if not columns_result:
                return None
            
            try:
                from schema_management.models import ColumnInfo, IndexInfo, ForeignKeyInfo
            except ImportError:
                try:
                    from backend.schema_management.models import ColumnInfo, IndexInfo, ForeignKeyInfo
                except ImportError:
                    logger.error("Schema management models not available for fallback schema discovery")
                    return None
            
            columns = []
            primary_keys = []
            
            for col in columns_result:
                is_primary = col.get("COLUMN_KEY") == "PRI"
                if is_primary:
                    primary_keys.append(col["COLUMN_NAME"])
                
                columns.append(ColumnInfo(
                    name=col["COLUMN_NAME"],
                    data_type=col["DATA_TYPE"],
                    is_nullable=col["IS_NULLABLE"] == "YES",
                    default_value=col.get("COLUMN_DEFAULT"),
                    is_primary_key=is_primary,
                    is_foreign_key=col.get("COLUMN_KEY") == "MUL",
                    comment=col.get("COLUMN_COMMENT"),
                    max_length=col.get("CHARACTER_MAXIMUM_LENGTH"),
                    precision=col.get("NUMERIC_PRECISION"),
                    scale=col.get("NUMERIC_SCALE"),
                    is_auto_increment=col.get("EXTRA", "").lower().find("auto_increment") >= 0,
                    character_set=col.get("CHARACTER_SET_NAME"),
                    collation=col.get("COLLATION_NAME")
                ))
            
            # Get index information
            indexes_result = self.execute_query(f"SHOW INDEX FROM `{database}`.`{table}`")
            indexes = []
            index_dict = {}
            
            for idx in indexes_result:
                index_name = idx["Key_name"]
                if index_name not in index_dict:
                    index_dict[index_name] = {
                        "name": index_name,
                        "columns": [],
                        "is_unique": idx["Non_unique"] == 0,
                        "is_primary": index_name == "PRIMARY",
                        "index_type": idx.get("Index_type", "BTREE"),
                        "comment": idx.get("Index_comment", "")
                    }
                index_dict[index_name]["columns"].append(idx["Column_name"])
            
            for idx_info in index_dict.values():
                indexes.append(IndexInfo(**idx_info))
            
            # Get foreign key information (simplified)
            foreign_keys = []  # Would need more complex query for full FK info
            
            return TableSchema(
                database=database,
                table=table,
                columns=columns,
                indexes=indexes,
                primary_keys=primary_keys,
                foreign_keys=foreign_keys,
                constraints=[]
            )
            
        except Exception as e:
            logger.error(f"Fallback schema discovery failed for {database}.{table}: {e}")
            return None
    
    async def _get_sample_data_fallback(self, database: str, table: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fallback sample data retrieval using direct SQL queries."""
        try:
            result = self.execute_query(f"SELECT * FROM `{database}`.`{table}` LIMIT %s", (limit,))
            return result if result else []
        except Exception as e:
            logger.error(f"Fallback sample data retrieval failed for {database}.{table}: {e}")
            return []
    
    async def validate_table_exists_mcp(self, database: str, table: str) -> bool:
        """
        Validate that a table exists using MCP server.
        
        Args:
            database: Database name
            table: Table name
            
        Returns:
            True if table exists, False otherwise
        """
        if not self.enable_mcp or not self.mcp_schema_manager:
            logger.warning("MCP not enabled, falling back to direct validation")
            return await self._validate_table_exists_fallback(database, table)
        
        try:
            return await self.mcp_schema_manager.validate_table_exists(database, table)
        except Exception as e:
            logger.error(f"MCP table validation failed for {database}.{table}: {e}")
            if self.mcp_schema_manager and self.mcp_schema_manager.mcp_config.fallback_enabled:
                logger.info("Using fallback table validation")
                return await self._validate_table_exists_fallback(database, table)
            return False
    
    async def _validate_table_exists_fallback(self, database: str, table: str) -> bool:
        """Fallback table existence validation using direct SQL queries."""
        try:
            result = self.execute_query(
                "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                (database, table),
                fetch_one=True
            )
            return result and result["count"] > 0
        except Exception as e:
            logger.error(f"Fallback table validation failed for {database}.{table}: {e}")
            return False
    
    async def validate_query_mcp(self, query: str) -> Dict[str, Any]:
        """
        Validate a SQL query using MCP server.
        
        Args:
            query: SQL query to validate
            
        Returns:
            Validation result with is_valid, errors, warnings, etc.
        """
        if not self.enable_mcp or not self.mcp_client:
            logger.warning("MCP not enabled, performing basic validation")
            return await self._validate_query_fallback(query)
        
        try:
            async with self.get_mcp_connection() as client:
                validation_result = await client.validate_query_against_schema(query)
                
                return {
                    "is_valid": validation_result.is_valid,
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                    "affected_tables": validation_result.affected_tables,
                    "estimated_rows": validation_result.estimated_rows,
                    "execution_plan": validation_result.execution_plan
                }
                
        except Exception as e:
            logger.error(f"MCP query validation failed: {e}")
            if self.mcp_schema_manager and self.mcp_schema_manager.mcp_config.fallback_enabled:
                logger.info("Using fallback query validation")
                return await self._validate_query_fallback(query)
            return {
                "is_valid": False,
                "errors": [f"Validation failed: {str(e)}"],
                "warnings": [],
                "affected_tables": []
            }
    
    async def _validate_query_fallback(self, query: str) -> Dict[str, Any]:
        """Fallback query validation using basic SQL parsing."""
        try:
            # Basic validation - try to explain the query
            explain_query = f"EXPLAIN {query}"
            result = self.execute_query(explain_query)
            
            return {
                "is_valid": True,
                "errors": [],
                "warnings": ["Basic validation only - MCP server unavailable"],
                "affected_tables": [],
                "execution_plan": result
            }
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"Query validation failed: {str(e)}"],
                "warnings": [],
                "affected_tables": []
            }
    
    async def refresh_schema_cache_mcp(self, cache_type: str = "all") -> bool:
        """
        Refresh MCP schema cache.
        
        Args:
            cache_type: Type of cache to refresh
            
        Returns:
            True if refresh successful, False otherwise
        """
        if not self.enable_mcp or not self.mcp_schema_manager:
            logger.warning("MCP not enabled, cannot refresh schema cache")
            return False
        
        try:
            return await self.mcp_schema_manager.refresh_schema_cache(cache_type)
        except Exception as e:
            logger.error(f"Failed to refresh MCP schema cache: {e}")
            return False
    
    def get_mcp_cache_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get MCP cache statistics.
        
        Returns:
            Cache statistics or None if MCP not enabled
        """
        if not self.enable_mcp or not self.mcp_schema_manager:
            return None
        
        try:
            cache_stats = self.mcp_schema_manager.get_cache_stats()
            detailed_stats = self.mcp_schema_manager.get_detailed_cache_stats()
            
            return {
                "basic_stats": {
                    "total_entries": cache_stats.total_entries,
                    "hit_rate": cache_stats.hit_rate,
                    "miss_rate": cache_stats.miss_rate,
                    "eviction_count": cache_stats.eviction_count,
                    "memory_usage_mb": cache_stats.memory_usage_mb,
                    "oldest_entry_age_seconds": cache_stats.oldest_entry_age_seconds,
                    "newest_entry_age_seconds": cache_stats.newest_entry_age_seconds
                },
                "detailed_stats": detailed_stats,
                "connection_stats": {
                    "is_connected": self._mcp_connected,
                    "connection_attempts": self._mcp_connection_attempts,
                    "last_health_check": self._last_mcp_health_check
                }
            }
        except Exception as e:
            logger.error(f"Failed to get MCP cache stats: {e}")
            return None


# Module-level cached configuration to avoid repeated environment variable lookups
_cached_config: Optional[DatabaseConfig] = None


def get_cached_config() -> DatabaseConfig:
    """Get cached database configuration, creating it if necessary"""
    global _cached_config
    if _cached_config is None:
        _cached_config = DatabaseConfig()
    return _cached_config


def refresh_cached_config() -> DatabaseConfig:
    """Refresh the cached configuration (useful for testing or config changes)"""
    global _cached_config
    _cached_config = DatabaseConfig()
    return _cached_config


# Convenience functions that use the global DatabaseManager
@contextmanager
def tidb_connection(autocommit: bool = True):
    """
    Context manager for TiDB connections using the global DatabaseManager.
    
    This is a convenience function that delegates to DatabaseManager.get_connection()
    for consistent connection management and configuration.
    
    Args:
        autocommit: Whether to enable autocommit mode
        
    Yields:
        pymysql.Connection: Database connection with proper cleanup
        
    Example:
        with tidb_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM financial_overview")
                results = cursor.fetchall()
    """
    db_manager = get_database()
    with db_manager.get_connection(autocommit=autocommit) as connection:
        yield connection


def test_tidb_connection() -> bool:
    """
    Test TiDB connection health using the global DatabaseManager.
    
    This function uses the DatabaseManager's health_check method for consistency.
    
    Returns:
        bool: True if connection is healthy, False otherwise
    """
    db_manager = get_database()
    return db_manager.health_check()


def get_direct_connection(autocommit: bool = True) -> Connection:
    """
    Get a direct PyMySQL connection without context management.
    
    WARNING: This function returns a raw connection that must be manually closed.
    Use tidb_connection() context manager instead for automatic cleanup.
    
    This function is provided for special cases where you need direct connection
    control (e.g., long-running operations, custom connection pooling).
    
    Args:
        autocommit: Whether to enable autocommit mode
        
    Returns:
        pymysql.Connection: Raw database connection (must be closed manually)
        
    Example:
        conn = get_direct_connection()
        try:
            # Your database operations
            pass
        finally:
            conn.close()  # IMPORTANT: Always close manually
    """
    config = get_cached_config()
    pymysql_config = config.pymysql_config.copy()
    pymysql_config["autocommit"] = autocommit
    return pymysql.connect(**pymysql_config)


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def close_database():
    """Close global database connections and MCP connections"""
    global _db_manager, _cached_config
    if _db_manager:
        await _db_manager.disconnect_mcp()
    _db_manager = None
    _cached_config = None
    logger.info("Database manager and cached config reset")


# MCP-enabled convenience functions
async def discover_databases() -> List[DatabaseInfo]:
    """Discover databases using MCP server"""
    db = get_database()
    return await db.discover_databases_mcp()


async def get_tables(database: str) -> List[TableInfo]:
    """Get tables using MCP server"""
    db = get_database()
    return await db.get_tables_mcp(database)


async def get_table_schema(database: str, table: str) -> Optional[TableSchema]:
    """Get table schema using MCP server"""
    db = get_database()
    return await db.get_table_schema_mcp(database, table)


async def execute_query_mcp(query: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Execute query using MCP server"""
    db = get_database()
    return await db.execute_query_mcp(query, params)


async def get_sample_data(database: str, table: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get sample data using MCP server"""
    db = get_database()
    return await db.get_sample_data_mcp(database, table, limit)


async def connect_mcp() -> bool:
    """Connect to MCP server"""
    db = get_database()
    return await db.connect_mcp()


async def mcp_health_check() -> bool:
    """Check MCP server health"""
    db = get_database()
    return await db.mcp_health_check()


async def validate_table_exists(database: str, table: str) -> bool:
    """Validate table existence using MCP server"""
    db = get_database()
    return await db.validate_table_exists_mcp(database, table)


async def validate_query(query: str) -> Dict[str, Any]:
    """Validate SQL query using MCP server"""
    db = get_database()
    return await db.validate_query_mcp(query)


async def refresh_schema_cache(cache_type: str = "all") -> bool:
    """Refresh MCP schema cache"""
    db = get_database()
    return await db.refresh_schema_cache_mcp(cache_type)


def get_mcp_cache_stats() -> Optional[Dict[str, Any]]:
    """Get MCP cache statistics"""
    db = get_database()
    return db.get_mcp_cache_stats()


# Convenience functions for common operations
def execute_query(query: str, params: Tuple = None, fetch_one: bool = False) -> Any:
    """Execute a query using the global database manager"""
    db = get_database()
    return db.execute_query(query, params, fetch_one=fetch_one)


def execute_many(query: str, params_list: List[Tuple]) -> int:
    """Execute many queries using the global database manager"""
    db = get_database()
    return db.execute_many(query, params_list)


def execute_transaction(queries: List[Tuple[str, Tuple]]) -> bool:
    """Execute transaction using the global database manager"""
    db = get_database()
    return db.execute_transaction(queries)