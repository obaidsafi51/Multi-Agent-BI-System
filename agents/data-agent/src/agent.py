"""
Main Data Agent service with TiDB integration and Dynamic Schema Management.
Orchestrates query processing, caching, validation, and optimization using real-time schema discovery.
"""

import asyncio
import json
import time
import sys
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

import structlog

from .database.connection import get_connection_manager, close_connection_manager
from .query.generator import get_query_generator
from .query.validator import get_data_validator
from .cache.manager import get_cache_manager, close_cache_manager
from .optimization.optimizer import get_query_optimizer

# Add backend to path for dynamic schema management imports
backend_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend')
sys.path.append(backend_path)

try:
    from schema_management.dynamic_schema_manager import get_dynamic_schema_manager
    from schema_management.intelligent_query_builder import get_intelligent_query_builder
    DYNAMIC_SCHEMA_AVAILABLE = True
except ImportError as e:
    print(f"Dynamic schema management not available: {e}")
    DYNAMIC_SCHEMA_AVAILABLE = False

logger = structlog.get_logger(__name__)


class DataAgent:
    """
    Main Data Agent service that processes financial data queries.
    Integrates TiDB connection, query generation, caching, validation, optimization,
    and dynamic schema management for intelligent query processing.
    """
    
    def __init__(self):
        """Initialize Data Agent with all components including dynamic schema management."""
        self.connection_manager = None
        self.query_generator = None
        self.data_validator = None
        self.cache_manager = None
        self.query_optimizer = None
        
        # Dynamic schema management components
        self.dynamic_schema_manager = None
        self.intelligent_query_builder = None
        self.use_dynamic_schema = DYNAMIC_SCHEMA_AVAILABLE
        
        self.is_initialized = False
        
        # Performance metrics
        self.metrics = {
            'queries_processed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_query_time': 0.0,
            'total_processing_time': 0.0,
            'errors': 0,
            'dynamic_queries': 0,
            'static_queries': 0,
            'schema_discoveries': 0,
            'last_reset': time.time()
        }
    
    async def initialize(self) -> None:
        """Initialize all Data Agent components including dynamic schema management."""
        try:
            logger.info("Initializing Data Agent components with dynamic schema management...")
            
            # Initialize connection manager
            self.connection_manager = await get_connection_manager()
            
            # Initialize traditional components
            self.query_generator = get_query_generator()
            self.data_validator = get_data_validator()
            self.cache_manager = await get_cache_manager()
            self.query_optimizer = get_query_optimizer()
            
            # Initialize dynamic schema management if available
            if DYNAMIC_SCHEMA_AVAILABLE:
                try:
                    self.dynamic_schema_manager = await get_dynamic_schema_manager()
                    self.intelligent_query_builder = await get_intelligent_query_builder(
                        self.dynamic_schema_manager
                    )
                    logger.info("Dynamic schema management initialized successfully")
                except Exception as e:
                    logger.warning(f"Failed to initialize dynamic schema management: {e}")
                    self.use_dynamic_schema = False
            else:
                logger.info("Dynamic schema management not available, using traditional mode")
                self.use_dynamic_schema = False
            
            self.is_initialized = True
            
            logger.info(
                f"Data Agent initialized successfully "
                f"(Dynamic Schema: {'enabled' if self.use_dynamic_schema else 'disabled'})"
            )
            
        except Exception as e:
            logger.error("Failed to initialize Data Agent", error=str(e))
            raise
    
    async def process_query(
        self, 
        query_intent: Dict[str, Any], 
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a financial data query from intent to results.
        
        Args:
            query_intent: Structured query intent from NLP agent
            user_context: Additional user context for optimization
            
        Returns:
            Dictionary containing query results and metadata
        """
        if not self.is_initialized:
            raise RuntimeError("Data Agent not initialized")
        
        start_time = time.time()
        query_id = f"query_{int(time.time() * 1000)}"
        
        try:
            logger.info(
                "Processing query",
                query_id=query_id,
                metric_type=query_intent.get('metric_type'),
                time_period=query_intent.get('time_period')
            )
            
            # Step 1: Check cache first (using dynamic cache tags if available)
            cache_key = self._generate_cache_key_dynamic(query_intent)
            cached_result = await self.cache_manager.get('query', cache_key)
            
            if cached_result:
                self.metrics['cache_hits'] += 1
                logger.info(f"Cache hit for query_id={query_id}, cache_key={cache_key}")
                
                # Add cache metadata
                cached_result['metadata']['cache_hit'] = True
                cached_result['metadata']['processing_time_ms'] = int((time.time() - start_time) * 1000)
                cached_result['metadata']['query_method'] = 'cached'
                
                return cached_result
            
            self.metrics['cache_misses'] += 1
            
            # Step 2: Generate SQL query using dynamic schema management or fallback
            sql_query = await self._generate_query_dynamic(query_intent, user_context)
            
            # Step 3: Optimize query
            query_plan = self.query_optimizer.optimize_query(
                sql_query.sql, 
                user_context
            )
            
            # Step 4: Execute query
            query_result = await self.connection_manager.execute_query(
                query_plan.optimized_query,
                sql_query.params,
                fetch_all=True
            )
            
            # Step 5: Validate results
            validation_result = self.data_validator.validate_query_result(
                query_result,
                query_intent.get('metric_type', ''),
                query_intent.get('aggregation_level', 'monthly')
            )
            
            # Step 6: Build response
            response = self._build_response(
                query_id=query_id,
                query_intent=query_intent,
                query_result=query_result,
                validation_result=validation_result,
                query_plan=query_plan,
                processing_time=time.time() - start_time
            )
            
            # Step 7: Cache successful results (using dynamic cache tags)
            if validation_result.is_valid and validation_result.quality_score > 0.7:
                cache_tags = self._generate_cache_tags_dynamic(query_intent)
                await self.cache_manager.set(
                    'query',
                    cache_key,
                    response,
                    ttl=1800,  # 30 minutes
                    tags=cache_tags
                )
            
            # Update metrics
            self._update_metrics(time.time() - start_time, success=True)
            
            logger.info(
                "Query processed successfully",
                query_id=query_id,
                processing_time_ms=int((time.time() - start_time) * 1000),
                data_quality_score=validation_result.quality_score,
                cache_stored=validation_result.is_valid
            )
            
            return response
            
        except Exception as e:
            self._update_metrics(time.time() - start_time, success=False)
            
            logger.error(
                "Query processing failed",
                query_id=query_id,
                error=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            
            # Return error response
            return {
                'query_id': query_id,
                'success': False,
                'error': {
                    'type': 'processing_error',
                    'message': str(e),
                    'code': 'DATA_AGENT_ERROR'
                },
                'data': [],
                'metadata': {
                    'processing_time_ms': int((time.time() - start_time) * 1000),
                    'timestamp': datetime.now().isoformat()
                }
            }
    
    async def get_data_summary(
        self, 
        table_name: str, 
        date_range: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Get summary statistics for a financial data table.
        
        Args:
            table_name: Name of the table to summarize
            date_range: Optional date range filter
            
        Returns:
            Dictionary containing summary statistics
        """
        try:
            # Build summary query
            base_query = f"""
            SELECT 
                COUNT(*) as total_records,
                MIN(period_date) as earliest_date,
                MAX(period_date) as latest_date,
                COUNT(DISTINCT period_date) as unique_periods
            FROM {table_name}
            """
            
            params = {}
            if date_range:
                base_query += " WHERE period_date BETWEEN :start_date AND :end_date"
                params.update(date_range)
            
            # Execute query
            result = await self.connection_manager.execute_query(base_query, params)
            
            return {
                'table_name': table_name,
                'summary': result['data'][0] if result['data'] else {},
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'query_time_ms': result['execution_time_ms']
                }
            }
            
        except Exception as e:
            logger.error("Failed to get data summary", table=table_name, error=str(e))
            raise
    
    async def invalidate_cache(self, tags: Optional[List[str]] = None) -> int:
        """
        Invalidate cached data by tags.
        
        Args:
            tags: List of cache tags to invalidate
            
        Returns:
            Number of cache entries invalidated
        """
        try:
            if tags:
                invalidated = await self.cache_manager.invalidate_by_tags(tags)
            else:
                # Clear all cache
                await self.cache_manager.clear_all()
                invalidated = -1  # Indicate full clear
            
            logger.info("Cache invalidation completed", tags=tags, invalidated_count=invalidated)
            
            return invalidated
            
        except Exception as e:
            logger.error("Cache invalidation failed", error=str(e))
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of all components.
        
        Returns:
            Dictionary containing health status and metrics
        """
        health_status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'components': {},
            'metrics': self.metrics.copy(),
            'errors': []
        }
        
        try:
            # Check database connection
            if self.connection_manager:
                db_health = await self.connection_manager.health_check()
                health_status['components']['database'] = db_health
                if db_health['status'] != 'healthy':
                    health_status['status'] = 'degraded'
            
            # Check cache manager
            if self.cache_manager:
                cache_health = await self.cache_manager.health_check()
                health_status['components']['cache'] = cache_health
                if cache_health['status'] != 'healthy':
                    health_status['status'] = 'degraded'
            
            # Check query optimizer
            if self.query_optimizer:
                optimizer_stats = self.query_optimizer.get_optimization_stats()
                health_status['components']['optimizer'] = {
                    'status': 'healthy',
                    'stats': optimizer_stats
                }
            
            # Check dynamic schema management
            if self.use_dynamic_schema:
                schema_health = {
                    'status': 'healthy',
                    'dynamic_schema_manager': 'available' if self.dynamic_schema_manager else 'unavailable',
                    'intelligent_query_builder': 'available' if self.intelligent_query_builder else 'unavailable'
                }
                
                # Get schema manager metrics if available
                if self.dynamic_schema_manager:
                    try:
                        schema_metrics = self.dynamic_schema_manager.get_metrics()
                        schema_health['metrics'] = schema_metrics
                    except Exception as e:
                        schema_health['metrics_error'] = str(e)
                        schema_health['status'] = 'degraded'
                
                health_status['components']['dynamic_schema'] = schema_health
            else:
                health_status['components']['dynamic_schema'] = {
                    'status': 'disabled',
                    'mode': 'static_fallback'
                }
            
            # Overall status assessment
            if any(comp.get('status') == 'unhealthy' for comp in health_status['components'].values()):
                health_status['status'] = 'unhealthy'
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['errors'].append(str(e))
            logger.error("Health check failed", error=str(e))
        
        return health_status
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get Data Agent performance metrics."""
        metrics = self.metrics.copy()
        
        # Add component-specific metrics
        if self.cache_manager:
            cache_stats = await self.cache_manager.get_stats()
            metrics['cache'] = {
                'hit_rate': cache_stats.hit_rate,
                'total_requests': cache_stats.total_requests,
                'entry_count': cache_stats.entry_count,
                'size_bytes': cache_stats.total_size_bytes
            }
        
        if self.query_optimizer:
            optimizer_stats = self.query_optimizer.get_optimization_stats()
            metrics['optimizer'] = optimizer_stats
        
        # Add dynamic schema management metrics
        if self.use_dynamic_schema:
            dynamic_metrics = {
                'dynamic_queries': self.metrics.get('dynamic_queries', 0),
                'static_queries': self.metrics.get('static_queries', 0),
                'schema_discoveries': self.metrics.get('schema_discoveries', 0),
                'dynamic_ratio': (
                    self.metrics.get('dynamic_queries', 0) / 
                    max(self.metrics['queries_processed'], 1)
                )
            }
            
            # Add schema manager metrics if available
            if self.dynamic_schema_manager:
                try:
                    schema_manager_metrics = self.dynamic_schema_manager.get_metrics()
                    dynamic_metrics['schema_manager'] = schema_manager_metrics
                except Exception as e:
                    dynamic_metrics['schema_manager_error'] = str(e)
            
            # Add query builder metrics if available
            if self.intelligent_query_builder:
                try:
                    builder_metrics = self.intelligent_query_builder.get_metrics()
                    dynamic_metrics['query_builder'] = builder_metrics
                except Exception as e:
                    dynamic_metrics['query_builder_error'] = str(e)
            
            metrics['dynamic_schema'] = dynamic_metrics
        
        return metrics
    
    async def close(self) -> None:
        """Close all Data Agent components and cleanup resources."""
        try:
            logger.info("Closing Data Agent components...")
            
            if self.cache_manager:
                await close_cache_manager()
            
            if self.connection_manager:
                await close_connection_manager()
            
            self.is_initialized = False
            
            logger.info("Data Agent closed successfully")
            
        except Exception as e:
            logger.error("Error closing Data Agent", error=str(e))
            raise
    
    def _generate_cache_key(self, query_intent: Dict[str, Any]) -> str:
        """Generate cache key from query intent."""
        key_components = [
            query_intent.get('metric_type', ''),
            query_intent.get('time_period', ''),
            query_intent.get('aggregation_level', ''),
            json.dumps(query_intent.get('filters', {}), sort_keys=True),
            json.dumps(query_intent.get('comparison_periods', []), sort_keys=True)
        ]
        
        return '_'.join(key_components)
    
    def _generate_cache_tags(self, query_intent: Dict[str, Any]) -> List[str]:
        """Generate cache tags for invalidation."""
        tags = []
        
        metric_type = query_intent.get('metric_type', '')
        if metric_type:
            tags.append(f"metric:{metric_type}")
        
        # Add table-based tags
        if metric_type in ['revenue', 'profit', 'expenses']:
            tags.append('table:financial_overview')
        elif 'cash_flow' in metric_type:
            tags.append('table:cash_flow')
        elif 'budget' in metric_type:
            tags.append('table:budget_tracking')
        elif 'investment' in metric_type:
            tags.append('table:investments')
        elif 'ratio' in metric_type:
            tags.append('table:financial_ratios')
        
        # Add time-based tags
        time_period = query_intent.get('time_period', '')
        if time_period:
            tags.append(f"period:{time_period}")
        
        return tags
    
    def _build_response(
        self,
        query_id: str,
        query_intent: Dict[str, Any],
        query_result: Dict[str, Any],
        validation_result: Any,
        query_plan: Any,
        processing_time: float
    ) -> Dict[str, Any]:
        """Build comprehensive response object."""
        
        return {
            'query_id': query_id,
            'success': True,
            'data': query_result['data'],
            'columns': query_result['columns'],
            'row_count': query_result['row_count'],
            'metadata': {
                'query_intent': query_intent,
                'processing_time_ms': int(processing_time * 1000),
                'database_time_ms': query_result['execution_time_ms'],
                'data_quality': {
                    'is_valid': validation_result.is_valid,
                    'quality_score': validation_result.quality_score,
                    'issues': validation_result.issues,
                    'warnings': validation_result.warnings
                },
                'optimization': {
                    'applied_optimizations': query_plan.applied_optimizations,
                    'estimated_improvement': query_plan.optimization_confidence,
                    'complexity_score': query_plan.estimated_cost
                },
                'cache_hit': False,
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def _update_metrics(self, processing_time: float, success: bool) -> None:
        """Update performance metrics."""
        self.metrics['queries_processed'] += 1
        self.metrics['total_processing_time'] += processing_time
        
        if success:
            # Update average query time
            total_queries = self.metrics['queries_processed']
            self.metrics['avg_query_time'] = (
                (self.metrics['avg_query_time'] * (total_queries - 1) + processing_time) 
                / total_queries
            )
        else:
            self.metrics['errors'] += 1
    
    async def _generate_query_dynamic(
        self, 
        query_intent: Dict[str, Any], 
        user_context: Optional[Dict[str, Any]] = None
    ):
        """
        Generate SQL query using dynamic schema management or fallback to static.
        
        Args:
            query_intent: Structured query intent from NLP agent
            user_context: Additional user context for optimization
            
        Returns:
            SQL query object (from intelligent builder or traditional generator)
        """
        # Try dynamic schema management first
        if self.use_dynamic_schema and self.intelligent_query_builder:
            try:
                logger.info("Using dynamic schema management for query generation")
                
                # Generate query context with schema discovery
                query_context = await self.dynamic_schema_manager.generate_query_context(query_intent)
                
                # Build query using intelligent query builder
                query_result = await self.intelligent_query_builder.build_query(
                    query_intent, 
                    query_context
                )
                
                self.metrics['dynamic_queries'] += 1
                logger.info(
                    f"Dynamic query generated with confidence: {query_result.confidence_score:.2f}"
                )
                
                return query_result
                
            except Exception as e:
                logger.warning(f"Dynamic query generation failed: {e}, falling back to static")
                self.use_dynamic_schema = False  # Temporarily disable for this session
        
        # Fallback to traditional query generation
        logger.info("Using traditional static query generation")
        self.metrics['static_queries'] += 1
        return self.query_generator.generate_query(query_intent)
    
    def _generate_cache_key_dynamic(self, query_intent: Dict[str, Any]) -> str:
        """
        Generate cache key using dynamic schema context.
        
        This version includes schema version information to ensure cache invalidation
        when schema changes occur.
        """
        # Include schema version if available
        schema_version = "unknown"
        if self.dynamic_schema_manager and hasattr(self.dynamic_schema_manager, 'metrics'):
            schema_version = str(self.dynamic_schema_manager.metrics.get('last_schema_update', 'unknown'))
        
        key_components = [
            query_intent.get('metric_type', ''),
            query_intent.get('time_period', ''),
            query_intent.get('aggregation_level', ''),
            json.dumps(query_intent.get('filters', {}), sort_keys=True),
            json.dumps(query_intent.get('comparison_periods', []), sort_keys=True),
            f"schema_v:{schema_version}"
        ]
        
        return '_'.join(key_components)
    
    def _generate_cache_tags_dynamic(self, query_intent: Dict[str, Any]) -> List[str]:
        """
        Generate cache tags using discovered table information.
        
        This replaces static table name references with dynamic discovery.
        """
        tags = []
        
        metric_type = query_intent.get('metric_type', '')
        if metric_type:
            tags.append(f"metric:{metric_type}")
        
        # Try to get actual table mappings from schema manager
        if self.dynamic_schema_manager:
            try:
                # This is a synchronous approximation - in reality you'd cache this info
                table_mappings = self.dynamic_schema_manager.business_mappings.get(metric_type.lower())
                if table_mappings:
                    table_name, _ = table_mappings
                    tags.append(f"table:{table_name}")
                else:
                    # Try semantic matching for unknown metrics
                    tags.append(f"unknown_metric:{metric_type}")
            except Exception as e:
                logger.warning(f"Failed to generate dynamic cache tags: {e}")
                # Fallback to basic tagging
                tags.append(f"metric:{metric_type}")
        else:
            # Use original static logic as fallback
            if metric_type in ['revenue', 'profit', 'expenses']:
                tags.append('table:financial_overview')
            elif 'cash_flow' in metric_type:
                tags.append('table:cash_flow')
            elif 'budget' in metric_type:
                tags.append('table:budget_tracking')
            elif 'investment' in metric_type:
                tags.append('table:investments')
            elif 'ratio' in metric_type:
                tags.append('table:financial_ratios')
        
        # Add time-based tags
        time_period = query_intent.get('time_period', '')
        if time_period:
            tags.append(f"period:{time_period}")
        
        return tags
    
    async def invalidate_schema_cache(self, scope: str = "schema") -> int:
        """
        Invalidate schema-related caches when schema changes are detected.
        
        Args:
            scope: Scope of invalidation ('schema', 'tables', 'all')
            
        Returns:
            Number of cache entries invalidated
        """
        try:
            # Invalidate schema manager cache if available
            if self.dynamic_schema_manager:
                await self.dynamic_schema_manager.invalidate_schema_cache(scope)
            
            # Invalidate data agent query cache for schema-dependent entries
            schema_tags = [f"scope:{scope}"]
            if scope == "all":
                await self.cache_manager.clear_all()
                invalidated = -1
            else:
                invalidated = await self.cache_manager.invalidate_by_tags(schema_tags)
            
            logger.info(
                f"Schema cache invalidation completed",
                scope=scope,
                invalidated_count=invalidated
            )
            
            return invalidated
            
        except Exception as e:
            logger.error(f"Schema cache invalidation failed: {e}")
            raise
    
    async def discover_schema_changes(self) -> Dict[str, Any]:
        """
        Check for schema changes and return discovery results.
        
        Returns:
            Dictionary containing schema change information
        """
        if not self.dynamic_schema_manager:
            return {
                "dynamic_schema_available": False,
                "message": "Dynamic schema management not available"
            }
        
        try:
            # Force fresh schema discovery
            schema_info = await self.dynamic_schema_manager.discover_schema(force_refresh=True)
            self.metrics['schema_discoveries'] += 1
            
            return {
                "dynamic_schema_available": True,
                "schema_version": schema_info.version,
                "tables_discovered": len(schema_info.tables),
                "discovery_timestamp": datetime.now().isoformat(),
                "schema_manager_metrics": self.dynamic_schema_manager.get_metrics()
            }
            
        except Exception as e:
            logger.error(f"Schema discovery failed: {e}")
            return {
                "dynamic_schema_available": True,
                "error": str(e),
                "discovery_timestamp": datetime.now().isoformat()
            }


# Global data agent instance
_data_agent: Optional[DataAgent] = None


async def get_data_agent() -> DataAgent:
    """Get or create global data agent instance."""
    global _data_agent
    
    if _data_agent is None:
        _data_agent = DataAgent()
        await _data_agent.initialize()
    
    return _data_agent


async def close_data_agent() -> None:
    """Close global data agent."""
    global _data_agent
    
    if _data_agent:
        await _data_agent.close()
        _data_agent = None