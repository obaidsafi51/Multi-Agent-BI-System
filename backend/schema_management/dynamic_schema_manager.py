"""
Dynamic Schema Manager - Core orchestrator for all schema-related operations.

This module provides the central interface for schema discovery, semantic mapping,
and query generation used by all agents in the system.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from .manager import MCPSchemaManager
from .client import EnhancedMCPClient
from .enhanced_cache import EnhancedSchemaCache
from .models import (
    DatabaseInfo, TableInfo, ColumnInfo, SchemaInfo, 
    ValidationResult, ValidationError, ValidationWarning
)

logger = logging.getLogger(__name__)


class SchemaMapping:
    """Represents a mapping between business terms and schema elements."""
    
    def __init__(
        self,
        business_term: str,
        schema_path: str,
        table_name: str,
        column_name: str,
        confidence_score: float,
        mapping_type: str = "semantic"
    ):
        self.business_term = business_term
        self.schema_path = schema_path
        self.table_name = table_name
        self.column_name = column_name
        self.confidence_score = confidence_score
        self.mapping_type = mapping_type


class QueryContext:
    """Enhanced query context with discovered schema information."""
    
    def __init__(
        self,
        intent: Dict[str, Any],
        table_mappings: List[SchemaMapping],
        column_mappings: List[SchemaMapping],
        suggested_joins: List[str] = None,
        optimization_hints: List[str] = None
    ):
        self.intent = intent
        self.table_mappings = table_mappings
        self.column_mappings = column_mappings
        self.suggested_joins = suggested_joins or []
        self.optimization_hints = optimization_hints or []


class DynamicSchemaManager:
    """
    Core manager for dynamic schema operations across all agents.
    
    Provides unified interface for:
    - Schema discovery and caching
    - Business term to database mapping
    - Query context generation
    - Schema change detection and notification
    """
    
    def __init__(
        self,
        mcp_client: Optional[EnhancedMCPClient] = None,
        cache: Optional[EnhancedSchemaCache] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.mcp_client = mcp_client
        self.cache = cache
        self.config = config or self._get_default_config()
        
        # Initialize schema manager
        self.schema_manager = MCPSchemaManager()
        
        # Initialize business term mappings (basic implementation)
        self._init_business_mappings()
        
        # Performance metrics
        self.metrics = {
            'schema_discoveries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'mapping_requests': 0,
            'last_schema_update': None
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for dynamic schema manager."""
        return {
            'cache_ttl': 1800,  # 30 minutes
            'discovery_timeout': 30,  # seconds
            'confidence_threshold': 0.7,
            'max_alternatives': 5,
            'enable_learning': True
        }
    
    def _init_business_mappings(self) -> None:
        """Initialize dynamic business term discovery."""
        # Remove static mappings - use dynamic discovery instead
        self.business_mappings = {}
        self._dynamic_mappings_cache = {}
        self._mapping_cache_ttl = 300  # 5 minute TTL for mapping cache
    
    async def discover_schema(self, force_refresh: bool = False, fast_mode: bool = False) -> SchemaInfo:
        """
        Discover complete database schema with semantic analysis.
        
        Args:
            force_refresh: If True, bypass cache and force fresh discovery
            fast_mode: If True, only discover primary database for quick results
            
        Returns:
            SchemaInfo containing discovered tables, columns, and metadata
        """
        try:
            cache_key = "complete_schema" if not fast_mode else "fast_schema"
            
            # Check cache first unless forced refresh
            if not force_refresh and self.cache:
                cached_schema = await self.cache.get_schema(cache_key)
                if cached_schema:
                    self.metrics['cache_hits'] += 1
                    logger.info(f"Schema discovery cache hit (fast_mode={fast_mode})")
                    return cached_schema
            
            self.metrics['cache_misses'] += 1
            logger.info(f"Performing fresh schema discovery (fast_mode={fast_mode})")
            
            # Discover schema using MCP
            if fast_mode:
                schema_info = await self._perform_fast_schema_discovery()
            else:
                schema_info = await self._perform_schema_discovery()
            
            # Cache the result
            if self.cache:
                await self.cache.set_schema(
                    cache_key, 
                    schema_info, 
                    ttl=3600 if fast_mode else self.config['cache_ttl']  # Fast mode cache expires sooner
                )
            
            self.metrics['schema_discoveries'] += 1
            self.metrics['last_schema_update'] = datetime.now()
            
            logger.info(f"Schema discovery completed: {len(schema_info.tables)} tables found (fast_mode={fast_mode})")
            return schema_info
            
        except Exception as e:
            logger.error(f"Schema discovery failed: {e}")
            # Return minimal fallback schema
            return self._get_fallback_schema()
    
    async def _perform_schema_discovery(self) -> SchemaInfo:
        """Perform actual schema discovery via MCP with parallel processing."""
        try:
            # Use the schema manager for discovery
            databases = await self.schema_manager.discover_databases()
            
            # Filter out system databases that cause performance issues
            system_databases = {'INFORMATION_SCHEMA', 'PERFORMANCE_SCHEMA', 'mysql', 'sys'}
            filtered_databases = [db for db in databases if db.name not in system_databases]
            
            logger.info(f"Discovered {len(databases)} total databases, filtering to {len(filtered_databases)} user databases")
            
            schema_info = SchemaInfo(databases=[], tables=[], version="dynamic")
            
            # Process databases in parallel with limited concurrency
            import asyncio
            semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent database discoveries
            
            async def discover_database_tables(db):
                async with semaphore:
                    try:
                        logger.info(f"Starting discovery for database: {db.name}")
                        tables = await self.schema_manager.get_tables(db.name)
                        
                        # Process tables in parallel within each database
                        table_semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent table schemas
                        
                        async def get_table_schema_safe(table):
                            async with table_semaphore:
                                try:
                                    return await self.schema_manager.get_table_schema(db.name, table.name)
                                except Exception as e:
                                    logger.warning(f"Failed to get schema for {db.name}.{table.name}: {e}")
                                    return None
                        
                        # Get all table schemas in parallel
                        table_schemas = await asyncio.gather(
                            *[get_table_schema_safe(table) for table in tables],
                            return_exceptions=True
                        )
                        
                        # Filter out None results and exceptions
                        valid_schemas = [schema for schema in table_schemas 
                                       if schema is not None and not isinstance(schema, Exception)]
                        
                        logger.info(f"Successfully discovered {len(valid_schemas)}/{len(tables)} tables for database {db.name}")
                        return valid_schemas
                        
                    except Exception as e:
                        logger.error(f"Failed to discover database {db.name}: {e}")
                        return []
            
            # Execute database discoveries in parallel
            database_results = await asyncio.gather(
                *[discover_database_tables(db) for db in filtered_databases],
                return_exceptions=True
            )
            
            # Flatten results and add to schema_info
            for result in database_results:
                if isinstance(result, list):
                    schema_info.tables.extend(result)
            
            logger.info(f"Schema discovery completed: {len(schema_info.tables)} tables discovered")
            return schema_info
            
        except Exception as e:
            logger.warning(f"MCP schema discovery failed, using fallback: {e}")
            return self._get_fallback_schema()

    async def _perform_fast_schema_discovery(self) -> SchemaInfo:
        """Perform fast schema discovery focusing on primary database only."""
        try:
            # Use the schema manager for discovery
            databases = await self.schema_manager.discover_databases()
            
            # Filter out system databases and prioritize primary databases
            system_databases = {'INFORMATION_SCHEMA', 'PERFORMANCE_SCHEMA', 'mysql', 'sys'}
            priority_databases = ['Agentic_BI', 'agentic_bi']  # Primary business databases
            
            # Find priority database first
            primary_db = None
            for db in databases:
                if db.name in priority_databases and db.name not in system_databases:
                    primary_db = db
                    break
            
            # If no priority database found, use first non-system database
            if not primary_db:
                for db in databases:
                    if db.name not in system_databases:
                        primary_db = db
                        break
            
            if not primary_db:
                logger.warning("No suitable database found for fast discovery")
                return self._get_fallback_schema()
            
            logger.info(f"Fast discovery focusing on database: {primary_db.name}")
            
            schema_info = SchemaInfo(databases=[], tables=[], version="fast")
            
            # Fast approach: Get table list only, skip detailed schema for speed
            tables = await self.schema_manager.get_tables(primary_db.name)
            
            # Convert TableInfo to basic schema representation for fast response
            for table in tables:
                # Create a basic table representation without full schema details
                basic_table = type('BasicTable', (), {
                    'name': table.name,
                    'database': primary_db.name,
                    'type': table.type,
                    'rows': table.rows,
                    'size_mb': table.size_mb,
                    'columns': []  # Empty for fast mode - avoid slow schema calls
                })()
                schema_info.tables.append(basic_table)
            
            logger.info(f"Fast schema discovery completed: {len(tables)} tables from {primary_db.name} (basic info only)")
            return schema_info
            
        except Exception as e:
            logger.warning(f"MCP schema discovery failed, using fallback: {e}")
            return self._get_fallback_schema()
    
    def _get_fallback_schema(self) -> SchemaInfo:
        """Return fallback schema when discovery fails."""
        # Create basic schema info for known tables
        tables = []
        
        # Financial overview table
        financial_cols = [
            ColumnInfo(name="period_date", data_type="DATE", is_nullable=False),
            ColumnInfo(name="revenue", data_type="DECIMAL", is_nullable=True),
            ColumnInfo(name="net_income", data_type="DECIMAL", is_nullable=True),
            ColumnInfo(name="total_expenses", data_type="DECIMAL", is_nullable=True)
        ]
        tables.append(TableInfo(name="financial_overview", columns=financial_cols))
        
        # Cash flow table
        cashflow_cols = [
            ColumnInfo(name="period_date", data_type="DATE", is_nullable=False),
            ColumnInfo(name="operating_cash_flow", data_type="DECIMAL", is_nullable=True),
            ColumnInfo(name="investing_cash_flow", data_type="DECIMAL", is_nullable=True),
            ColumnInfo(name="financing_cash_flow", data_type="DECIMAL", is_nullable=True),
            ColumnInfo(name="net_cash_flow", data_type="DECIMAL", is_nullable=True)
        ]
        tables.append(TableInfo(name="cash_flow", columns=cashflow_cols))
        
        return SchemaInfo(tables=tables, databases=[], version="fallback")
    
    async def find_tables_for_metric(self, metric_type: str) -> List[SchemaMapping]:
        """
        Find database tables that contain data for the specified metric.
        
        Args:
            metric_type: Business metric type (e.g., 'revenue', 'cash_flow')
            
        Returns:
            List of schema mappings with confidence scores
        """
        self.metrics['mapping_requests'] += 1
        
        metric_lower = metric_type.lower()
        mappings = []
        
        # Use dynamic discovery instead of static mappings
        # Check if we have cached dynamic mappings
        if metric_lower in self._dynamic_mappings_cache:
            cached_mapping = self._dynamic_mappings_cache[metric_lower]
            if time.time() - cached_mapping['timestamp'] < self._mapping_cache_ttl:
                table_name, column_name = cached_mapping['mapping']
                mapping = SchemaMapping(
                    business_term=metric_type,
                    schema_path=f"default.{table_name}.{column_name}",
                    table_name=table_name,
                    column_name=column_name,
                    confidence_score=0.85,  # Slightly lower for dynamic discovery
                    mapping_type="dynamic_cached"
                )
                mappings.append(mapping)
        
        # Look for semantic matches (this should now be the primary method)
        semantic_matches = await self._find_semantic_matches(metric_lower)
        mappings.extend(semantic_matches)
        
        # Sort by confidence score
        mappings.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return mappings[:self.config['max_alternatives']]
    
    async def _find_semantic_matches(self, metric_term: str) -> List[SchemaMapping]:
        """Find semantic matches for a business term using dynamic discovery."""
        matches = []
        
        try:
            # Get all available tables dynamically
            available_tables = await self.get_table_names()
            
            # Create dynamic semantic matching based on table and column names
            for table_name in available_tables:
                try:
                    # Get table schema to check column names
                    table_schema = await self.get_table_schema(table_name)
                    if not table_schema:
                        continue
                    
                    columns = table_schema.get('columns', {})
                    
                    # Find columns that semantically match the metric term
                    for column_name in columns.keys():
                        confidence = self._calculate_semantic_confidence(metric_term, table_name, column_name)
                        
                        if confidence > 0.5:  # Only include matches with reasonable confidence
                            mapping = SchemaMapping(
                                business_term=metric_term,
                                schema_path=f"default.{table_name}.{column_name}",
                                table_name=table_name,
                                column_name=column_name,
                                confidence_score=confidence,
                                mapping_type="semantic_dynamic"
                            )
                            matches.append(mapping)
                            
                            # Cache successful mappings
                            self._dynamic_mappings_cache[metric_term] = {
                                'mapping': (table_name, column_name),
                                'timestamp': time.time()
                            }
                            
                except Exception as e:
                    logger.warning(f"Error processing table {table_name} for semantic matching: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in semantic matching for {metric_term}: {e}")
        
        return matches
    
    def _calculate_semantic_confidence(self, metric_term: str, table_name: str, column_name: str) -> float:
        """Calculate confidence score for semantic matching."""
        confidence = 0.0
        metric_lower = metric_term.lower()
        table_lower = table_name.lower()
        column_lower = column_name.lower()
        
        # Direct matches get highest confidence
        if metric_lower in column_lower or column_lower in metric_lower:
            confidence = 0.9
        elif metric_lower in table_lower or table_lower in metric_lower:
            confidence = 0.7
        else:
            # Keyword-based matching
            keyword_matches = {
                'cash': ['cash', 'flow'],
                'money': ['cash', 'revenue', 'income'],
                'earnings': ['income', 'profit', 'earnings'],
                'turnover': ['revenue', 'sales'],
                'expenditure': ['expense', 'cost', 'spending'],
                'spending': ['expense', 'cost']
            }
            
            for keyword, related_terms in keyword_matches.items():
                if keyword in metric_lower:
                    for term in related_terms:
                        if term in column_lower or term in table_lower:
                            confidence = max(confidence, 0.6)
                            break
        
        return confidence
    
    async def get_column_mappings(self, business_term: str) -> List[SchemaMapping]:
        """
        Get column mappings for a business term.
        
        Args:
            business_term: Business terminology to map
            
        Returns:
            List of column mappings with confidence scores
        """
        return await self.find_tables_for_metric(business_term)
    
    async def generate_query_context(self, intent: Dict[str, Any]) -> QueryContext:
        """
        Generate enhanced query context with discovered schema.
        
        Args:
            intent: Query intent from NLP agent
            
        Returns:
            QueryContext with table/column mappings and optimization hints
        """
        metric_type = intent.get('metric_type', '')
        
        # Find table mappings
        table_mappings = await self.find_tables_for_metric(metric_type)
        
        # Find column mappings
        column_mappings = []
        for field in ['filters', 'comparison_periods']:
            if field in intent and intent[field]:
                field_mappings = await self.get_column_mappings(str(intent[field]))
                column_mappings.extend(field_mappings)
        
        # Generate optimization hints
        optimization_hints = self._generate_optimization_hints(intent, table_mappings)
        
        # Suggest joins if needed
        suggested_joins = self._suggest_joins(intent, table_mappings)
        
        return QueryContext(
            intent=intent,
            table_mappings=table_mappings,
            column_mappings=column_mappings,
            suggested_joins=suggested_joins,
            optimization_hints=optimization_hints
        )
    
    def _generate_optimization_hints(
        self, 
        intent: Dict[str, Any], 
        table_mappings: List[SchemaMapping]
    ) -> List[str]:
        """Generate query optimization hints."""
        hints = []
        
        # Time-based hints
        time_period = intent.get('time_period', '').lower()
        if 'year' in time_period or 'annual' in time_period:
            hints.append("Consider using yearly aggregation for better performance")
        
        # Table-specific hints
        for mapping in table_mappings:
            if mapping.table_name == 'financial_overview':
                hints.append("Use period_date index for time-based filtering")
            elif mapping.table_name == 'cash_flow':
                hints.append("Consider caching for frequent cash flow queries")
        
        return hints
    
    def _suggest_joins(
        self, 
        intent: Dict[str, Any], 
        table_mappings: List[SchemaMapping]
    ) -> List[str]:
        """Suggest table joins based on intent and mappings."""
        joins = []
        
        # If multiple tables are involved, suggest joins
        table_names = {mapping.table_name for mapping in table_mappings}
        
        if len(table_names) > 1:
            if 'financial_overview' in table_names and 'cash_flow' in table_names:
                joins.append("JOIN cash_flow c ON f.period_date = c.period_date")
        
        return joins
    
    async def suggest_alternatives(self, metric_type: str) -> List[str]:
        """
        Suggest alternative metrics when the requested one is not found.
        
        Args:
            metric_type: The requested metric that wasn't found
            
        Returns:
            List of alternative metric suggestions
        """
        alternatives = []
        
        # Simple suggestion logic based on similarity
        metric_lower = metric_type.lower()
        
        if 'revenue' in metric_lower or 'sales' in metric_lower:
            alternatives.extend(['revenue', 'profit', 'income'])
        elif 'profit' in metric_lower or 'income' in metric_lower:
            alternatives.extend(['revenue', 'net_profit', 'gross_profit'])
        elif 'cash' in metric_lower:
            alternatives.extend(['cash_flow', 'operating_cash_flow', 'net_cash_flow'])
        elif 'expense' in metric_lower or 'cost' in metric_lower:
            alternatives.extend(['expenses', 'operating_expenses', 'total_expenses'])
        else:
            # Default suggestions
            alternatives.extend(['revenue', 'profit', 'cash_flow', 'expenses'])
        
        return alternatives[:3]  # Return top 3 suggestions
    
    async def invalidate_schema_cache(self, scope: str = "all") -> None:
        """
        Invalidate schema cache to force fresh discovery.
        
        Args:
            scope: Scope of invalidation ('all', 'tables', 'mappings')
        """
        if self.cache:
            if scope == "all":
                await self.cache.clear_all()
            else:
                await self.cache.invalidate_by_tags([f"scope:{scope}"])
        
        logger.info(f"Schema cache invalidated: {scope}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the schema manager."""
        return {
            **self.metrics,
            'cache_hit_ratio': (
                self.metrics['cache_hits'] / 
                (self.metrics['cache_hits'] + self.metrics['cache_misses'])
                if self.metrics['cache_hits'] + self.metrics['cache_misses'] > 0 
                else 0
            )
        }


# Global instance for easy access
_dynamic_schema_manager: Optional[DynamicSchemaManager] = None


async def get_dynamic_schema_manager() -> DynamicSchemaManager:
    """Get or create global dynamic schema manager instance."""
    global _dynamic_schema_manager
    
    if _dynamic_schema_manager is None:
        _dynamic_schema_manager = DynamicSchemaManager()
    
    return _dynamic_schema_manager


async def close_dynamic_schema_manager() -> None:
    """Close global dynamic schema manager."""
    global _dynamic_schema_manager
    _dynamic_schema_manager = None
