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
        """Initialize basic business term to table/column mappings."""
        # Basic financial metrics mappings
        self.business_mappings = {
            'revenue': ('financial_overview', 'revenue'),
            'sales': ('financial_overview', 'revenue'),
            'income': ('financial_overview', 'revenue'),
            'profit': ('financial_overview', 'net_income'),
            'net_profit': ('financial_overview', 'net_income'),
            'expenses': ('financial_overview', 'total_expenses'),
            'costs': ('financial_overview', 'total_expenses'),
            'cash_flow': ('cash_flow', 'net_cash_flow'),
            'operating_cash_flow': ('cash_flow', 'operating_cash_flow'),
            'investing_cash_flow': ('cash_flow', 'investing_cash_flow'),
            'financing_cash_flow': ('cash_flow', 'financing_cash_flow'),
            'budget': ('budget_tracking', 'budgeted_amount'),
            'budget_variance': ('budget_tracking', 'variance_amount'),
            'investment': ('investments', 'current_value'),
            'roi': ('investments', 'roi_percentage'),
            'return_on_investment': ('investments', 'roi_percentage')
        }
    
    async def discover_schema(self, force_refresh: bool = False) -> SchemaInfo:
        """
        Discover complete database schema with semantic analysis.
        
        Args:
            force_refresh: If True, bypass cache and force fresh discovery
            
        Returns:
            SchemaInfo containing discovered tables, columns, and metadata
        """
        try:
            cache_key = "complete_schema"
            
            # Check cache first unless forced refresh
            if not force_refresh and self.cache:
                cached_schema = await self.cache.get_schema(cache_key)
                if cached_schema:
                    self.metrics['cache_hits'] += 1
                    logger.info("Schema discovery cache hit")
                    return cached_schema
            
            self.metrics['cache_misses'] += 1
            logger.info("Performing fresh schema discovery")
            
            # Discover schema using MCP
            schema_info = await self._perform_schema_discovery()
            
            # Cache the result
            if self.cache:
                await self.cache.set_schema(
                    cache_key, 
                    schema_info, 
                    ttl=self.config['cache_ttl']
                )
            
            self.metrics['schema_discoveries'] += 1
            self.metrics['last_schema_update'] = datetime.now()
            
            logger.info(f"Schema discovery completed: {len(schema_info.tables)} tables found")
            return schema_info
            
        except Exception as e:
            logger.error(f"Schema discovery failed: {e}")
            # Return minimal fallback schema
            return self._get_fallback_schema()
    
    async def _perform_schema_discovery(self) -> SchemaInfo:
        """Perform actual schema discovery via MCP."""
        try:
            # Use the schema manager for discovery
            databases = await self.schema_manager.discover_databases()
            
            schema_info = SchemaInfo(databases=[], tables=[], version="dynamic")
            
            for db in databases:
                tables = await self.schema_manager.get_tables(db.name)
                for table in tables:
                    # Get detailed table schema
                    table_schema = await self.schema_manager.get_table_schema(db.name, table.name)
                    schema_info.tables.append(table_schema)
            
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
        
        # Check direct mappings first
        if metric_lower in self.business_mappings:
            table_name, column_name = self.business_mappings[metric_lower]
            mapping = SchemaMapping(
                business_term=metric_type,
                schema_path=f"default.{table_name}.{column_name}",
                table_name=table_name,
                column_name=column_name,
                confidence_score=0.95,
                mapping_type="direct"
            )
            mappings.append(mapping)
        
        # Look for semantic matches
        semantic_matches = await self._find_semantic_matches(metric_lower)
        mappings.extend(semantic_matches)
        
        # Sort by confidence score
        mappings.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return mappings[:self.config['max_alternatives']]
    
    async def _find_semantic_matches(self, metric_term: str) -> List[SchemaMapping]:
        """Find semantic matches for a business term."""
        matches = []
        
        # Simple keyword-based semantic matching
        semantic_keywords = {
            'cash': [('cash_flow', 'net_cash_flow', 0.8)],
            'money': [('cash_flow', 'net_cash_flow', 0.7), ('financial_overview', 'revenue', 0.6)],
            'earnings': [('financial_overview', 'net_income', 0.8)],
            'turnover': [('financial_overview', 'revenue', 0.8)],
            'expenditure': [('financial_overview', 'total_expenses', 0.8)],
            'spending': [('financial_overview', 'total_expenses', 0.7)]
        }
        
        for keyword, table_mappings in semantic_keywords.items():
            if keyword in metric_term:
                for table_name, column_name, confidence in table_mappings:
                    mapping = SchemaMapping(
                        business_term=metric_term,
                        schema_path=f"default.{table_name}.{column_name}",
                        table_name=table_name,
                        column_name=column_name,
                        confidence_score=confidence,
                        mapping_type="semantic"
                    )
                    matches.append(mapping)
        
        return matches
    
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
