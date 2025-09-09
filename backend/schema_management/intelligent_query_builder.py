"""
Intelligent Query Builder - Dynamic SQL generation using discovered schema.

This module replaces static SQL templates with dynamic query generation
based on real-time schema discovery and semantic mappings.
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

from .dynamic_schema_manager import DynamicSchemaManager, QueryContext, SchemaMapping

logger = logging.getLogger(__name__)


class QueryResult:
    """Result of intelligent query building."""
    
    def __init__(
        self,
        sql: str,
        parameters: Dict[str, Any] = None,
        estimated_rows: int = None,
        optimization_hints: List[str] = None,
        processing_time_ms: int = None,
        confidence_score: float = None
    ):
        self.sql = sql
        self.parameters = parameters or {}
        self.estimated_rows = estimated_rows
        self.optimization_hints = optimization_hints or []
        self.processing_time_ms = processing_time_ms
        self.confidence_score = confidence_score


class IntelligentQueryBuilder:
    """
    Builds SQL queries dynamically using discovered schema and semantic mappings.
    
    Features:
    - Dynamic SQL generation based on discovered schema
    - Query optimization using indexes and constraints
    - Alternative query suggestions for failed queries
    - Query validation against real-time schema
    - Support for complex joins and aggregations
    """
    
    def __init__(
        self,
        schema_manager: Optional[DynamicSchemaManager] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.schema_manager = schema_manager
        self.config = config or self._get_default_config()
        
        # SQL generation patterns
        self._init_sql_patterns()
        
        # Performance metrics
        self.metrics = {
            'queries_built': 0,
            'successful_generations': 0,
            'fallback_used': 0,
            'avg_build_time_ms': 0.0
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for query builder."""
        return {
            'default_limit': 1000,
            'max_joins': 5,
            'optimization_level': 'moderate',
            'enable_query_hints': True,
            'fallback_to_static': True
        }
    
    def _init_sql_patterns(self) -> None:
        """Initialize common SQL patterns and templates."""
        self.aggregation_patterns = {
            'daily': "DATE_FORMAT(period_date, '%Y-%m-%d')",
            'weekly': "DATE_FORMAT(period_date, '%Y-W%u')",
            'monthly': "DATE_FORMAT(period_date, '%Y-%m')",
            'quarterly': "CONCAT(YEAR(period_date), '-Q', QUARTER(period_date))",
            'yearly': "YEAR(period_date)"
        }
        
        self.time_filters = {
            'this_month': "period_date >= DATE_FORMAT(CURDATE(), '%Y-%m-01')",
            'this_quarter': "period_date >= DATE_FORMAT(CURDATE(), '%Y-%m-01') - INTERVAL (MONTH(CURDATE()) % 3) MONTH",
            'this_year': "period_date >= DATE_FORMAT(CURDATE(), '%Y-01-01')",
            'last_12_months': "period_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)",
            'last_6_months': "period_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)"
        }
    
    async def build_query(
        self,
        intent: Dict[str, Any],
        context: Optional[QueryContext] = None
    ) -> QueryResult:
        """
        Build SQL query from intent using dynamic schema.
        
        Args:
            intent: Query intent from NLP agent
            context: Optional pre-computed query context
            
        Returns:
            QueryResult with generated SQL and metadata
        """
        start_time = datetime.now()
        
        try:
            self.metrics['queries_built'] += 1
            
            # Get or generate query context
            if context is None and self.schema_manager:
                context = await self.schema_manager.generate_query_context(intent)
            
            # Check if we have valid table mappings
            if not context or not context.table_mappings:
                logger.warning(f"No table mappings found for metric: {intent.get('metric_type')}")
                return await self._build_fallback_query(intent)
            
            # Select primary table for the query
            primary_mapping = self._select_primary_table(context.table_mappings, intent)
            
            # Build query components
            select_clause = self._build_select_clause(intent, primary_mapping)
            from_clause = self._build_from_clause(primary_mapping)
            where_clause = self._build_where_clause(intent, primary_mapping)
            group_by_clause = self._build_group_by_clause(intent)
            order_by_clause = self._build_order_by_clause(intent)
            limit_clause = self._build_limit_clause(intent)
            
            # Combine into final query
            sql_parts = [
                select_clause,
                from_clause,
                where_clause,
                group_by_clause,
                order_by_clause,
                limit_clause
            ]
            
            sql = ' '.join(part for part in sql_parts if part).strip()
            
            # Generate parameters
            parameters = self._extract_parameters(intent)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Build result
            result = QueryResult(
                sql=sql,
                parameters=parameters,
                optimization_hints=context.optimization_hints if context else [],
                processing_time_ms=int(processing_time),
                confidence_score=primary_mapping.confidence_score
            )
            
            self.metrics['successful_generations'] += 1
            self._update_metrics(processing_time)
            
            logger.info(f"Query built successfully: {intent.get('metric_type')} -> {primary_mapping.table_name}")
            return result
            
        except Exception as e:
            logger.error(f"Query building failed: {e}")
            return await self._build_fallback_query(intent)
    
    def _select_primary_table(
        self, 
        table_mappings: List[SchemaMapping], 
        intent: Dict[str, Any]
    ) -> SchemaMapping:
        """Select the best table mapping for the query."""
        # Sort by confidence score and return the highest
        sorted_mappings = sorted(table_mappings, key=lambda x: x.confidence_score, reverse=True)
        return sorted_mappings[0]
    
    def _build_select_clause(
        self, 
        intent: Dict[str, Any], 
        primary_mapping: SchemaMapping
    ) -> str:
        """Build SELECT clause based on intent and mapping."""
        metric_type = intent.get('metric_type', '')
        aggregation_level = intent.get('aggregation_level', 'monthly')
        
        # Build time grouping
        time_expr = self.aggregation_patterns.get(aggregation_level, self.aggregation_patterns['monthly'])
        
        # Build metric selection
        metric_column = primary_mapping.column_name
        
        # Handle aggregation
        if 'cash_flow' in metric_type:
            # Special handling for cash flow metrics
            select_parts = [
                f"{time_expr} as period",
                f"SUM(operating_cash_flow) as operating_cash_flow",
                f"SUM(investing_cash_flow) as investing_cash_flow", 
                f"SUM(financing_cash_flow) as financing_cash_flow",
                f"SUM(net_cash_flow) as net_cash_flow"
            ]
        else:
            # Standard metric aggregation
            select_parts = [
                f"{time_expr} as period",
                f"SUM({metric_column}) as {metric_type}"
            ]
        
        return f"SELECT {', '.join(select_parts)}"
    
    def _build_from_clause(self, primary_mapping: SchemaMapping) -> str:
        """Build FROM clause."""
        return f"FROM {primary_mapping.table_name}"
    
    def _build_where_clause(
        self, 
        intent: Dict[str, Any], 
        primary_mapping: SchemaMapping
    ) -> str:
        """Build WHERE clause with time and filter conditions."""
        conditions = []
        
        # Add time period filter
        time_period = intent.get('time_period', 'this_year').lower()
        if time_period in self.time_filters:
            conditions.append(self.time_filters[time_period])
        else:
            # Default to current year
            conditions.append("period_date >= DATE_FORMAT(CURDATE(), '%Y-01-01')")
        
        # Add custom filters
        filters = intent.get('filters', {})
        for key, value in filters.items():
            if isinstance(value, str):
                conditions.append(f"{key} = '{value}'")
            else:
                conditions.append(f"{key} = {value}")
        
        return f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    def _build_group_by_clause(self, intent: Dict[str, Any]) -> str:
        """Build GROUP BY clause."""
        aggregation_level = intent.get('aggregation_level', 'monthly')
        time_expr = self.aggregation_patterns.get(aggregation_level, self.aggregation_patterns['monthly'])
        return f"GROUP BY {time_expr}"
    
    def _build_order_by_clause(self, intent: Dict[str, Any]) -> str:
        """Build ORDER BY clause."""
        return "ORDER BY period"
    
    def _build_limit_clause(self, intent: Dict[str, Any]) -> str:
        """Build LIMIT clause."""
        limit = intent.get('limit', self.config['default_limit'])
        return f"LIMIT {limit}"
    
    def _extract_parameters(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Extract query parameters from intent."""
        # For this basic implementation, we're using direct SQL generation
        # In a more advanced version, we'd use parameterized queries
        return {}
    
    async def _build_fallback_query(self, intent: Dict[str, Any]) -> QueryResult:
        """Build fallback query when dynamic generation fails."""
        self.metrics['fallback_used'] += 1
        
        metric_type = intent.get('metric_type', 'revenue')
        
        # Static fallback queries
        fallback_queries = {
            'revenue': """
                SELECT 
                    DATE_FORMAT(period_date, '%Y-%m') as period,
                    SUM(revenue) as revenue
                FROM financial_overview 
                WHERE period_date >= DATE_FORMAT(CURDATE(), '%Y-01-01')
                GROUP BY DATE_FORMAT(period_date, '%Y-%m')
                ORDER BY period
                LIMIT 1000
            """,
            'cash_flow': """
                SELECT 
                    DATE_FORMAT(period_date, '%Y-%m') as period,
                    SUM(operating_cash_flow) as operating_cash_flow,
                    SUM(investing_cash_flow) as investing_cash_flow,
                    SUM(financing_cash_flow) as financing_cash_flow,
                    SUM(net_cash_flow) as net_cash_flow
                FROM cash_flow 
                WHERE period_date >= DATE_FORMAT(CURDATE(), '%Y-01-01')
                GROUP BY DATE_FORMAT(period_date, '%Y-%m')
                ORDER BY period
                LIMIT 1000
            """,
            'profit': """
                SELECT 
                    DATE_FORMAT(period_date, '%Y-%m') as period,
                    SUM(net_income) as profit
                FROM financial_overview 
                WHERE period_date >= DATE_FORMAT(CURDATE(), '%Y-01-01')
                GROUP BY DATE_FORMAT(period_date, '%Y-%m')
                ORDER BY period
                LIMIT 1000
            """
        }
        
        # Get fallback query or use default
        sql = fallback_queries.get(metric_type, fallback_queries['revenue'])
        
        # Clean up the SQL
        sql = re.sub(r'\s+', ' ', sql.strip())
        
        logger.warning(f"Using fallback query for metric: {metric_type}")
        
        return QueryResult(
            sql=sql,
            parameters={},
            optimization_hints=['Using fallback static query'],
            confidence_score=0.5
        )
    
    def _update_metrics(self, processing_time_ms: float) -> None:
        """Update performance metrics."""
        # Update average build time
        current_avg = self.metrics['avg_build_time_ms']
        total_builds = self.metrics['queries_built']
        
        self.metrics['avg_build_time_ms'] = (
            (current_avg * (total_builds - 1) + processing_time_ms) / total_builds
        )
    
    async def suggest_alternatives(self, failed_query: str, error: str) -> List[str]:
        """
        Suggest alternative queries when the original fails.
        
        Args:
            failed_query: The SQL query that failed
            error: Error message from the database
            
        Returns:
            List of alternative query suggestions
        """
        alternatives = []
        
        # Simple error-based suggestions
        if "table" in error.lower() and "doesn't exist" in error.lower():
            alternatives.append("Check if the table name is correct or if schema has changed")
            alternatives.append("Try using a different metric type")
        
        if "column" in error.lower() and "unknown" in error.lower():
            alternatives.append("Verify column names match current schema")
            alternatives.append("Consider using SELECT * to see available columns")
        
        return alternatives
    
    async def validate_query_against_schema(self, query: str) -> bool:
        """
        Validate query against discovered schema.
        
        Args:
            query: SQL query to validate
            
        Returns:
            True if query appears valid, False otherwise
        """
        # Basic validation checks
        query_upper = query.upper()
        
        # Check for required SQL keywords
        if not any(keyword in query_upper for keyword in ['SELECT', 'FROM']):
            return False
        
        # Check for potential SQL injection patterns
        dangerous_patterns = ['DROP', 'DELETE', 'UPDATE', 'INSERT', '--', ';']
        if any(pattern in query_upper for pattern in dangerous_patterns):
            return False
        
        return True
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get query builder performance metrics."""
        return {
            **self.metrics,
            'success_rate': (
                self.metrics['successful_generations'] / self.metrics['queries_built']
                if self.metrics['queries_built'] > 0 else 0
            ),
            'fallback_rate': (
                self.metrics['fallback_used'] / self.metrics['queries_built']
                if self.metrics['queries_built'] > 0 else 0
            )
        }


# Global instance
_intelligent_query_builder: Optional[IntelligentQueryBuilder] = None


async def get_intelligent_query_builder(
    schema_manager: Optional[DynamicSchemaManager] = None
) -> IntelligentQueryBuilder:
    """Get or create global intelligent query builder instance."""
    global _intelligent_query_builder
    
    if _intelligent_query_builder is None:
        _intelligent_query_builder = IntelligentQueryBuilder(schema_manager)
    
    return _intelligent_query_builder
