"""
TiDB Connection Manager with SSL configuration and connection pooling.
Implements secure database connections with retry logic and health monitoring.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, AsyncGenerator
from urllib.parse import urlparse

import pymysql
from sqlalchemy import create_engine, text, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
import structlog

logger = structlog.get_logger(__name__)


class TiDBConnectionManager:
    """
    TiDB connection manager with SSL configuration, connection pooling,
    and health monitoring capabilities.
    """
    
    def __init__(self, database_url: str, **kwargs):
        """
        Initialize TiDB connection manager.
        
        Args:
            database_url: TiDB connection URL
            **kwargs: Additional configuration options
        """
        self.database_url = database_url
        self.engine = None
        self.async_engine = None
        self.session_factory = None
        self.is_connected = False
        
        # Configuration options
        self.config = {
            'pool_size': kwargs.get('pool_size', 10),
            'max_overflow': kwargs.get('max_overflow', 20),
            'pool_timeout': kwargs.get('pool_timeout', 30),
            'pool_recycle': kwargs.get('pool_recycle', 3600),
            'pool_pre_ping': kwargs.get('pool_pre_ping', True),
            'connect_timeout': kwargs.get('connect_timeout', 10),
            'read_timeout': kwargs.get('read_timeout', 30),
            'write_timeout': kwargs.get('write_timeout', 30),
            'ssl_disabled': kwargs.get('ssl_disabled', False),
            'ssl_verify_cert': kwargs.get('ssl_verify_cert', True),
            'ssl_verify_identity': kwargs.get('ssl_verify_identity', True),
        }
        
        # Health check configuration
        self.health_check_interval = kwargs.get('health_check_interval', 60)
        self.max_retries = kwargs.get('max_retries', 3)
        self.retry_delay = kwargs.get('retry_delay', 1)
        
        # Connection statistics
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'failed_connections': 0,
            'queries_executed': 0,
            'avg_query_time': 0.0
        }
    
    def _build_connection_url(self) -> str:
        """
        Build TiDB connection URL with SSL and connection parameters.
        
        Returns:
            Formatted connection URL with all parameters
        """
        parsed = urlparse(self.database_url)
        
        # Base connection parameters (PyMySQL compatible)
        params = {
            'charset': 'utf8mb4',
            'connect_timeout': self.config['connect_timeout'],
            'autocommit': False,
        }
        
        # For TiDB Cloud, we need SSL but don't use ssl_disabled parameter
        # Instead, we'll configure SSL through the ssl parameter later
        
        # Build parameter string
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        
        # Reconstruct URL
        if parsed.query:
            # Remove SSL-related parameters that may conflict with aiomysql
            existing_params = parsed.query
            # Filter out problematic SSL parameters
            filtered_params = []
            for param in existing_params.split('&'):
                if not any(ssl_param in param for ssl_param in ['ssl_disabled', 'ssl_verify_cert', 'ssl_verify_identity']):
                    filtered_params.append(param)
            
            if filtered_params:
                connection_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{'&'.join(filtered_params)}&{param_string}"
            else:
                connection_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{param_string}"
        else:
            connection_url = f"{self.database_url}?{param_string}"
        
        return connection_url
    
    async def initialize(self) -> None:
        """
        Initialize database connections and connection pools.
        """
        try:
            connection_url = self._build_connection_url()
            
            # For TiDB Cloud, we need to enable SSL for both async and sync engines
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # For async engine, we need to replace the driver properly
            async_url = connection_url
            if 'mysql+pymysql://' in async_url:
                async_url = async_url.replace('mysql+pymysql://', 'mysql+aiomysql://')
            elif 'mysql://' in async_url:
                async_url = async_url.replace('mysql://', 'mysql+aiomysql://')
            
            # Create async engine for main operations with SSL
            connect_args_async = {
                'ssl': ssl_context
            }
            
            self.async_engine = create_async_engine(
                async_url,
                pool_size=self.config['pool_size'],
                max_overflow=self.config['max_overflow'],
                pool_timeout=self.config['pool_timeout'],
                pool_recycle=self.config['pool_recycle'],
                pool_pre_ping=self.config['pool_pre_ping'],
                echo=False,  # Set to True for SQL debugging
                connect_args=connect_args_async
            )
            
            # For sync engine, ensure we use pymysql with SSL
            sync_url = connection_url
            if 'mysql+aiomysql://' in sync_url:
                sync_url = sync_url.replace('mysql+aiomysql://', 'mysql+pymysql://')
            elif 'mysql://' in sync_url and 'mysql+' not in sync_url:
                sync_url = sync_url.replace('mysql://', 'mysql+pymysql://')
            
            # Create sync engine with SSL for health checks
            connect_args_sync = {
                'ssl': ssl_context
            }
            
            self.engine = create_engine(
                sync_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_timeout=self.config['pool_timeout'],
                pool_recycle=self.config['pool_recycle'],
                pool_pre_ping=self.config['pool_pre_ping'],
                echo=False,
                connect_args=connect_args_sync
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection
            await self._test_connection()
            self.is_connected = True
            
            # Set up event listeners for connection monitoring
            self._setup_event_listeners()
            
            logger.info("TiDB connection manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize TiDB connection: {str(e)}")
            raise
    
    def _setup_event_listeners(self) -> None:
        """Set up SQLAlchemy event listeners for connection monitoring."""
        
        @event.listens_for(self.async_engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            self.stats['total_connections'] += 1
            self.stats['active_connections'] += 1
            logger.debug("New database connection established")
        
        @event.listens_for(self.async_engine.sync_engine, "close")
        def on_close(dbapi_connection, connection_record):
            self.stats['active_connections'] = max(0, self.stats['active_connections'] - 1)
            logger.debug("Database connection closed")
        
        @event.listens_for(self.async_engine.sync_engine, "handle_error")
        def on_error(exception_context):
            self.stats['failed_connections'] += 1
            logger.error(f"Database connection error: {str(exception_context.original_exception)}")
    
    async def _test_connection(self) -> None:
        """
        Test database connection with a simple query.
        
        Raises:
            SQLAlchemyError: If connection test fails
        """
        try:
            async with self.async_engine.begin() as conn:
                result = await conn.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                if row[0] != 1:
                    raise SQLAlchemyError("Connection test failed")
                    
            logger.info("Database connection test successful")
            
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            raise
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with automatic cleanup.
        
        Yields:
            AsyncSession: Database session
        """
        if not self.is_connected:
            raise RuntimeError("Database connection not initialized")
        
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()
    
    async def execute_query(
        self, 
        query: str, 
        params: Optional[Dict[str, Any]] = None,
        fetch_all: bool = True
    ) -> Dict[str, Any]:
        """
        Execute SQL query with parameters and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch_all: Whether to fetch all results or just metadata
            
        Returns:
            Dictionary containing query results and metadata
        """
        import time
        start_time = time.time()
        
        try:
            async with self.get_session() as session:
                result = await session.execute(text(query), params or {})
                
                if fetch_all:
                    rows = result.fetchall()
                    columns = list(result.keys()) if result.keys() else []
                    data = [dict(zip(columns, row)) for row in rows]
                else:
                    data = []
                    columns = list(result.keys()) if result.keys() else []
                
                execution_time = int((time.time() - start_time) * 1000)
                self.stats['queries_executed'] += 1
                
                # Update average query time
                if self.stats['queries_executed'] > 1:
                    self.stats['avg_query_time'] = (
                        (self.stats['avg_query_time'] * (self.stats['queries_executed'] - 1) + execution_time) 
                        / self.stats['queries_executed']
                    )
                else:
                    self.stats['avg_query_time'] = execution_time
                
                return {
                    'data': data,
                    'columns': columns,
                    'row_count': len(data) if fetch_all else result.rowcount,
                    'execution_time_ms': execution_time,
                    'query': query,
                    'params': params
                }
                
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(
                "Query execution failed", 
                query=query, 
                params=params, 
                error=str(e),
                execution_time_ms=execution_time
            )
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of database connection.
        
        Returns:
            Dictionary containing health status and metrics
        """
        health_status = {
            'status': 'healthy',
            'timestamp': asyncio.get_event_loop().time(),
            'connection_stats': self.stats.copy(),
            'pool_status': {},
            'test_query_ms': 0,
            'errors': []
        }
        
        try:
            # Test basic connectivity
            import time
            start_time = time.time()
            await self._test_connection()
            health_status['test_query_ms'] = int((time.time() - start_time) * 1000)
            
            # Get pool status (handle different pool types safely)
            if self.async_engine:
                try:
                    pool = self.async_engine.pool
                    health_status['pool_status'] = {
                        'size': pool.size(),
                        'checked_in': pool.checkedin(),
                        'checked_out': pool.checkedout(),
                        'overflow': pool.overflow()
                    }
                    # Only add invalid count if the attribute exists
                    if hasattr(pool, 'invalid'):
                        health_status['pool_status']['invalid'] = pool.invalid()
                except AttributeError as e:
                    # Some pool types don't have all these methods
                    logger.debug("Pool status method not available", error=str(e))
                    health_status['pool_status'] = {'status': 'pool_methods_unavailable'}
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['errors'].append(str(e))
            logger.error("Database health check failed", error=str(e))
        
        return health_status
    
    async def close(self) -> None:
        """Close all database connections and cleanup resources."""
        try:
            if self.async_engine:
                await self.async_engine.dispose()
            
            if self.engine:
                self.engine.dispose()
            
            self.is_connected = False
            logger.info("Database connections closed successfully")
            
        except Exception as e:
            logger.error("Error closing database connections", error=str(e))
            raise


# Global connection manager instance
_connection_manager: Optional[TiDBConnectionManager] = None


async def get_connection_manager() -> TiDBConnectionManager:
    """
    Get or create global TiDB connection manager instance.
    
    Returns:
        TiDBConnectionManager: Global connection manager instance
    """
    global _connection_manager
    
    if _connection_manager is None:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        _connection_manager = TiDBConnectionManager(database_url)
        await _connection_manager.initialize()
    
    return _connection_manager


async def close_connection_manager() -> None:
    """Close global connection manager."""
    global _connection_manager
    
    if _connection_manager:
        await _connection_manager.close()
        _connection_manager = None