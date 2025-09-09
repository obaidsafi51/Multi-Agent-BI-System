"""
Connection Pool Optimizer for MCP Clients.

This module implements optimized connection pooling for MCP clients to improve
performance and resource utilization in dynamic schema management operations.
"""

import asyncio
import logging
import time
import weakref
from typing import Dict, Any, Optional, List, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """Connection states in the pool."""
    IDLE = "idle"
    ACTIVE = "active"
    UNHEALTHY = "unhealthy"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass
class ConnectionInfo:
    """Information about a pooled connection."""
    connection_id: str
    created_at: datetime
    last_used: datetime
    last_health_check: datetime
    state: ConnectionState
    use_count: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self, max_age_seconds: int) -> bool:
        """Check if connection has exceeded maximum age."""
        age = (datetime.now() - self.created_at).total_seconds()
        return age > max_age_seconds
    
    def is_idle_timeout(self, idle_timeout_seconds: int) -> bool:
        """Check if connection has been idle too long."""
        idle_time = (datetime.now() - self.last_used).total_seconds()
        return idle_time > idle_timeout_seconds
    
    def needs_health_check(self, health_check_interval_seconds: int) -> bool:
        """Check if connection needs a health check."""
        since_last_check = (datetime.now() - self.last_health_check).total_seconds()
        return since_last_check > health_check_interval_seconds


@dataclass
class PoolMetrics:
    """Connection pool metrics."""
    total_connections: int = 0
    idle_connections: int = 0
    active_connections: int = 0
    unhealthy_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    connection_acquisitions: int = 0
    connection_timeouts: int = 0
    average_acquisition_time: float = 0.0
    peak_connections: int = 0
    pool_utilization: float = 0.0


class MCPConnectionPool:
    """Optimized connection pool for MCP clients."""
    
    def __init__(
        self,
        min_connections: int = 2,
        max_connections: int = 10,
        idle_timeout_seconds: int = 300,
        max_connection_age_seconds: int = 3600,
        connection_retry_attempts: int = 3,
        health_check_interval_seconds: int = 60,
        acquisition_timeout_seconds: int = 30
    ):
        """
        Initialize connection pool.
        
        Args:
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections allowed
            idle_timeout_seconds: Timeout for idle connections
            max_connection_age_seconds: Maximum age for connections
            connection_retry_attempts: Number of retry attempts for failed connections
            health_check_interval_seconds: Interval for health checks
            acquisition_timeout_seconds: Timeout for acquiring connections
        """
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.idle_timeout_seconds = idle_timeout_seconds
        self.max_connection_age_seconds = max_connection_age_seconds
        self.connection_retry_attempts = connection_retry_attempts
        self.health_check_interval_seconds = health_check_interval_seconds
        self.acquisition_timeout_seconds = acquisition_timeout_seconds
        
        # Connection management
        self._connections: Dict[str, Any] = {}  # connection_id -> actual connection
        self._connection_info: Dict[str, ConnectionInfo] = {}
        self._idle_connections: Set[str] = set()
        self._active_connections: Set[str] = set()
        self._unhealthy_connections: Set[str] = set()
        
        # Synchronization
        self._lock = asyncio.Lock()
        self._connection_semaphore = asyncio.Semaphore(max_connections)
        self._shutdown = False
        
        # Metrics
        self.metrics = PoolMetrics()
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Connection factory (to be set by user)
        self._connection_factory: Optional[Callable] = None
        self._health_check_func: Optional[Callable] = None
        
        logger.info(
            f"MCP connection pool initialized: "
            f"min={min_connections}, max={max_connections}"
        )
    
    async def initialize(
        self,
        connection_factory: Callable,
        health_check_func: Optional[Callable] = None
    ) -> None:
        """
        Initialize the connection pool.
        
        Args:
            connection_factory: Async function to create new connections
            health_check_func: Async function to check connection health
        """
        self._connection_factory = connection_factory
        self._health_check_func = health_check_func
        
        # Create initial connections
        await self._ensure_min_connections()
        
        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        if health_check_func:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("Connection pool initialization completed")
    
    async def acquire_connection(self, timeout: Optional[float] = None) -> Any:
        """
        Acquire a connection from the pool.
        
        Args:
            timeout: Timeout for acquiring connection
            
        Returns:
            Connection object
            
        Raises:
            asyncio.TimeoutError: If timeout exceeded
            Exception: If connection acquisition failed
        """
        start_time = time.time()
        timeout = timeout or self.acquisition_timeout_seconds
        
        try:
            # Wait for connection availability with timeout
            await asyncio.wait_for(
                self._connection_semaphore.acquire(),
                timeout=timeout
            )
            
            async with self._lock:
                connection_id = await self._get_or_create_connection()
                
                if connection_id:
                    # Move to active set
                    self._idle_connections.discard(connection_id)
                    self._active_connections.add(connection_id)
                    
                    # Update connection info
                    conn_info = self._connection_info[connection_id]
                    conn_info.last_used = datetime.now()
                    conn_info.use_count += 1
                    conn_info.state = ConnectionState.ACTIVE
                    
                    # Update metrics
                    acquisition_time = time.time() - start_time
                    self.metrics.connection_acquisitions += 1
                    self.metrics.average_acquisition_time = (
                        (self.metrics.average_acquisition_time * (self.metrics.connection_acquisitions - 1) + acquisition_time) /
                        self.metrics.connection_acquisitions
                    )
                    
                    logger.debug(f"Connection acquired: {connection_id} (took {acquisition_time:.3f}s)")
                    return self._connections[connection_id]
                else:
                    self._connection_semaphore.release()
                    raise Exception("Failed to acquire connection")
        
        except asyncio.TimeoutError:
            self.metrics.connection_timeouts += 1
            logger.warning(f"Connection acquisition timeout after {timeout}s")
            raise
        except Exception as e:
            self.metrics.failed_requests += 1
            logger.error(f"Connection acquisition failed: {e}")
            raise
    
    async def release_connection(self, connection: Any) -> None:
        """
        Release a connection back to the pool.
        
        Args:
            connection: Connection to release
        """
        connection_id = None
        
        async with self._lock:
            # Find connection ID
            for conn_id, conn in self._connections.items():
                if conn is connection:
                    connection_id = conn_id
                    break
            
            if not connection_id:
                logger.warning("Attempted to release unknown connection")
                return
            
            # Move to idle set
            self._active_connections.discard(connection_id)
            self._idle_connections.add(connection_id)
            
            # Update connection info
            if connection_id in self._connection_info:
                conn_info = self._connection_info[connection_id]
                conn_info.last_used = datetime.now()
                conn_info.state = ConnectionState.IDLE
            
            # Release semaphore
            self._connection_semaphore.release()
            
            logger.debug(f"Connection released: {connection_id}")
    
    async def _get_or_create_connection(self) -> Optional[str]:
        """Get an existing idle connection or create a new one."""
        # Try to get an idle connection first
        if self._idle_connections:
            # Get the most recently used idle connection
            idle_connections = list(self._idle_connections)
            idle_connections.sort(
                key=lambda cid: self._connection_info[cid].last_used,
                reverse=True
            )
            
            for connection_id in idle_connections:
                conn_info = self._connection_info[connection_id]
                
                # Check if connection is still valid
                if not conn_info.is_expired(self.max_connection_age_seconds):
                    return connection_id
                else:
                    # Remove expired connection
                    await self._remove_connection(connection_id)
        
        # Create new connection if under limit
        if len(self._connections) < self.max_connections:
            return await self._create_new_connection()
        
        # No connections available
        return None
    
    async def _create_new_connection(self) -> Optional[str]:
        """Create a new connection."""
        if not self._connection_factory:
            raise Exception("Connection factory not set")
        
        connection_id = str(uuid.uuid4())
        
        try:
            # Create the actual connection
            connection = await self._connection_factory()
            
            # Store connection and info
            self._connections[connection_id] = connection
            self._connection_info[connection_id] = ConnectionInfo(
                connection_id=connection_id,
                created_at=datetime.now(),
                last_used=datetime.now(),
                last_health_check=datetime.now(),
                state=ConnectionState.IDLE
            )
            
            # Update metrics
            self.metrics.total_connections += 1
            self.metrics.peak_connections = max(
                self.metrics.peak_connections,
                self.metrics.total_connections
            )
            
            logger.debug(f"New connection created: {connection_id}")
            return connection_id
            
        except Exception as e:
            logger.error(f"Failed to create new connection: {e}")
            return None
    
    async def _remove_connection(self, connection_id: str) -> None:
        """Remove a connection from the pool."""
        try:
            # Remove from all sets
            self._idle_connections.discard(connection_id)
            self._active_connections.discard(connection_id)
            self._unhealthy_connections.discard(connection_id)
            
            # Close the actual connection
            if connection_id in self._connections:
                connection = self._connections[connection_id]
                
                # Update connection state
                if connection_id in self._connection_info:
                    self._connection_info[connection_id].state = ConnectionState.CLOSING
                
                # Attempt to close gracefully
                try:
                    if hasattr(connection, 'close'):
                        await connection.close()
                    elif hasattr(connection, 'disconnect'):
                        await connection.disconnect()
                except Exception as e:
                    logger.warning(f"Error closing connection {connection_id}: {e}")
                
                del self._connections[connection_id]
            
            # Remove connection info
            if connection_id in self._connection_info:
                self._connection_info[connection_id].state = ConnectionState.CLOSED
                del self._connection_info[connection_id]
            
            # Update metrics
            self.metrics.total_connections -= 1
            
            logger.debug(f"Connection removed: {connection_id}")
            
        except Exception as e:
            logger.error(f"Error removing connection {connection_id}: {e}")
    
    async def _ensure_min_connections(self) -> None:
        """Ensure minimum number of connections are available."""
        current_count = len(self._connections)
        
        if current_count < self.min_connections:
            needed = self.min_connections - current_count
            
            for _ in range(needed):
                connection_id = await self._create_new_connection()
                if connection_id:
                    self._idle_connections.add(connection_id)
                else:
                    break  # Stop if we can't create connections
    
    async def _cleanup_loop(self) -> None:
        """Background task for connection cleanup."""
        while not self._shutdown:
            try:
                await self._cleanup_connections()
                await asyncio.sleep(60)  # Cleanup every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(10)  # Shorter sleep on error
    
    async def _cleanup_connections(self) -> None:
        """Clean up expired and idle connections."""
        async with self._lock:
            connections_to_remove = []
            
            # Check all connections for cleanup criteria
            for connection_id, conn_info in self._connection_info.items():
                should_remove = False
                
                # Check if expired
                if conn_info.is_expired(self.max_connection_age_seconds):
                    logger.debug(f"Connection {connection_id} expired (age: {conn_info.created_at})")
                    should_remove = True
                
                # Check if idle timeout (only for idle connections above minimum)
                elif (connection_id in self._idle_connections and 
                      conn_info.is_idle_timeout(self.idle_timeout_seconds) and
                      len(self._connections) > self.min_connections):
                    logger.debug(f"Connection {connection_id} idle timeout")
                    should_remove = True
                
                # Check if unhealthy
                elif connection_id in self._unhealthy_connections:
                    logger.debug(f"Connection {connection_id} marked unhealthy")
                    should_remove = True
                
                if should_remove:
                    connections_to_remove.append(connection_id)
            
            # Remove identified connections
            for connection_id in connections_to_remove:
                await self._remove_connection(connection_id)
            
            # Ensure minimum connections
            await self._ensure_min_connections()
            
            # Update metrics
            self._update_pool_metrics()
    
    async def _health_check_loop(self) -> None:
        """Background task for connection health checks."""
        while not self._shutdown:
            try:
                await self._check_connection_health()
                await asyncio.sleep(self.health_check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(30)  # Sleep on error
    
    async def _check_connection_health(self) -> None:
        """Check health of all connections."""
        if not self._health_check_func:
            return
        
        async with self._lock:
            connections_to_check = []
            
            # Find connections that need health checks
            for connection_id, conn_info in self._connection_info.items():
                if (conn_info.needs_health_check(self.health_check_interval_seconds) and
                    connection_id in self._idle_connections):  # Only check idle connections
                    connections_to_check.append(connection_id)
        
        # Perform health checks outside the lock
        for connection_id in connections_to_check:
            try:
                connection = self._connections.get(connection_id)
                if not connection:
                    continue
                
                # Perform health check
                is_healthy = await self._health_check_func(connection)
                
                async with self._lock:
                    if connection_id in self._connection_info:
                        conn_info = self._connection_info[connection_id]
                        conn_info.last_health_check = datetime.now()
                        
                        if not is_healthy:
                            # Mark as unhealthy
                            self._idle_connections.discard(connection_id)
                            self._unhealthy_connections.add(connection_id)
                            conn_info.state = ConnectionState.UNHEALTHY
                            conn_info.error_count += 1
                            
                            logger.warning(f"Connection {connection_id} failed health check")
                        else:
                            # Ensure it's in the right state
                            if conn_info.state == ConnectionState.UNHEALTHY:
                                self._unhealthy_connections.discard(connection_id)
                                self._idle_connections.add(connection_id)
                                conn_info.state = ConnectionState.IDLE
                                conn_info.error_count = 0
                                
                                logger.info(f"Connection {connection_id} recovered")
            
            except Exception as e:
                logger.error(f"Health check failed for connection {connection_id}: {e}")
                
                # Mark as unhealthy on error
                async with self._lock:
                    if connection_id in self._connection_info:
                        self._idle_connections.discard(connection_id)
                        self._unhealthy_connections.add(connection_id)
                        self._connection_info[connection_id].state = ConnectionState.UNHEALTHY
                        self._connection_info[connection_id].error_count += 1
    
    def _update_pool_metrics(self) -> None:
        """Update pool metrics."""
        self.metrics.total_connections = len(self._connections)
        self.metrics.idle_connections = len(self._idle_connections)
        self.metrics.active_connections = len(self._active_connections)
        self.metrics.unhealthy_connections = len(self._unhealthy_connections)
        
        if self.max_connections > 0:
            self.metrics.pool_utilization = self.metrics.total_connections / self.max_connections
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get current pool statistics."""
        async with self._lock:
            self._update_pool_metrics()
            
            return {
                "total_connections": self.metrics.total_connections,
                "idle_connections": self.metrics.idle_connections,
                "active_connections": self.metrics.active_connections,
                "unhealthy_connections": self.metrics.unhealthy_connections,
                "pool_utilization": self.metrics.pool_utilization,
                "peak_connections": self.metrics.peak_connections,
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "connection_acquisitions": self.metrics.connection_acquisitions,
                "connection_timeouts": self.metrics.connection_timeouts,
                "average_acquisition_time": self.metrics.average_acquisition_time,
                "configuration": {
                    "min_connections": self.min_connections,
                    "max_connections": self.max_connections,
                    "idle_timeout_seconds": self.idle_timeout_seconds,
                    "max_connection_age_seconds": self.max_connection_age_seconds
                }
            }
    
    async def shutdown(self) -> None:
        """Shutdown the connection pool."""
        logger.info("Shutting down connection pool")
        
        self._shutdown = True
        
        # Cancel background tasks
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        async with self._lock:
            connection_ids = list(self._connections.keys())
            
            for connection_id in connection_ids:
                await self._remove_connection(connection_id)
        
        logger.info("Connection pool shutdown completed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()


class OptimizedMCPClient:
    """MCP client with optimized connection pooling."""
    
    def __init__(
        self,
        connection_pool: MCPConnectionPool,
        retry_attempts: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize optimized MCP client.
        
        Args:
            connection_pool: Connection pool to use
            retry_attempts: Number of retry attempts for failed operations
            retry_delay: Delay between retry attempts
        """
        self.connection_pool = connection_pool
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        logger.info("Optimized MCP client initialized")
    
    async def execute_with_connection(
        self,
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an operation with a pooled connection.
        
        Args:
            operation: Async function to execute with connection
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Operation result
        """
        last_exception = None
        
        for attempt in range(self.retry_attempts):
            connection = None
            
            try:
                # Acquire connection
                connection = await self.connection_pool.acquire_connection()
                
                # Execute operation
                result = await operation(connection, *args, **kwargs)
                
                # Update metrics
                self.connection_pool.metrics.successful_requests += 1
                
                return result
                
            except Exception as e:
                last_exception = e
                self.connection_pool.metrics.failed_requests += 1
                
                logger.warning(
                    f"Operation failed on attempt {attempt + 1}/{self.retry_attempts}: {e}"
                )
                
                # Wait before retry (except on last attempt)
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
            
            finally:
                # Always release connection
                if connection:
                    await self.connection_pool.release_connection(connection)
        
        # All attempts failed
        logger.error(f"Operation failed after {self.retry_attempts} attempts")
        raise last_exception
    
    async def get_databases(self) -> List[str]:
        """Get list of databases using pooled connection."""
        async def _get_databases(connection):
            # This would be the actual MCP call
            # For now, return mock data
            return ["default", "analytics", "reporting"]
        
        return await self.execute_with_connection(_get_databases)
    
    async def get_tables(self, database_name: str) -> List[str]:
        """Get list of tables using pooled connection."""
        async def _get_tables(connection, db_name):
            # This would be the actual MCP call to dynamically discover tables
            # Import schema manager for dynamic discovery
            from .manager import DynamicSchemaManager
            schema_manager = DynamicSchemaManager()
            await schema_manager.initialize()
            return await schema_manager.get_table_names()
        
        return await self.execute_with_connection(_get_tables, database_name)
    
    async def get_table_schema(self, database_name: str, table_name: str) -> Dict[str, Any]:
        """Get table schema using pooled connection."""
        async def _get_table_schema(connection, db_name, tbl_name):
            # This would be the actual MCP call
            # For now, return mock data
            return {
                "name": tbl_name,
                "columns": [
                    {"name": "id", "type": "INT", "nullable": False},
                    {"name": "created_at", "type": "TIMESTAMP", "nullable": False}
                ]
            }
        
        return await self.execute_with_connection(_get_table_schema, database_name, table_name)
