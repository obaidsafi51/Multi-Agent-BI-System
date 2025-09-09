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
    ValidationError, ValidationWarning, ValidationSeverity, CacheStats,
    QueryIntent, QueryContext, QueryResult
)
from .semantic_mapper import SemanticSchemaMapper, SemanticMappingConfig
from .query_builder import IntelligentQueryBuilder
from .change_detector import SchemaChangeDetector

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
        enhanced_cache: Optional[EnhancedSchemaCache] = None,
        enable_semantic_mapping: bool = True,
        enable_change_detection: bool = True
    ):
        """
        Initialize MCP Schema Manager.
        
        Args:
            mcp_config: MCP client configuration
            validation_config: Schema validation configuration
            enable_monitoring: Whether to enable monitoring and observability
            enhanced_cache: Enhanced cache instance (optional)
            enable_semantic_mapping: Whether to enable semantic mapping capabilities
            enable_change_detection: Whether to enable schema change detection
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
        
        # Initialize Phase 2 components
        self.enable_semantic_mapping = enable_semantic_mapping
        self.enable_change_detection = enable_change_detection
        
        if self.enable_semantic_mapping:
            semantic_config = SemanticMappingConfig.from_env()
            self.semantic_mapper = SemanticSchemaMapper(config=semantic_config)
            self.query_builder = IntelligentQueryBuilder(
                schema_manager=self,
                semantic_mapper=self.semantic_mapper
            )
            logger.info("Initialized semantic mapping and intelligent query building")
        else:
            self.semantic_mapper = None
            self.query_builder = None
        
        if self.enable_change_detection:
            self.change_detector = SchemaChangeDetector(
                schema_manager=self,
                cache_manager=self.enhanced_cache
            )
            logger.info("Initialized schema change detection")
        else:
            self.change_detector = None
        
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
        Connect to the MCP server and start Phase 2 services.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            success = await self.client.connect()
            
            if success and self.enable_change_detection and self.change_detector:
                # Start schema change monitoring
                await self.change_detector.start_monitoring()
                logger.info("Started schema change monitoring")
            
            return success
        except Exception as e:
            logger.error(f"Failed to connect MCP Schema Manager: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the MCP server and stop Phase 2 services."""
        try:
            if self.enable_change_detection and self.change_detector:
                await self.change_detector.stop_monitoring()
                logger.info("Stopped schema change monitoring")
        except Exception as e:
            logger.error(f"Error stopping change detection: {e}")
        
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
    
    # Phase 2 Methods: Semantic Understanding and Query Intelligence
    
    async def map_business_term_to_schema(
        self,
        business_term: str,
        context: Optional[str] = None,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Map a business term to database schema elements using semantic analysis.
        
        Args:
            business_term: Business term to map (e.g., 'revenue', 'customer')
            context: Optional context to improve mapping accuracy
            filter_criteria: Optional criteria to filter schema elements
            
        Returns:
            List of semantic mappings with confidence scores
        """
        if not self.enable_semantic_mapping or not self.semantic_mapper:
            logger.warning("Semantic mapping is not enabled")
            return []
        
        try:
            # Discover current schema for analysis
            await self._ensure_schema_analyzed()
            
            # Perform semantic mapping
            mappings = await self.semantic_mapper.map_business_term(
                business_term,
                context=context,
                schema_filter=filter_criteria
            )
            
            # Convert to serializable format
            result = []
            for mapping in mappings:
                result.append({
                    'business_term': mapping.business_term,
                    'schema_element_type': mapping.schema_element_type,
                    'schema_element_path': mapping.schema_element_path,
                    'confidence_score': mapping.confidence_score,
                    'similarity_type': mapping.similarity_type,
                    'context_match': mapping.context_match,
                    'metadata': mapping.metadata,
                    'created_at': mapping.created_at.isoformat()
                })
            
            logger.info(f"Mapped '{business_term}' to {len(result)} schema elements")
            return result
            
        except Exception as e:
            logger.error(f"Failed to map business term '{business_term}': {e}")
            return []
    
    async def build_intelligent_query(
        self,
        query_intent: Dict[str, Any],
        query_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build an intelligent SQL query from natural language intent.
        
        Args:
            query_intent: Parsed query intent with metrics, filters, etc.
            query_context: Query context with user info, preferences, etc.
            
        Returns:
            Query result with SQL, confidence score, and metadata
        """
        if not self.enable_semantic_mapping or not self.query_builder:
            logger.warning("Intelligent query building is not enabled")
            return {
                'success': False,
                'error': 'Intelligent query building is not available',
                'sql': '',
                'confidence_score': 0.0
            }
        
        try:
            # Convert dictionaries to proper objects
            intent = QueryIntent(
                metric_type=query_intent.get('metric_type', ''),
                filters=query_intent.get('filters', {}),
                time_period=query_intent.get('time_period'),
                aggregation_type=query_intent.get('aggregation_type', 'sum'),
                group_by=query_intent.get('group_by', []),
                order_by=query_intent.get('order_by'),
                limit=query_intent.get('limit'),
                confidence=query_intent.get('confidence', 0.0),
                parsed_entities=query_intent.get('parsed_entities', {})
            )
            
            context = QueryContext(
                user_id=query_context.get('user_id', ''),
                session_id=query_context.get('session_id', ''),
                query_history=query_context.get('query_history', []),
                available_schemas=query_context.get('available_schemas', []),
                user_preferences=query_context.get('user_preferences', {}),
                business_context=query_context.get('business_context')
            )
            
            # Build the query
            result = await self.query_builder.build_query(intent, context)
            
            # Convert result to serializable format
            return {
                'success': True,
                'sql': result.sql,
                'parameters': result.parameters,
                'estimated_rows': result.estimated_rows,
                'optimization_hints': result.optimization_hints,
                'alternative_queries': result.alternative_queries,
                'confidence_score': result.confidence_score,
                'processing_time_ms': result.processing_time_ms,
                'used_mappings': [
                    {
                        'business_term': m.business_term,
                        'schema_element_path': m.schema_element_path,
                        'confidence_score': m.confidence_score
                    }
                    for m in result.used_mappings
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to build intelligent query: {e}")
            return {
                'success': False,
                'error': str(e),
                'sql': '',
                'confidence_score': 0.0
            }
    
    async def get_schema_change_history(
        self,
        database: Optional[str] = None,
        table: Optional[str] = None,
        change_types: Optional[List[str]] = None,
        severity_levels: Optional[List[str]] = None,
        since: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get schema change history with optional filtering.
        
        Args:
            database: Filter by database name
            table: Filter by table name
            change_types: Filter by change types
            severity_levels: Filter by severity levels
            since: Filter by changes since this ISO datetime string
            limit: Maximum number of changes to return
            
        Returns:
            List of schema changes
        """
        if not self.enable_change_detection or not self.change_detector:
            logger.warning("Schema change detection is not enabled")
            return []
        
        try:
            # Convert string parameters to proper types
            change_type = None
            if change_types and len(change_types) == 1:
                from .change_detector import ChangeType
                try:
                    change_type = ChangeType(change_types[0])
                except ValueError:
                    pass
            
            severity = None
            if severity_levels and len(severity_levels) == 1:
                from .change_detector import ChangeSeverity
                try:
                    severity = ChangeSeverity(severity_levels[0])
                except ValueError:
                    pass
            
            since_dt = None
            if since:
                try:
                    since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                except ValueError:
                    pass
            
            # Get filtered changes
            changes = self.change_detector.get_change_history(
                database=database,
                table=table,
                change_type=change_type,
                severity=severity,
                since=since_dt,
                limit=limit
            )
            
            # Convert to serializable format
            result = []
            for change in changes:
                result.append({
                    'change_id': change.change_id,
                    'change_type': change.change_type.value,
                    'severity': change.severity.value,
                    'database': change.database,
                    'table': change.table,
                    'element_name': change.element_name,
                    'old_definition': change.old_definition,
                    'new_definition': change.new_definition,
                    'detected_at': change.detected_at.isoformat(),
                    'impact_analysis': change.impact_analysis,
                    'migration_suggestions': change.migration_suggestions,
                    'affected_queries': change.affected_queries
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get schema change history: {e}")
            return []
    
    async def force_schema_change_check(self) -> Dict[str, Any]:
        """
        Force an immediate check for schema changes.
        
        Returns:
            Dictionary with check results
        """
        if not self.enable_change_detection or not self.change_detector:
            return {
                'success': False,
                'error': 'Schema change detection is not enabled',
                'changes_detected': 0
            }
        
        try:
            changes = await self.change_detector.force_schema_check()
            
            return {
                'success': True,
                'changes_detected': len(changes),
                'changes': [
                    {
                        'change_type': c.change_type.value,
                        'severity': c.severity.value,
                        'database': c.database,
                        'table': c.table,
                        'element_name': c.element_name
                    }
                    for c in changes
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to force schema change check: {e}")
            return {
                'success': False,
                'error': str(e),
                'changes_detected': 0
            }
    
    async def get_semantic_mapping_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about semantic mapping performance.
        
        Returns:
            Dictionary with semantic mapping statistics
        """
        if not self.enable_semantic_mapping or not self.semantic_mapper:
            return {
                'enabled': False,
                'message': 'Semantic mapping is not enabled'
            }
        
        try:
            return {
                'enabled': True,
                **self.semantic_mapper.get_mapping_statistics()
            }
        except Exception as e:
            logger.error(f"Failed to get semantic mapping statistics: {e}")
            return {
                'enabled': True,
                'error': str(e)
            }
    
    async def get_change_detection_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about schema change detection.
        
        Returns:
            Dictionary with change detection statistics
        """
        if not self.enable_change_detection or not self.change_detector:
            return {
                'enabled': False,
                'message': 'Schema change detection is not enabled'
            }
        
        try:
            return {
                'enabled': True,
                **self.change_detector.get_change_statistics()
            }
        except Exception as e:
            logger.error(f"Failed to get change detection statistics: {e}")
            return {
                'enabled': True,
                'error': str(e)
            }
    
    async def _ensure_schema_analyzed(self):
        """Ensure that current database schemas have been analyzed for semantic mapping."""
        try:
            databases = await self.discover_databases()
            
            for database in databases:
                if database.accessible:
                    tables = await self.get_tables(database.name)
                    
                    for table in tables:
                        table_schema = await self.get_table_schema(database.name, table.name)
                        if table_schema and self.semantic_mapper:
                            # Analyze table schema for semantic information
                            await self.semantic_mapper.analyze_table_schema(table_schema)
            
            logger.debug("Schema analysis completed for semantic mapping")
            
        except Exception as e:
            logger.error(f"Failed to ensure schema analyzed: {e}")
    
    def learn_from_successful_query(
        self,
        business_term: str,
        schema_element_path: str,
        success_score: float = 1.0
    ):
        """
        Learn from a successful query to improve future semantic mappings.
        
        Args:
            business_term: Business term that was successfully mapped
            schema_element_path: Schema element that was successfully used
            success_score: Score indicating how successful the mapping was (0.0 to 1.0)
        """
        if not self.enable_semantic_mapping or not self.semantic_mapper:
            logger.warning("Semantic mapping is not enabled - cannot learn from successful query")
            return
        
        try:
            from .semantic_mapper import SemanticMapping
            
            # Create a mapping object for learning
            mapping = SemanticMapping(
                business_term=business_term,
                schema_element_type='column',  # Assume column for now
                schema_element_path=schema_element_path,
                confidence_score=0.8,  # Base confidence
                similarity_type='learned',
                context_match=True,
                metadata={'learned_from_query': True},
                created_at=datetime.now()
            )
            
            # Learn from this successful mapping
            self.semantic_mapper.learn_successful_mapping(mapping, success_score)
            
            logger.info(f"Learned from successful mapping: '{business_term}' -> '{schema_element_path}'")
            
        except Exception as e:
            logger.error(f"Failed to learn from successful query: {e}")
    
    def add_schema_change_listener(self, listener_func):
        """
        Add a listener function to be notified of schema changes.
        
        Args:
            listener_func: Function to call when schema changes are detected
        """
        if not self.enable_change_detection or not self.change_detector:
            logger.warning("Schema change detection is not enabled - cannot add listener")
            return
        
        self.change_detector.add_change_listener(listener_func)
        logger.info("Added schema change listener")
    
    def remove_schema_change_listener(self, listener_func):
        """
        Remove a schema change listener function.
        
        Args:
            listener_func: Function to remove from listeners
        """
        if not self.enable_change_detection or not self.change_detector:
            logger.warning("Schema change detection is not enabled - cannot remove listener")
            return
        
        self.change_detector.remove_change_listener(listener_func)
        logger.info("Removed schema change listener")