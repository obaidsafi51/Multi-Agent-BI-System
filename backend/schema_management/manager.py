"""
MCP Schema Manager for centralized schema operations.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .client import EnhancedMCPClient, MCPRequestError
from .config import MCPSchemaConfig, SchemaValidationConfig
from .enhanced_cache import EnhancedSchemaCache
from .models import (
    DatabaseInfo, TableInfo, ColumnInfo, TableSchema, ValidationResult,
    ValidationError, ValidationWarning, ValidationSeverity, CacheStats
)

# Import monitoring components
try:
    from .monitoring import (
        get_logger, get_metrics_collector, MCPHealthMonitor, 
        MCPAlertManager, MCPPerformanceTracker
    )
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    import logging
    
    def get_logger(name):
        return logging.getLogger(name)
    
    def get_metrics_collector():
        return None

logger = get_logger(__name__) if MONITORING_AVAILABLE else logging.getLogger(__name__)


class SchemaCacheManager:
    """Simple cache manager for MCP schema responses."""
    
    def __init__(self, client, ttl_seconds: int = 300, ttl: Optional[float] = None):
        """Initialize cache manager."""
        self.client = client
        # Support both ttl_seconds and ttl parameters for backwards compatibility
        if ttl is not None:
            self.ttl = ttl
        else:
            self.ttl = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, datetime] = {}
    
    def get_schema(self) -> Dict[str, Any]:
        """Get schema from cache or fetch from client."""
        import time
        now = time.time()
        entry = self._cache.get("schema")
        
        if entry and (now - self._timestamps.get("schema", 0)) < self.ttl:
            return entry
        
        # Fetch new schema
        try:
            # For synchronous operation, we'll need to handle async properly
            if hasattr(self.client, 'discover_schema'):
                schema = self.client.discover_schema()
            else:
                # Fallback to basic schema structure
                schema = {"tables": [], "version": "unknown"}
            
            # Create a new object to ensure identity changes
            new_schema = dict(schema) if isinstance(schema, dict) else {"tables": [], "version": "unknown"}
            self._cache["schema"] = new_schema
            self._timestamps["schema"] = now
            return new_schema
        except Exception as e:
            logger.error(f"Failed to fetch schema: {e}")
            # Return cached version if available, even if stale
            return self._cache.get("schema", {"tables": [], "version": "unknown"})
    
    def invalidate(self):
        """Clear all cached entries."""
        self._cache.clear()
        self._timestamps.clear()


class MCPSchemaManager:
    """
    Central manager for MCP-based schema operations.
    
    Provides high-level interface for schema discovery, caching, and validation
    while managing the underlying MCP client connections and error handling.
    Includes comprehensive monitoring and observability features.
    """
    
    def __init__(
        self,
        mcp_config: Optional[MCPSchemaConfig] = None,
        validation_config: Optional[SchemaValidationConfig] = None,
        enable_monitoring: bool = True,
        enhanced_cache: Optional[EnhancedSchemaCache] = None
    ):
        """
        Initialize MCP Schema Manager.
        
        Args:
            mcp_config: MCP client configuration
            validation_config: Schema validation configuration
            enable_monitoring: Whether to enable monitoring and observability
            enhanced_cache: Enhanced cache instance (optional)
        """
        self.mcp_config = mcp_config or MCPSchemaConfig.from_env()
        self.validation_config = validation_config or SchemaValidationConfig.from_env()
        self.client = EnhancedMCPClient(self.mcp_config)
        
        # Use enhanced cache if provided, otherwise create one
        if enhanced_cache:
            self.enhanced_cache = enhanced_cache
        else:
            self.enhanced_cache = EnhancedSchemaCache(
                config=self.mcp_config,
                default_ttl=self.mcp_config.cache_ttl
            )
        
        # Legacy cache for backward compatibility
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
        
        # Initialize monitoring components if available
        self.enable_monitoring = enable_monitoring and MONITORING_AVAILABLE
        
        if self.enable_monitoring:
            self.metrics_collector = get_metrics_collector()
            self.performance_tracker = MCPPerformanceTracker()
            self.health_monitor = MCPHealthMonitor()
            self.alert_manager = MCPAlertManager()
            
            # Set dependencies for health monitor
            self.health_monitor.set_dependencies(
                mcp_client=self.client,
                schema_manager=self,
                cache_manager=self
            )
            
            logger.info("Initialized MCP Schema Manager with monitoring enabled")
        else:
            self.metrics_collector = None
            self.performance_tracker = None
            self.health_monitor = None
            self.alert_manager = None
            
            if enable_monitoring:
                logger.warning("Monitoring requested but not available - continuing without monitoring")
            else:
                logger.info("Initialized MCP Schema Manager without monitoring")
        
        logger.info("Initialized MCP Schema Manager")
    
    async def connect(self) -> bool:
        """
        Connect to the MCP server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            return await self.client.connect()
        except Exception as e:
            logger.error(f"Failed to connect MCP Schema Manager: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the MCP server."""
        await self.client.disconnect()
    
    def _get_cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operation."""
        key_parts = [operation]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        return ":".join(key_parts)
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if not self.mcp_config.enable_caching:
            return False
        
        if cache_key not in self._cache_timestamps:
            return False
        
        cache_time = self._cache_timestamps[cache_key]
        ttl_seconds = self.mcp_config.cache_ttl
        return datetime.now() - cache_time < timedelta(seconds=ttl_seconds)
    
    def _set_cache(self, cache_key: str, data: Any):
        """Set data in cache."""
        if not self.mcp_config.enable_caching:
            return
        
        # Set in enhanced cache
        try:
            # Extract operation and parameters from cache key
            parts = cache_key.split(':')
            operation = parts[0]
            params = {}
            
            for part in parts[1:]:
                if ':' in part:
                    k, v = part.split(':', 1)
                    params[k] = v
            
            # Use asyncio.run for sync compatibility
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're already in an async context, create a task
                    asyncio.create_task(self.enhanced_cache.set(operation, data, **params))
                else:
                    loop.run_until_complete(self.enhanced_cache.set(operation, data, **params))
            except RuntimeError:
                # No event loop, create one
                asyncio.run(self.enhanced_cache.set(operation, data, **params))
        except Exception as e:
            logger.debug(f"Enhanced cache set failed for {cache_key}: {e}")
        
        # Also set in legacy cache for backward compatibility
        self._schema_cache[cache_key] = data
        self._cache_timestamps[cache_key] = datetime.now()
        
        # Simple cache eviction - remove oldest entries if cache gets too large
        max_cache_size = 1000  # Configurable limit
        if len(self._schema_cache) > max_cache_size:
            oldest_key = min(self._cache_timestamps.keys(), 
                           key=lambda k: self._cache_timestamps[k])
            del self._schema_cache[oldest_key]
            del self._cache_timestamps[oldest_key]
            self._cache_stats["evictions"] += 1
    
    def _get_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache."""
        if not self.mcp_config.enable_caching:
            return None
        
        # Try enhanced cache first
        try:
            # Extract operation and parameters from cache key
            parts = cache_key.split(':')
            operation = parts[0]
            params = {}
            
            for part in parts[1:]:
                if ':' in part:
                    k, v = part.split(':', 1)
                    params[k] = v
            
            # Use asyncio.run for sync compatibility
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're already in an async context, create a task
                    task = asyncio.create_task(self.enhanced_cache.get(operation, **params))
                    result = None
                    # For now, return None if we can't wait
                else:
                    result = loop.run_until_complete(self.enhanced_cache.get(operation, **params))
            except RuntimeError:
                # No event loop, create one
                result = asyncio.run(self.enhanced_cache.get(operation, **params))
            
            if result is not None:
                self._cache_stats["hits"] += 1
                return result
        except Exception as e:
            logger.debug(f"Enhanced cache lookup failed for {cache_key}: {e}")
        
        # Fall back to legacy cache
        if self._is_cache_valid(cache_key):
            self._cache_stats["hits"] += 1
            return self._schema_cache.get(cache_key)
        
        self._cache_stats["misses"] += 1
        return None
    
    async def discover_databases(self) -> List[DatabaseInfo]:
        """
        Discover all accessible databases.
        
        Returns:
            List of database information
        """
        if self.enable_monitoring and self.performance_tracker:
            async with self.performance_tracker.track_operation(
                "discover_databases"
            ) as perf_data:
                return await self._discover_databases_impl(perf_data)
        else:
            return await self._discover_databases_impl()
    
    async def _discover_databases_impl(self, perf_data: Optional[Dict[str, Any]] = None) -> List[DatabaseInfo]:
        """Implementation of database discovery with monitoring support."""
        cache_key = self._get_cache_key("discover_databases")
        
        # Check cache first
        cache_start_time = time.time()
        cached_result = self._get_cache(cache_key)
        
        if cached_result is not None:
            if perf_data:
                perf_data['cache_hit'] = True
            
            if self.enable_monitoring and self.metrics_collector:
                cache_time_ms = (time.time() - cache_start_time) * 1000
                self.metrics_collector.record_cache_hit(cache_time_ms)
            
            logger.debug("Returning cached database discovery result")
            return cached_result
        
        if perf_data:
            perf_data['cache_hit'] = False
        
        if self.enable_monitoring and self.metrics_collector:
            cache_time_ms = (time.time() - cache_start_time) * 1000
            self.metrics_collector.record_cache_miss(cache_time_ms)
        
        try:
            # Use the MCP client directly to discover databases
            mcp_start_time = time.time()
            db_result = await self.client._send_request("discover_databases_tool", {})
            
            if perf_data:
                perf_data['network_time_ms'] = (time.time() - mcp_start_time) * 1000
            
            if not db_result or (isinstance(db_result, dict) and db_result.get('error')):
                error_msg = db_result.get('error') if isinstance(db_result, dict) else 'Unknown error'
                logger.error(f"Database discovery failed: {error_msg}")
                
                if self.enable_monitoring and self.metrics_collector:
                    self.metrics_collector.record_error("DatabaseDiscoveryError", "discover_databases", error_msg)
                
                if self.mcp_config.fallback_enabled:
                    return []
                raise MCPRequestError(f"Failed to discover databases: {error_msg}")
            
            # Process database results
            databases = []
            for db_data in db_result:
                databases.append(DatabaseInfo(
                    name=db_data['name'],
                    charset=db_data.get('charset', 'utf8mb4'),
                    collation=db_data.get('collation', 'utf8mb4_general_ci'),
                    accessible=db_data.get('accessible', True),
                    table_count=db_data.get('table_count')
                ))
            
            self._set_cache(cache_key, databases)
            
            logger.info(f"Discovered {len(databases)} databases")
            return databases
            
        except Exception as e:
            logger.error(f"Failed to discover databases: {e}")
            
            if self.enable_monitoring and self.metrics_collector:
                self.metrics_collector.record_error(type(e).__name__, "discover_databases", str(e))
            
            if self.mcp_config.fallback_enabled:
                logger.warning("Using fallback: returning empty database list")
                return []
            raise
    
    async def get_table_schema(self, database: str, table: str) -> Optional[TableSchema]:
        """
        Get table schema information.
        
        Args:
            database: Database name
            table: Table name
            
        Returns:
            Table schema information or None if not found
        """
        cache_key = self._get_cache_key("table_schema", database=database, table=table)
        cached_result = self._get_cache(cache_key)
        
        if cached_result is not None:
            logger.debug(f"Returning cached schema for {database}.{table}")
            return cached_result
        
        try:
            detailed_schema = await self.client.get_table_schema_detailed(database, table)
            schema = detailed_schema.schema
            
            self._set_cache(cache_key, schema)
            
            logger.debug(f"Retrieved schema for {database}.{table} with {len(schema.columns)} columns")
            return schema
            
        except Exception as e:
            logger.error(f"Failed to get table schema for {database}.{table}: {e}")
            if self.mcp_config.fallback_enabled:
                logger.warning("Using fallback: returning None for table schema")
                return None
            raise
    
    async def get_tables(self, database: str) -> List[TableInfo]:
        """
        Get tables in a specific database.
        
        Args:
            database: Database name
            
        Returns:
            List of table information
        """
        cache_key = self._get_cache_key("tables", database=database)
        cached_result = self._get_cache(cache_key)
        
        if cached_result is not None:
            logger.debug(f"Returning cached tables for database {database}")
            return cached_result
        
        try:
            # Use the MCP client to discover tables
            result = await self.client._send_request("discover_tables_tool", {"database": database})
            
            if not result:
                logger.error(f"Failed to discover tables in {database}: No response from server")
                if self.mcp_config.fallback_enabled:
                    return []
                raise MCPRequestError("Failed to discover tables: No response from server")
            
            # Handle error response (dict with error key)
            if isinstance(result, dict) and result.get('error'):
                logger.error(f"Failed to discover tables in {database}: {result['error']}")
                if self.mcp_config.fallback_enabled:
                    return []
                raise MCPRequestError(f"Failed to discover tables: {result['error']}")
            
            tables = []
            for table_data in result:
                # Parse datetime fields if present
                created_at = None
                updated_at = None
                
                if table_data.get('created_at'):
                    try:
                        created_at = datetime.fromisoformat(table_data['created_at'].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid created_at format for table {table_data.get('name')}: {table_data.get('created_at')}")
                
                if table_data.get('updated_at'):
                    try:
                        updated_at = datetime.fromisoformat(table_data['updated_at'].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid updated_at format for table {table_data.get('name')}: {table_data.get('updated_at')}")
                
                tables.append(TableInfo(
                    name=table_data['name'],
                    type=table_data.get('type', 'BASE TABLE'),
                    engine=table_data.get('engine', 'InnoDB'),
                    rows=table_data.get('rows', 0),
                    size_mb=float(table_data.get('size_mb', 0.0)),
                    comment=table_data.get('comment'),
                    created_at=created_at,
                    updated_at=updated_at
                ))
            
            self._set_cache(cache_key, tables)
            
            logger.info(f"Discovered {len(tables)} tables in database {database}")
            return tables
            
        except Exception as e:
            logger.error(f"Failed to get tables for database {database}: {e}")
            if self.mcp_config.fallback_enabled:
                logger.warning("Using fallback: returning empty table list")
                return []
            raise
    
    async def validate_table_exists(self, database: str, table: str) -> bool:
        """
        Validate that a table exists in the database.
        
        Args:
            database: Database name
            table: Table name
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            tables = await self.get_tables(database)
            return any(t.name == table for t in tables)
        except Exception as e:
            logger.error(f"Failed to validate table existence for {database}.{table}: {e}")
            return False
    
    async def get_column_info(self, database: str, table: str, column: str) -> Optional[ColumnInfo]:
        """
        Get information about a specific column.
        
        Args:
            database: Database name
            table: Table name
            column: Column name
            
        Returns:
            Column information or None if not found
        """
        try:
            schema = await self.get_table_schema(database, table)
            if not schema:
                return None
            
            for col in schema.columns:
                if col.name == column:
                    return col
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get column info for {database}.{table}.{column}: {e}")
            return None
    
    async def refresh_schema_cache(self, cache_type: str = "all") -> bool:
        """
        Refresh schema cache.
        
        Args:
            cache_type: Type of cache to refresh ("all", "databases", "tables", "schemas")
            
        Returns:
            True if refresh successful, False otherwise
        """
        try:
            if cache_type == "all":
                cleared_count = len(self._schema_cache)
                self._schema_cache.clear()
                self._cache_timestamps.clear()
                logger.info(f"Cleared all schema cache ({cleared_count} entries)")
            else:
                # Clear specific cache entries
                keys_to_remove = [k for k in self._schema_cache.keys() if k.startswith(cache_type)]
                for key in keys_to_remove:
                    del self._schema_cache[key]
                    del self._cache_timestamps[key]
                logger.info(f"Cleared {len(keys_to_remove)} cache entries for type: {cache_type}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh schema cache: {e}")
            return False
    
    async def invalidate_cache_by_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match cache keys (supports wildcards)
            
        Returns:
            Number of entries invalidated
        """
        try:
            import fnmatch
            
            keys_to_remove = []
            for key in self._schema_cache.keys():
                if fnmatch.fnmatch(key, pattern):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._schema_cache[key]
                del self._cache_timestamps[key]
            
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries matching pattern: {pattern}")
            return len(keys_to_remove)
            
        except Exception as e:
            logger.error(f"Failed to invalidate cache by pattern '{pattern}': {e}")
            return 0
    
    async def get_cache_entry_details(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific cache entry.
        
        Args:
            cache_key: Cache key to inspect
            
        Returns:
            Cache entry details or None if not found
        """
        if cache_key not in self._schema_cache:
            return None
        
        timestamp = self._cache_timestamps.get(cache_key)
        age_seconds = (datetime.now() - timestamp).total_seconds() if timestamp else 0
        is_valid = self._is_cache_valid(cache_key)
        
        return {
            "key": cache_key,
            "timestamp": timestamp.isoformat() if timestamp else None,
            "age_seconds": int(age_seconds),
            "is_valid": is_valid,
            "ttl_remaining": max(0, self.mcp_config.cache_ttl - age_seconds) if is_valid else 0,
            "data_type": type(self._schema_cache[cache_key]).__name__,
            "data_size": len(str(self._schema_cache[cache_key]))
        }
    
    def get_cache_stats(self) -> CacheStats:
        """
        Get cache performance statistics.
        
        Returns:
            Cache statistics
        """
        total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = self._cache_stats["hits"] / total_requests if total_requests > 0 else 0.0
        miss_rate = 1.0 - hit_rate
        
        # Calculate cache age statistics
        now = datetime.now()
        ages = [(now - ts).total_seconds() for ts in self._cache_timestamps.values()]
        
        # Estimate memory usage (rough calculation)
        memory_usage_mb = 0.0
        try:
            import sys
            total_size = sum(sys.getsizeof(str(data)) for data in self._schema_cache.values())
            memory_usage_mb = total_size / (1024 * 1024)
        except Exception:
            # Fallback to simple estimation
            memory_usage_mb = len(self._schema_cache) * 0.001  # Rough estimate
        
        return CacheStats(
            total_entries=len(self._schema_cache),
            hit_rate=hit_rate,
            miss_rate=miss_rate,
            eviction_count=self._cache_stats["evictions"],
            memory_usage_mb=memory_usage_mb,
            oldest_entry_age_seconds=int(max(ages)) if ages else 0,
            newest_entry_age_seconds=int(min(ages)) if ages else 0
        )
    
    def get_detailed_cache_stats(self) -> Dict[str, Any]:
        """
        Get detailed cache statistics including per-operation breakdown.
        
        Returns:
            Detailed cache statistics
        """
        stats = self.get_cache_stats()
        
        # Analyze cache keys by operation type
        operation_stats = {}
        for key in self._schema_cache.keys():
            operation = key.split(':')[0] if ':' in key else 'unknown'
            if operation not in operation_stats:
                operation_stats[operation] = 0
            operation_stats[operation] += 1
        
        # Calculate expiry information
        now = datetime.now()
        expired_count = 0
        expiring_soon_count = 0  # Expiring within 10% of TTL
        
        for timestamp in self._cache_timestamps.values():
            age = (now - timestamp).total_seconds()
            if age > self.mcp_config.cache_ttl:
                expired_count += 1
            elif age > self.mcp_config.cache_ttl * 0.9:
                expiring_soon_count += 1
        
        return {
            "basic_stats": stats,
            "operation_breakdown": operation_stats,
            "cache_health": {
                "expired_entries": expired_count,
                "expiring_soon": expiring_soon_count,
                "healthy_entries": len(self._schema_cache) - expired_count - expiring_soon_count
            },
            "configuration": {
                "cache_enabled": self.mcp_config.enable_caching,
                "cache_ttl": self.mcp_config.cache_ttl,
                "fallback_enabled": self.mcp_config.fallback_enabled
            },
            "performance_metrics": {
                "total_hits": self._cache_stats["hits"],
                "total_misses": self._cache_stats["misses"],
                "total_evictions": self._cache_stats["evictions"]
            }
        }
    
    async def health_check(self) -> bool:
        """
        Check the health of the MCP schema manager.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            if self.enable_monitoring and self.health_monitor:
                health_report = await self.health_monitor.perform_health_check()
                return health_report.overall_status.value in ['healthy', 'degraded']
            else:
                # Fallback to simple client health check
                return await self.client.health_check()
        except Exception as e:
            logger.error(f"Schema manager health check failed: {e}")
            return False
    
    async def get_comprehensive_monitoring_report(self) -> Dict[str, Any]:
        """
        Get comprehensive monitoring report including metrics, health, and performance data.
        
        Returns:
            Dictionary containing all monitoring information
        """
        if not self.enable_monitoring:
            return {
                'monitoring_enabled': False,
                'message': 'Monitoring is not enabled for this instance'
            }
        
        report = {
            'monitoring_enabled': True,
            'timestamp': datetime.utcnow().isoformat(),
            'system_metrics': self.metrics_collector.get_comprehensive_metrics() if self.metrics_collector else {},
            'health_summary': {},
            'performance_summary': {},
            'active_alerts': [],
            'optimization_recommendations': []
        }
        
        try:
            # Health information
            if self.health_monitor:
                latest_health = self.health_monitor.get_latest_health_status()
                if latest_health:
                    report['health_summary'] = latest_health.to_dict()
                else:
                    health_report = await self.health_monitor.perform_health_check()
                    report['health_summary'] = health_report.to_dict()
            
            # Performance information
            if self.performance_tracker:
                report['performance_summary'] = self.performance_tracker.get_performance_summary()
                report['optimization_recommendations'] = [
                    rec.to_dict() for rec in self.performance_tracker.get_optimization_recommendations()
                ]
            
            # Alert information
            if self.alert_manager:
                await self.alert_manager.check_alerts(self.health_monitor.get_latest_health_status())
                report['active_alerts'] = [
                    alert.to_dict() for alert in self.alert_manager.get_active_alerts()
                ]
                report['alert_summary'] = self.alert_manager.get_alert_summary()
        
        except Exception as e:
            logger.error(f"Error generating monitoring report: {e}")
            report['error'] = str(e)
        
        return report
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Get current monitoring system status.
        
        Returns:
            Dictionary with monitoring system status
        """
        return {
            'monitoring_enabled': self.enable_monitoring,
            'monitoring_available': MONITORING_AVAILABLE,
            'components': {
                'metrics_collector': self.metrics_collector is not None,
                'performance_tracker': self.performance_tracker is not None,
                'health_monitor': self.health_monitor is not None,
                'alert_manager': self.alert_manager is not None
            },
            'cache_stats': self.get_cache_stats().to_dict() if hasattr(self.get_cache_stats(), 'to_dict') else self.get_cache_stats()
        }
    
    async def start_monitoring(self):
        """Start background monitoring tasks."""
        if not self.enable_monitoring:
            logger.warning("Cannot start monitoring - monitoring is not enabled")
            return
        
        logger.info("Starting MCP schema management monitoring")
        
        # Start periodic health checks
        if self.health_monitor and self.alert_manager:
            asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        logger.info("Monitoring loop started")
        
        while True:
            try:
                # Perform health check
                health_report = await self.health_monitor.perform_health_check()
                
                # Check for alerts
                await self.alert_manager.check_alerts(health_report)
                
                # Wait before next check
                await asyncio.sleep(self.health_monitor.check_interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(60)