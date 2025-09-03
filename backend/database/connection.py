"""
Database connection utilities using pure PyMySQL for TiDB Cloud.
No SQLAlchemy dependencies - pure PyMySQL implementation.
"""

import os
import logging
from typing import Optional, Dict, Any, List, Tuple
from contextlib import contextmanager
import pymysql
from pymysql.cursors import DictCursor
from pymysql import Connection
import time
from functools import wraps

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
    """Pure PyMySQL database manager for TiDB Cloud"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or get_cached_config()
    
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


def close_database():
    """Close global database connections (no-op for PyMySQL as connections are per-request)"""
    global _db_manager, _cached_config
    _db_manager = None
    _cached_config = None
    logger.info("Database manager and cached config reset")


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