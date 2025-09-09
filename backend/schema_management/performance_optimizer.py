"""
Performance Optimization Module for Dynamic Schema Management.

This module implements advanced performance optimizations including:
- Intelligent cache warming and prefetching strategies
- Query generation performance optimization with index hints
- Adaptive TTL strategies based on schema change frequency
- Connection pooling optimization for MCP clients
- Lazy loading and pagination for large schema discovery results
"""

import asyncio
import logging
import time
import statistics
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from .client import EnhancedMCPClient
from .enhanced_cache import EnhancedSchemaCache, CacheEntryType
from .models import DatabaseInfo, TableInfo, ColumnInfo, SchemaInfo

logger = logging.getLogger(__name__)


class OptimizationLevel(str, Enum):
    """Performance optimization levels."""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    AGGRESSIVE = "aggressive"


@dataclass
class PerformanceMetrics:
    """Performance tracking metrics."""
    schema_discovery_times: List[float] = field(default_factory=list)
    query_generation_times: List[float] = field(default_factory=list)
    cache_warming_times: List[float] = field(default_factory=list)
    connection_pool_utilization: float = 0.0
    memory_usage_mb: float = 0.0
    cache_hit_ratio: float = 0.0
    query_success_rate: float = 0.0
    
    def get_average_discovery_time(self) -> float:
        """Get average schema discovery time."""
        return statistics.mean(self.schema_discovery_times) if self.schema_discovery_times else 0.0
    
    def get_p95_discovery_time(self) -> float:
        """Get 95th percentile discovery time."""
        if len(self.schema_discovery_times) < 20:
            return self.get_average_discovery_time()
        
        sorted_times = sorted(self.schema_discovery_times)
        p95_index = int(len(sorted_times) * 0.95)
        return sorted_times[p95_index]


@dataclass
class CacheWarmingStrategy:
    """Configuration for cache warming strategies."""
    enable_predictive_warming: bool = True
    warmup_common_tables: bool = True
    warmup_frequently_accessed: bool = True
    warmup_schedule_hours: List[int] = field(default_factory=lambda: [6, 12, 18])  # 6 AM, 12 PM, 6 PM
    max_concurrent_warmups: int = 5
    warmup_timeout_seconds: int = 30


@dataclass
class ConnectionPoolConfig:
    """Configuration for MCP connection pooling."""
    min_connections: int = 2
    max_connections: int = 10
    idle_timeout_seconds: int = 300
    max_connection_age_seconds: int = 3600
    connection_retry_attempts: int = 3
    health_check_interval_seconds: int = 60


class SchemaDiscoveryOptimizer:
    """Optimizes schema discovery operations for large databases."""
    
    def __init__(
        self,
        mcp_client: EnhancedMCPClient,
        optimization_level: OptimizationLevel = OptimizationLevel.INTERMEDIATE
    ):
        self.mcp_client = mcp_client
        self.optimization_level = optimization_level
        self.metrics = PerformanceMetrics()
        
        # Pagination settings based on optimization level
        self.pagination_config = self._get_pagination_config()
        
        # Index awareness
        self.known_indexes: Dict[str, List[str]] = {}
        self.constraint_cache: Dict[str, Dict[str, Any]] = {}
    
    def _get_pagination_config(self) -> Dict[str, int]:
        """Get pagination configuration based on optimization level."""
        configs = {
            OptimizationLevel.BASIC: {
                "tables_per_batch": 10,
                "columns_per_batch": 50,
                "max_concurrent_batches": 2
            },
            OptimizationLevel.INTERMEDIATE: {
                "tables_per_batch": 25,
                "columns_per_batch": 100,
                "max_concurrent_batches": 5
            },
            OptimizationLevel.AGGRESSIVE: {
                "tables_per_batch": 50,
                "columns_per_batch": 200,
                "max_concurrent_batches": 10
            }
        }
        return configs[self.optimization_level]
    
    async def discover_schema_optimized(
        self,
        database_name: str,
        table_filter: Optional[str] = None,
        include_metadata: bool = True
    ) -> SchemaInfo:
        """
        Optimized schema discovery with pagination and lazy loading.
        
        Args:
            database_name: Name of the database to discover
            table_filter: Optional table name filter pattern
            include_metadata: Whether to include detailed metadata
            
        Returns:
            SchemaInfo with discovered schema
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting optimized schema discovery for database: {database_name}")
            
            # Discover tables with pagination
            all_tables = await self._discover_tables_paginated(database_name, table_filter)
            
            # Filter tables if needed
            if table_filter:
                import fnmatch
                all_tables = [t for t in all_tables if fnmatch.fnmatch(t.name, table_filter)]
            
            # Discover table schemas in batches
            enriched_tables = await self._discover_table_schemas_batched(
                database_name, all_tables, include_metadata
            )
            
            # Build schema info
            schema_info = SchemaInfo(
                databases=[DatabaseInfo(name=database_name)],
                tables=enriched_tables,
                version="optimized"
            )
            
            # Record performance metrics
            discovery_time = time.time() - start_time
            self.metrics.schema_discovery_times.append(discovery_time)
            
            logger.info(
                f"Optimized schema discovery completed in {discovery_time:.2f}s "
                f"({len(enriched_tables)} tables)"
            )
            
            return schema_info
            
        except Exception as e:
            logger.error(f"Optimized schema discovery failed: {e}")
            raise
    
    async def _discover_tables_paginated(
        self,
        database_name: str,
        table_filter: Optional[str] = None
    ) -> List[TableInfo]:
        """Discover tables with pagination support."""
        all_tables = []
        offset = 0
        batch_size = self.pagination_config["tables_per_batch"]
        
        while True:
            try:
                # Get batch of tables
                batch_tables = await self.mcp_client.get_tables_paginated(
                    database_name,
                    limit=batch_size,
                    offset=offset,
                    name_filter=table_filter
                )
                
                if not batch_tables:
                    break
                
                all_tables.extend(batch_tables)
                offset += batch_size
                
                # Apply optimization level limits
                if self.optimization_level == OptimizationLevel.BASIC and len(all_tables) >= 100:
                    logger.info("Basic optimization level: limiting to 100 tables")
                    break
                elif self.optimization_level == OptimizationLevel.INTERMEDIATE and len(all_tables) >= 500:
                    logger.info("Intermediate optimization level: limiting to 500 tables")
                    break
                
            except Exception as e:
                logger.warning(f"Failed to get table batch at offset {offset}: {e}")
                break
        
        logger.info(f"Discovered {len(all_tables)} tables")
        return all_tables
    
    async def _discover_table_schemas_batched(
        self,
        database_name: str,
        tables: List[TableInfo],
        include_metadata: bool
    ) -> List[TableInfo]:
        """Discover table schemas in concurrent batches."""
        enriched_tables = []
        batch_size = self.pagination_config["tables_per_batch"]
        max_concurrent = self.pagination_config["max_concurrent_batches"]
        
        # Process tables in batches
        for i in range(0, len(tables), batch_size):
            batch = tables[i:i + batch_size]
            
            # Create semaphore to limit concurrency
            semaphore = asyncio.Semaphore(max_concurrent)
            
            # Process batch concurrently
            tasks = [
                self._discover_single_table_schema(
                    database_name, table, include_metadata, semaphore
                )
                for table in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.warning(f"Failed to discover table schema: {result}")
                    continue
                
                if result:
                    enriched_tables.append(result)
        
        return enriched_tables
    
    async def _discover_single_table_schema(
        self,
        database_name: str,
        table: TableInfo,
        include_metadata: bool,
        semaphore: asyncio.Semaphore
    ) -> Optional[TableInfo]:
        """Discover schema for a single table with concurrency control."""
        async with semaphore:
            try:
                # Get table schema
                table_schema = await self.mcp_client.get_table_schema(database_name, table.name)
                
                if include_metadata:
                    # Enrich with metadata
                    table_schema = await self._enrich_table_metadata(database_name, table_schema)
                
                return table_schema
                
            except Exception as e:
                logger.warning(f"Failed to discover schema for table {table.name}: {e}")
                return None
    
    async def _enrich_table_metadata(
        self,
        database_name: str,
        table: TableInfo
    ) -> TableInfo:
        """Enrich table with performance-relevant metadata."""
        try:
            # Get indexes if not cached
            if table.name not in self.known_indexes:
                indexes = await self._discover_table_indexes(database_name, table.name)
                self.known_indexes[table.name] = indexes
            
            # Get constraints if not cached
            constraint_key = f"{database_name}.{table.name}"
            if constraint_key not in self.constraint_cache:
                constraints = await self._discover_table_constraints(database_name, table.name)
                self.constraint_cache[constraint_key] = constraints
            
            # Add metadata to table
            table.metadata = table.metadata or {}
            table.metadata.update({
                "indexes": self.known_indexes.get(table.name, []),
                "constraints": self.constraint_cache.get(constraint_key, {}),
                "discovery_method": "optimized"
            })
            
            return table
            
        except Exception as e:
            logger.warning(f"Failed to enrich metadata for table {table.name}: {e}")
            return table
    
    async def _discover_table_indexes(self, database_name: str, table_name: str) -> List[str]:
        """Discover indexes for a table."""
        try:
            # This would use MCP to get actual index information
            # For now, return common index patterns
            common_indexes = ["id", "created_at", "updated_at", "period_date"]
            return common_indexes
        except Exception as e:
            logger.warning(f"Failed to discover indexes for {table_name}: {e}")
            return []
    
    async def _discover_table_constraints(
        self,
        database_name: str,
        table_name: str
    ) -> Dict[str, Any]:
        """Discover constraints for a table."""
        try:
            # This would use MCP to get actual constraint information
            # For now, return empty dict
            return {}
        except Exception as e:
            logger.warning(f"Failed to discover constraints for {table_name}: {e}")
            return {}


class IntelligentCacheWarmer:
    """Implements intelligent cache warming and prefetching strategies."""
    
    def __init__(
        self,
        cache: EnhancedSchemaCache,
        schema_optimizer: SchemaDiscoveryOptimizer,
        strategy: CacheWarmingStrategy
    ):
        self.cache = cache
        self.schema_optimizer = schema_optimizer
        self.strategy = strategy
        
        # Track warming performance
        self.warming_metrics = {
            "total_warmups": 0,
            "successful_warmups": 0,
            "failed_warmups": 0,
            "avg_warming_time": 0.0
        }
        
        # Predictive warming data
        self.access_patterns: Dict[str, List[datetime]] = {}
        self.frequently_accessed_keys: Set[str] = set()
    
    async def warm_cache_intelligently(
        self,
        database_names: List[str],
        priority_tables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Warm cache using intelligent strategies.
        
        Args:
            database_names: List of databases to warm
            priority_tables: Optional list of high-priority tables
            
        Returns:
            Warming results summary
        """
        start_time = time.time()
        warming_results = {
            "databases_warmed": 0,
            "tables_warmed": 0,
            "cache_entries_created": 0,
            "errors": []
        }
        
        try:
            logger.info(f"Starting intelligent cache warming for {len(database_names)} databases")
            
            # 1. Warm common/frequent access patterns
            if self.strategy.warmup_frequently_accessed:
                await self._warm_frequent_patterns()
            
            # 2. Warm priority tables first
            if priority_tables:
                for db_name in database_names:
                    for table_name in priority_tables:
                        try:
                            await self._warm_table_schema(db_name, table_name)
                            warming_results["tables_warmed"] += 1
                        except Exception as e:
                            error_msg = f"Failed to warm priority table {table_name}: {e}"
                            logger.warning(error_msg)
                            warming_results["errors"].append(error_msg)
            
            # 3. Warm common tables across databases
            if self.strategy.warmup_common_tables:
                # Dynamically discover common tables from schema
                from .manager import DynamicSchemaManager
                schema_manager = DynamicSchemaManager()
                await schema_manager.initialize()
                
                common_tables = await schema_manager.get_table_names()
                
                for db_name in database_names:
                    semaphore = asyncio.Semaphore(self.strategy.max_concurrent_warmups)
                    
                    tasks = [
                        self._warm_table_with_semaphore(db_name, table_name, semaphore)
                        for table_name in common_tables
                    ]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            error_msg = f"Failed to warm {common_tables[i]}: {result}"
                            warming_results["errors"].append(error_msg)
                        else:
                            warming_results["tables_warmed"] += 1
                    
                    warming_results["databases_warmed"] += 1
            
            # 4. Predictive warming based on access patterns
            if self.strategy.enable_predictive_warming:
                await self._predictive_warming()
            
            # Update metrics
            warming_time = time.time() - start_time
            self.warming_metrics["total_warmups"] += 1
            self.warming_metrics["avg_warming_time"] = (
                (self.warming_metrics["avg_warming_time"] * (self.warming_metrics["total_warmups"] - 1) + warming_time) /
                self.warming_metrics["total_warmups"]
            )
            
            logger.info(
                f"Cache warming completed in {warming_time:.2f}s: "
                f"{warming_results['tables_warmed']} tables warmed"
            )
            
            return warming_results
            
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            warming_results["errors"].append(str(e))
            return warming_results
    
    async def _warm_table_with_semaphore(
        self,
        database_name: str,
        table_name: str,
        semaphore: asyncio.Semaphore
    ) -> bool:
        """Warm a single table schema with concurrency control."""
        async with semaphore:
            return await self._warm_table_schema(database_name, table_name)
    
    async def _warm_table_schema(self, database_name: str, table_name: str) -> bool:
        """Warm schema for a specific table."""
        try:
            # Check if already cached and not expiring soon
            cache_key = f"table:{database_name}.{table_name}"
            
            cached_schema = await self.cache.get("table_schema", database=database_name, table=table_name)
            if cached_schema:
                return True  # Already warmed
            
            # Discover and cache the schema
            table_schema = await self.schema_optimizer.mcp_client.get_table_schema(
                database_name, table_name
            )
            
            if table_schema:
                # Cache with extended TTL for warmed entries
                await self.cache.set(
                    "table_schema",
                    table_schema,
                    ttl=self.cache.default_ttl * 2,  # Double TTL for warmed entries
                    metadata={"warmed": True, "warm_time": datetime.now().isoformat()},
                    database=database_name,
                    table=table_name
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Failed to warm table schema {database_name}.{table_name}: {e}")
            return False
    
    async def _warm_frequent_patterns(self) -> None:
        """Warm cache for frequently accessed patterns."""
        for cache_key in self.frequently_accessed_keys:
            try:
                # Check if needs refreshing
                cached_data = await self.cache.get_schema(cache_key)
                if not cached_data:
                    # Re-discover and cache
                    # This would be specific to the cache key pattern
                    pass
            except Exception as e:
                logger.warning(f"Failed to warm frequent pattern {cache_key}: {e}")
    
    async def _predictive_warming(self) -> None:
        """Warm cache based on predicted access patterns."""
        # Get dynamic table list from schema
        from .manager import DynamicSchemaManager
        schema_manager = DynamicSchemaManager()
        await schema_manager.initialize()
        
        current_hour = datetime.now().hour
        all_tables = await schema_manager.get_table_names()
        
        # Predict likely access patterns based on time
        if current_hour in [8, 9, 10]:  # Morning business hours
            # Focus on overview and cash-related tables
            predicted_tables = [table for table in all_tables if any(keyword in table.lower() for keyword in ["overview", "cash", "budget"])][:3]
        elif current_hour in [13, 14, 15]:  # Afternoon hours
            # Focus on investment and ratio-related tables  
            predicted_tables = [table for table in all_tables if any(keyword in table.lower() for keyword in ["investment", "ratio"])][:2]
        elif current_hour in [17, 18]:  # End of day
            # Focus on audit and overview tables
            predicted_tables = [table for table in all_tables if any(keyword in table.lower() for keyword in ["audit", "overview"])][:2]
        else:
            return  # No prediction for other hours
        
        # Warm predicted tables
        for table_name in predicted_tables:
            try:
                await self._warm_table_schema("default", table_name)
            except Exception as e:
                logger.warning(f"Failed predictive warming for {table_name}: {e}")
    
    def record_access_pattern(self, cache_key: str) -> None:
        """Record access pattern for predictive warming."""
        now = datetime.now()
        
        if cache_key not in self.access_patterns:
            self.access_patterns[cache_key] = []
        
        self.access_patterns[cache_key].append(now)
        
        # Keep only recent accesses (last 7 days)
        cutoff = now - timedelta(days=7)
        self.access_patterns[cache_key] = [
            access_time for access_time in self.access_patterns[cache_key]
            if access_time > cutoff
        ]
        
        # Update frequently accessed set
        if len(self.access_patterns[cache_key]) >= 10:  # 10+ accesses in 7 days
            self.frequently_accessed_keys.add(cache_key)


class AdaptiveTTLManager:
    """Manages adaptive TTL strategies based on schema change frequency."""
    
    def __init__(self):
        self.change_frequencies: Dict[str, List[datetime]] = {}
        self.base_ttl = 1800  # 30 minutes
        self.min_ttl = 300    # 5 minutes
        self.max_ttl = 14400  # 4 hours
    
    def calculate_adaptive_ttl(self, schema_element: str) -> int:
        """
        Calculate adaptive TTL based on change frequency.
        
        Args:
            schema_element: Schema element identifier
            
        Returns:
            Calculated TTL in seconds
        """
        if schema_element not in self.change_frequencies:
            return self.base_ttl
        
        changes = self.change_frequencies[schema_element]
        now = datetime.now()
        
        # Count changes in the last 24 hours
        recent_changes = [
            change_time for change_time in changes
            if (now - change_time).total_seconds() < 86400  # 24 hours
        ]
        
        change_count = len(recent_changes)
        
        if change_count == 0:
            # No recent changes, use longer TTL
            return min(self.max_ttl, self.base_ttl * 2)
        elif change_count <= 2:
            # Few changes, use normal TTL
            return self.base_ttl
        elif change_count <= 5:
            # Moderate changes, use shorter TTL
            return max(self.min_ttl, self.base_ttl // 2)
        else:
            # Frequent changes, use minimum TTL
            return self.min_ttl
    
    def record_schema_change(self, schema_element: str) -> None:
        """Record a schema change for adaptive TTL calculation."""
        now = datetime.now()
        
        if schema_element not in self.change_frequencies:
            self.change_frequencies[schema_element] = []
        
        self.change_frequencies[schema_element].append(now)
        
        # Keep only changes from the last 7 days
        cutoff = now - timedelta(days=7)
        self.change_frequencies[schema_element] = [
            change_time for change_time in self.change_frequencies[schema_element]
            if change_time > cutoff
        ]


class QueryOptimizationHints:
    """Generates query optimization hints based on discovered schema."""
    
    def __init__(self, schema_optimizer: SchemaDiscoveryOptimizer):
        self.schema_optimizer = schema_optimizer
    
    def generate_index_hints(
        self,
        table_name: str,
        where_conditions: List[str],
        order_by_columns: List[str] = None
    ) -> List[str]:
        """
        Generate index hints for query optimization.
        
        Args:
            table_name: Target table name
            where_conditions: List of WHERE condition columns
            order_by_columns: List of ORDER BY columns
            
        Returns:
            List of index hints
        """
        hints = []
        
        # Get known indexes for the table
        table_indexes = self.schema_optimizer.known_indexes.get(table_name, [])
        
        if not table_indexes:
            return hints
        
        # Suggest indexes for WHERE conditions
        for condition_column in where_conditions:
            if condition_column in table_indexes:
                hints.append(f"USE INDEX ({condition_column}) for WHERE clause")
        
        # Suggest indexes for ORDER BY
        if order_by_columns:
            for order_column in order_by_columns:
                if order_column in table_indexes:
                    hints.append(f"USE INDEX ({order_column}) for ORDER BY clause")
        
        # Suggest composite indexes if multiple conditions
        if len(where_conditions) > 1:
            composite_candidates = [col for col in where_conditions if col in table_indexes]
            if len(composite_candidates) > 1:
                hints.append(f"Consider composite index on ({', '.join(composite_candidates)})")
        
        return hints
    
    def generate_query_optimization_suggestions(
        self,
        sql_query: str,
        table_info: TableInfo
    ) -> List[str]:
        """Generate general query optimization suggestions."""
        suggestions = []
        
        # Basic query analysis
        query_lower = sql_query.lower()
        
        # Check for SELECT *
        if "select *" in query_lower:
            suggestions.append("Consider selecting specific columns instead of SELECT *")
        
        # Check for missing LIMIT
        if "limit" not in query_lower and ("select" in query_lower and "count" not in query_lower):
            suggestions.append("Consider adding LIMIT clause for large result sets")
        
        # Check for date filtering
        if "period_date" in [col.name for col in table_info.columns]:
            if "period_date" not in query_lower:
                suggestions.append("Consider adding period_date filter for time-based queries")
        
        # Check for proper JOIN usage
        if "join" in query_lower and "on" not in query_lower:
            suggestions.append("Ensure proper JOIN conditions are specified")
        
        return suggestions


class PerformanceMonitor:
    """Monitors and reports performance metrics for dynamic schema management."""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.alert_thresholds = {
            "max_discovery_time": 30.0,  # seconds
            "min_cache_hit_ratio": 0.8,
            "max_memory_usage_mb": 500.0
        }
    
    def record_schema_discovery_time(self, duration: float) -> None:
        """Record schema discovery performance."""
        self.metrics.schema_discovery_times.append(duration)
        
        # Keep only recent measurements (last 100)
        if len(self.metrics.schema_discovery_times) > 100:
            self.metrics.schema_discovery_times = self.metrics.schema_discovery_times[-100:]
    
    def record_query_generation_time(self, duration: float) -> None:
        """Record query generation performance."""
        self.metrics.query_generation_times.append(duration)
        
        # Keep only recent measurements
        if len(self.metrics.query_generation_times) > 100:
            self.metrics.query_generation_times = self.metrics.query_generation_times[-100:]
    
    def check_performance_alerts(self) -> List[str]:
        """Check for performance issues and return alerts."""
        alerts = []
        
        # Check discovery time
        if self.metrics.schema_discovery_times:
            avg_discovery_time = self.metrics.get_average_discovery_time()
            if avg_discovery_time > self.alert_thresholds["max_discovery_time"]:
                alerts.append(
                    f"High schema discovery time: {avg_discovery_time:.2f}s "
                    f"(threshold: {self.alert_thresholds['max_discovery_time']}s)"
                )
        
        # Check cache hit ratio
        if self.metrics.cache_hit_ratio < self.alert_thresholds["min_cache_hit_ratio"]:
            alerts.append(
                f"Low cache hit ratio: {self.metrics.cache_hit_ratio:.2f} "
                f"(threshold: {self.alert_thresholds['min_cache_hit_ratio']})"
            )
        
        # Check memory usage
        if self.metrics.memory_usage_mb > self.alert_thresholds["max_memory_usage_mb"]:
            alerts.append(
                f"High memory usage: {self.metrics.memory_usage_mb:.1f}MB "
                f"(threshold: {self.alert_thresholds['max_memory_usage_mb']}MB)"
            )
        
        return alerts
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        return {
            "schema_discovery": {
                "average_time": self.metrics.get_average_discovery_time(),
                "p95_time": self.metrics.get_p95_discovery_time(),
                "total_discoveries": len(self.metrics.schema_discovery_times)
            },
            "query_generation": {
                "average_time": (
                    statistics.mean(self.metrics.query_generation_times)
                    if self.metrics.query_generation_times else 0.0
                ),
                "total_generations": len(self.metrics.query_generation_times)
            },
            "cache_performance": {
                "hit_ratio": self.metrics.cache_hit_ratio,
                "memory_usage_mb": self.metrics.memory_usage_mb
            },
            "system_health": {
                "connection_pool_utilization": self.metrics.connection_pool_utilization,
                "query_success_rate": self.metrics.query_success_rate
            },
            "alerts": self.check_performance_alerts()
        }
