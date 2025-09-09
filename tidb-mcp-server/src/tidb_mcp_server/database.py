"""
Database connection manager for TiDB MCP Server.
Provides direct database connections with proper error handling and configuration.
"""

import logging
import os
import pymysql
import ssl
import datetime
import decimal
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TiDBConnection:
    """
    TiDB connection manager with SSL support and error handling.
    """
    
    def __init__(self):
        """Initialize TiDB connection configuration."""
        self.config = self._load_config()
        self._connection = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load database configuration from environment variables."""
        return {
            "host": os.getenv("TIDB_HOST"),
            "port": int(os.getenv("TIDB_PORT", "4000")),
            "user": os.getenv("TIDB_USER"),
            "password": os.getenv("TIDB_PASSWORD"),
            "database": os.getenv("TIDB_DATABASE", "Agentic_BI"),
            "charset": "utf8mb4",
            "autocommit": True,
            "connect_timeout": 30,
            "read_timeout": 30,
            "write_timeout": 30,
        }
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for TiDB Cloud connections."""
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context
        except Exception as e:
            logger.warning(f"Failed to create SSL context: {e}")
            return None
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with proper cleanup."""
        connection = None
        try:
            # Create connection configuration
            connect_config = self.config.copy()
            
            # Add SSL configuration for TiDB Cloud
            ssl_context = self._create_ssl_context()
            if ssl_context:
                connect_config["ssl"] = ssl_context
            
            # Add cursor class for dict results
            connect_config["cursorclass"] = pymysql.cursors.DictCursor
            
            # Establish connection
            connection = pymysql.connect(**connect_config)
            logger.debug("Database connection established")
            
            yield connection
            
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection:
                connection.close()
                logger.debug("Database connection closed")
    
    def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1 as test")
                    result = cursor.fetchone()
                    return result and result.get("test") == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch_all: bool = True,
        fetch_one: bool = False
    ) -> Any:
        """Execute a query and return results."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Execute the query
                    cursor.execute(query, params or ())
                    
                    # Determine how to fetch results based on query type
                    query_upper = query.strip().upper()
                    
                    if any(query_upper.startswith(cmd) for cmd in [
                        'SELECT', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN', 'WITH'
                    ]):
                        if fetch_one:
                            result = cursor.fetchone()
                            return self._sanitize_result(result) if result else None
                        elif fetch_all:
                            results = cursor.fetchall()
                            return [self._sanitize_result(row) for row in results] if results else []
                        else:
                            return cursor
                    else:
                        # For non-SELECT queries, commit and return affected rows
                        conn.commit()
                        return cursor.rowcount
                        
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def _sanitize_result(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize database results to handle binary data and encoding issues."""
        if not isinstance(row, dict):
            return row
            
        sanitized = {}
        for key, value in row.items():
            if isinstance(value, bytes):
                # Handle binary data by encoding as base64 or converting to string safely
                try:
                    # Try to decode as UTF-8
                    sanitized[key] = value.decode('utf-8')
                except UnicodeDecodeError:
                    # If UTF-8 fails, encode as base64
                    import base64
                    sanitized[key] = base64.b64encode(value).decode('ascii')
                    logger.debug(f"Converted binary data to base64 for column: {key}")
            elif isinstance(value, (datetime.datetime, datetime.date)):
                # Convert datetime objects to ISO strings
                sanitized[key] = value.isoformat()
            elif isinstance(value, decimal.Decimal):
                # Convert decimal to float
                sanitized[key] = float(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """Execute multiple queries with parameters."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(query, params_list)
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            logger.error(f"Execute many failed: {e}")
            raise
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information."""
        info = {}
        try:
            # Get version
            version_result = self.execute_query("SELECT VERSION() as version", fetch_one=True)
            info["version"] = version_result["version"] if version_result else "Unknown"
            
            # Get current database
            db_result = self.execute_query("SELECT DATABASE() as current_db", fetch_one=True)
            info["current_database"] = db_result["current_db"] if db_result else None
            
            # Get available databases
            databases = self.execute_query("SHOW DATABASES")
            info["available_databases"] = [db["Database"] for db in databases] if databases else []
            
            # Check TiDB version (may not be available on all setups)
            try:
                tidb_result = self.execute_query("SELECT @@tidb_version as tidb_version", fetch_one=True)
                info["tidb_version"] = tidb_result["tidb_version"] if tidb_result else None
            except Exception:
                info["tidb_version"] = "TiDB version query not supported"
            
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            info["error"] = str(e)
        
        return info


class DatabaseManager:
    """
    Database manager compatible with the MCP server architecture.
    Provides the same interface as the backend DatabaseManager.
    """
    
    def __init__(self):
        """Initialize database manager."""
        self.tidb_connection = TiDBConnection()
        logger.info("DatabaseManager initialized for MCP server")
    
    def test_connection(self) -> bool:
        """Test database connection."""
        return self.tidb_connection.test_connection()
    
    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch_all: bool = True,
        fetch_one: bool = False
    ) -> Any:
        """Execute a query with the same interface as backend DatabaseManager."""
        return self.tidb_connection.execute_query(query, params, fetch_all, fetch_one)
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """Execute multiple queries."""
        return self.tidb_connection.execute_many(query, params_list)
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information."""
        return self.tidb_connection.get_database_info()
    
    def health_check(self) -> bool:
        """Check database health."""
        return self.test_connection()
    
    def close(self):
        """Close database connections (no-op for connection-per-request pattern)."""
        logger.debug("Database manager close called (no persistent connections)")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def close_database_manager():
    """Close global database manager."""
    global _db_manager
    if _db_manager:
        _db_manager.close()
        _db_manager = None
