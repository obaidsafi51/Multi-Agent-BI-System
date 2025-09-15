"""
Enhanced Data Agent with MCP Client integration.
Integrates with TiDB MCP Server through Model Context Protocol for database operations.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from .mcp_client import get_mcp_client, close_mcp_client
from .query.generator import get_query_generator
from .query.validator import get_data_validator
from .cache.manager import get_cache_manager, close_cache_manager
from .optimization.optimizer import get_query_optimizer

logger = structlog.get_logger(__name__)


class MCPDataAgent:
    """
    Enhanced Data Agent service that processes financial data queries using MCP protocol.
    Integrates with TiDB MCP Server for database operations, with caching, validation, and optimization.
    """
    
    def __init__(self):
        """Initialize MCP Data Agent with all components."""
        self.mcp_client = None
        self.query_generator = None
        self.data_validator = None
        self.cache_manager = None
        self.query_optimizer = None
        self.is_initialized = False
        
        # Get database name from environment variable
        self.default_database = os.getenv('TIDB_DATABASE', 'Agentic_BI')
        
        # Performance metrics
        self.metrics = {
            'queries_processed': 0,
            'mcp_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_query_time': 0.0,
            'total_processing_time': 0.0,
            'errors': 0,
            'last_reset': time.time()
        }
    
    async def initialize(self) -> None:
        """Initialize all MCP Data Agent components."""
        try:
            logger.info("Initializing MCP Data Agent components...")
            
            # Initialize MCP client
            self.mcp_client = get_mcp_client()
            connected = await self.mcp_client.connect()
            
            if not connected:
                logger.warning("Failed to connect to TiDB MCP Server, will retry on first request")
            
            # Initialize other components
            self.query_generator = get_query_generator(default_database=self.default_database)
            self.data_validator = get_data_validator()
            self.cache_manager = await get_cache_manager()
            self.query_optimizer = get_query_optimizer()
            
            self.is_initialized = True
            
            logger.info("MCP Data Agent initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize MCP Data Agent", error=str(e))
            raise
    
    async def process_query(
        self, 
        query_intent: Dict[str, Any], 
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a financial data query from intent to results using MCP protocol.
        
        Args:
            query_intent: Structured query intent from NLP agent
            user_context: Additional user context for optimization
            
        Returns:
            Dictionary containing query results and metadata
        """
        if not self.is_initialized:
            raise RuntimeError("MCP Data Agent not initialized")
        
        start_time = time.time()
        query_id = f"mcp_query_{int(time.time() * 1000)}"
        
        try:
            logger.info(
                "Processing query via MCP",
                query_id=query_id,
                metric_type=query_intent.get('metric_type'),
                time_period=query_intent.get('time_period')
            )
            
            # Step 1: Check cache first
            cache_key = self._generate_cache_key(query_intent)
            cached_result = await self.cache_manager.get('query', cache_key)
            
            if cached_result:
                self.metrics['cache_hits'] += 1
                logger.info(f"Cache hit for query_id={query_id}, cache_key={cache_key}")
                
                # Add cache metadata
                cached_result['metadata']['cache_hit'] = True
                cached_result['metadata']['processing_time_ms'] = int((time.time() - start_time) * 1000)
                
                return cached_result
            
            self.metrics['cache_misses'] += 1
            
            # Step 2: Ensure MCP connection
            if not self.mcp_client.is_connected:
                connected = await self.mcp_client.connect()
                if not connected:
                    raise RuntimeError("Failed to connect to TiDB MCP Server")
            
            # Step 3: Generate SQL query
            sql_query = self.query_generator.generate_query(query_intent)
            
            # Step 4: Validate query with MCP server
            validation_result = await self.mcp_client.validate_query(sql_query.sql)
            if not validation_result or not validation_result.get('valid', True):
                raise ValueError(f"Query validation failed: {validation_result}")
            
            # Step 5: Optimize query
            query_plan = self.query_optimizer.optimize_query(
                sql_query.sql, 
                user_context
            )
            
            # Step 6: Execute query via MCP
            mcp_result = await self.mcp_client.execute_query(
                query=query_plan.optimized_query,
                timeout=30,
                use_cache=True
            )
            
            self.metrics['mcp_requests'] += 1
            
            if not mcp_result or not mcp_result.get('success', False):
                error_msg = mcp_result.get('error', 'Unknown MCP error') if mcp_result else 'No response from MCP server'
                raise RuntimeError(f"MCP query execution failed: {error_msg}")
            
            # Convert MCP result to internal format
            query_result = {
                'data': mcp_result.get('rows', []),
                'columns': mcp_result.get('columns', []),
                'row_count': mcp_result.get('row_count', 0),
                'execution_time_ms': mcp_result.get('execution_time_ms', 0)
            }
            
            # Step 7: Validate results
            data_validation = self.data_validator.validate_query_result(
                query_result,
                query_intent.get('metric_type', ''),
                query_intent.get('aggregation_level', 'monthly')
            )
            
            # Step 8: Build response
            response = self._build_response(
                query_id=query_id,
                query_intent=query_intent,
                query_result=query_result,
                validation_result=data_validation,
                query_plan=query_plan,
                mcp_result=mcp_result,
                processing_time=time.time() - start_time
            )
            
            # Step 9: Cache successful results
            if data_validation.is_valid and data_validation.quality_score > 0.7:
                cache_tags = self._generate_cache_tags(query_intent)
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
                "Query processed successfully via MCP",
                query_id=query_id,
                processing_time_ms=int((time.time() - start_time) * 1000),
                data_quality_score=data_validation.quality_score,
                cache_stored=data_validation.is_valid,
                mcp_execution_time_ms=mcp_result.get('execution_time_ms', 0)
            )
            
            return response
            
        except Exception as e:
            self._update_metrics(time.time() - start_time, success=False)
            
            logger.error(
                "MCP query processing failed",
                query_id=query_id,
                error=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            
            # Return error response
            return {
                'query_id': query_id,
                'success': False,
                'error': {
                    'type': 'mcp_processing_error',
                    'message': str(e),
                    'code': 'MCP_DATA_AGENT_ERROR'
                },
                'data': [],
                'metadata': {
                    'processing_time_ms': int((time.time() - start_time) * 1000),
                    'timestamp': datetime.now().isoformat(),
                    'mcp_used': True
                }
            }
    
    async def discover_schema(self, database: str = None) -> Dict[str, Any]:
        """
        Discover database schema using MCP protocol.
        
        Args:
            database: Database name to discover (defaults to environment TIDB_DATABASE)
            
        Returns:
            Dictionary containing schema information
        """
        if database is None:
            database = self.default_database
            
        try:
            logger.info("Discovering schema via MCP", database=database)
            
            # Ensure MCP connection
            if not self.mcp_client.is_connected:
                await self.mcp_client.connect()
            
            # Get database info
            databases = await self.mcp_client.discover_databases()
            target_db = next((db for db in databases if db['name'] == database), None)
            
            if not target_db:
                raise ValueError(f"Database '{database}' not found")
            
            # Get tables
            tables = await self.mcp_client.discover_tables(database)
            
            # Get detailed schema for key tables
            detailed_schemas = {}
            financial_tables = ['revenue', 'expenses', 'cashflow', 'cfo_kpis', 'pnl_statement', 'balance_Sheet']
            
            for table_info in tables:
                table_name = table_info['name']
                if table_name in financial_tables:
                    schema = await self.mcp_client.get_table_schema(database, table_name)
                    if schema:
                        detailed_schemas[table_name] = schema
            
            return {
                'database': target_db,
                'tables': tables,
                'detailed_schemas': detailed_schemas,
                'discovery_method': 'mcp',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Schema discovery failed", database=database, error=str(e))
            raise
    
    async def get_sample_data(
        self, 
        table_name: str, 
        database: str = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get sample data from a table using MCP protocol.
        
        Args:
            table_name: Name of the table
            database: Database name (defaults to environment TIDB_DATABASE)
            limit: Number of sample rows
            
        Returns:
            Dictionary containing sample data
        """
        if database is None:
            database = self.default_database
            
        try:
            logger.info("Getting sample data via MCP", table=table_name, database=database, limit=limit)
            
            # Ensure MCP connection
            if not self.mcp_client.is_connected:
                await self.mcp_client.connect()
            
            # Get sample data via MCP
            sample_result = await self.mcp_client.get_sample_data(
                database=database,
                table=table_name,
                limit=limit
            )
            
            if not sample_result:
                raise ValueError(f"Failed to get sample data for {database}.{table_name}")
            
            return {
                'table_name': table_name,
                'database': database,
                'sample_data': sample_result,
                'method': 'mcp',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Sample data retrieval failed", table=table_name, error=str(e))
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Simplified health check for MCP agent.
        
        Returns:
            Basic health status
        """
        try:
            mcp_connected = await self.mcp_client.health_check() if self.mcp_client else False
            return {
                'status': 'healthy' if mcp_connected else 'degraded',
                'timestamp': time.time(),
                'mcp_connected': mcp_connected
            }
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                'status': 'unhealthy',
                'timestamp': time.time(),
                'error': str(e)
            }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get MCP Data Agent performance metrics."""
        metrics = self.metrics.copy()
        
        # Add MCP-specific metrics
        if self.mcp_client:
            try:
                mcp_stats = await self.mcp_client.get_server_stats()
                metrics['mcp_server'] = mcp_stats
            except Exception:
                pass
        
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
        
        return metrics
    
    async def execute_sql(
        self,
        sql_query: str,
        query_context: Optional[Dict[str, Any]] = None,
        query_id: Optional[str] = None,
        execution_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute raw SQL query via MCP protocol for WebSocket requests.
        
        Args:
            sql_query: Raw SQL query to execute
            query_context: Query context information
            query_id: Unique query identifier
            execution_config: Execution configuration
            
        Returns:
            Dictionary containing query results and metadata
        """
        if not self.is_initialized:
            raise RuntimeError("MCP Data Agent not initialized")
        
        start_time = time.time()
        query_id = query_id or f"sql_query_{int(time.time() * 1000)}"
        
        try:
            logger.info(f"Executing SQL query via MCP: {query_id}")
            
            # Ensure MCP connection
            if not self.mcp_client.is_connected:
                connected = await self.mcp_client.connect()
                if not connected:
                    raise RuntimeError("Failed to connect to TiDB MCP Server")
            
            # Execute raw SQL query through MCP
            mcp_result = await self.mcp_client.execute_query(
                query=sql_query,
                timeout=30,
                use_cache=execution_config.get('use_cache', True) if execution_config else True
            )
            
            self.metrics['queries_processed'] += 1
            self.metrics['mcp_requests'] += 1
            
            if not mcp_result or not mcp_result.get('success'):
                error_msg = mcp_result.get('error', 'Unknown MCP error') if mcp_result else 'No response from MCP server'
                raise RuntimeError(f"MCP query execution failed: {error_msg}")
            
            # Extract data from MCP response
            data = mcp_result.get('data', [])
            columns = mcp_result.get('columns', [])
            row_count = len(data)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Build response
            response = {
                'success': True,
                'query_id': query_id,
                'data': data,
                'columns': columns,
                'row_count': row_count,
                'processing_time_ms': int(processing_time),
                'metadata': {
                    'query_id': query_id,
                    'processing_time_ms': int(processing_time),
                    'database_time_ms': mcp_result.get('execution_time_ms', 0),
                    'timestamp': datetime.utcnow().isoformat(),
                    'data_source': 'mcp_server',
                    'cache_hit': False
                }
            }
            
            # Update metrics
            self._update_metrics(processing_time / 1000, success=True)
            
            logger.info(f"SQL query executed successfully: {query_id} in {processing_time:.2f}ms")
            
            return response
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self._update_metrics(processing_time / 1000, success=False)
            
            logger.error(f"SQL query execution failed: {query_id}, error: {e}")
            
            return {
                'success': False,
                'query_id': query_id,
                'error': {
                    'type': 'sql_execution_error',
                    'message': str(e),
                    'code': 'MCP_SQL_ERROR'
                },
                'data': [],
                'columns': [],
                'row_count': 0,
                'processing_time_ms': int(processing_time),
                'metadata': {
                    'query_id': query_id,
                    'processing_time_ms': int(processing_time),
                    'timestamp': datetime.utcnow().isoformat(),
                    'data_source': 'mcp_server',
                    'cache_hit': False,
                    'error': True
                }
            }
    
    async def close(self) -> None:
        """Close all MCP Data Agent components and cleanup resources."""
        try:
            logger.info("Closing MCP Data Agent components...")
            
            if self.cache_manager:
                await close_cache_manager()
            
            if self.mcp_client:
                await close_mcp_client()
            
            self.is_initialized = False
            
            logger.info("MCP Data Agent closed successfully")
            
        except Exception as e:
            logger.error("Error closing MCP Data Agent", error=str(e))
            raise
    
    def _generate_cache_key(self, query_intent: Dict[str, Any]) -> str:
        """Generate cache key from query intent."""
        key_components = [
            'mcp',  # Add MCP prefix to differentiate from direct DB cache
            query_intent.get('metric_type', ''),
            query_intent.get('time_period', ''),
            query_intent.get('aggregation_level', ''),
            json.dumps(query_intent.get('filters', {}), sort_keys=True),
            json.dumps(query_intent.get('comparison_periods', []), sort_keys=True)
        ]
        
        return '_'.join(key_components)
    
    def _generate_cache_tags(self, query_intent: Dict[str, Any]) -> List[str]:
        """Generate cache tags for invalidation."""
        tags = ['mcp']  # Add MCP tag
        
        metric_type = query_intent.get('metric_type', '')
        if metric_type:
            tags.append(f"metric:{metric_type}")
        
        # Add table-based tags
        if metric_type in ['revenue', 'sales', 'income']:
            tags.append('table:revenue')
        elif metric_type in ['expenses', 'costs']:
            tags.append('table:expenses')
        elif 'cash_flow' in metric_type or 'cash' in metric_type:
            tags.append('table:cashflow')
        elif 'profit' in metric_type or 'pnl' in metric_type:
            tags.append('table:pnl_statement')
        elif 'kpi' in metric_type:
            tags.append('table:cfo_kpis')
        
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
        mcp_result: Dict[str, Any],
        processing_time: float
    ) -> Dict[str, Any]:
        """Build comprehensive response object with MCP metadata."""
        
        return {
            'query_id': query_id,
            'success': True,
            'data': query_result['data'],
            'columns': query_result['columns'],
            'row_count': query_result['row_count'],
            'metadata': {
                'query_intent': query_intent,
                'processing_time_ms': int(processing_time * 1000),
                'mcp_execution_time_ms': mcp_result.get('execution_time_ms', 0),
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
                'mcp_metadata': {
                    'truncated': mcp_result.get('truncated', False),
                    'server_cache_used': mcp_result.get('execution_time_ms', 0) < 100,  # Heuristic for server cache
                    'execution_method': 'mcp_protocol'
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


# Global MCP data agent instance
_mcp_data_agent: Optional[MCPDataAgent] = None


async def get_mcp_data_agent() -> MCPDataAgent:
    """Get or create global MCP data agent instance."""
    global _mcp_data_agent
    
    if _mcp_data_agent is None:
        _mcp_data_agent = MCPDataAgent()
        await _mcp_data_agent.initialize()
    
    return _mcp_data_agent


async def close_mcp_data_agent() -> None:
    """Close global MCP data agent."""
    global _mcp_data_agent
    
    if _mcp_data_agent:
        await _mcp_data_agent.close()
        _mcp_data_agent = None
