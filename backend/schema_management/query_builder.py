"""
Intelligent Query Builder for dynamic SQL generation.

This module provides intelligent SQL query generation based on discovered schema,
semantic mappings, and query optimization techniques.
"""

import re
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

from .models import (
    TableSchema, ColumnInfo, QueryIntent, QueryContext, QueryResult,
    SemanticMapping, SchemaElement, ValidationResult, ValidationError, ValidationSeverity
)
from .semantic_mapper import SemanticSchemaMapper
from .manager import MCPSchemaManager

logger = logging.getLogger(__name__)


class AggregationType(str, Enum):
    """Supported aggregation types."""
    SUM = "sum"
    COUNT = "count"
    AVG = "avg"
    MAX = "max"
    MIN = "min"
    COUNT_DISTINCT = "count_distinct"


class JoinType(str, Enum):
    """Supported SQL join types."""
    INNER = "INNER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    FULL = "FULL"


@dataclass
class TableMapping:
    """Mapping between business concept and database table."""
    business_concept: str
    table_schema: TableSchema
    confidence_score: float
    semantic_mappings: List[SemanticMapping]
    join_priority: int  # Lower number = higher priority for joins


@dataclass
class ColumnMapping:
    """Mapping between business attribute and database column."""
    business_attribute: str
    column_info: ColumnInfo
    table_path: str  # database.table
    confidence_score: float
    semantic_mapping: SemanticMapping
    is_metric: bool  # True if this column represents a measurable metric
    is_dimension: bool  # True if this column is used for grouping/filtering


@dataclass
class JoinPath:
    """Represents a join path between tables."""
    from_table: str
    to_table: str
    join_type: JoinType
    join_condition: str
    cost_estimate: float
    foreign_key_based: bool


@dataclass
class QueryPlan:
    """Execution plan for a generated query."""
    primary_table: TableMapping
    required_joins: List[JoinPath]
    column_mappings: List[ColumnMapping]
    where_conditions: List[str]
    group_by_columns: List[str]
    order_by_clause: Optional[str]
    estimated_cost: float
    optimization_notes: List[str]


class QueryBuildError(Exception):
    """Exception raised when query building fails."""
    pass


class IntelligentQueryBuilder:
    """
    Builds SQL queries dynamically using discovered schema and semantic mappings.
    
    Features:
    - Dynamic SQL generation based on discovered schema
    - Query optimization using indexes and constraints
    - Alternative query suggestions for failed queries
    - Query validation against real-time schema
    - Support for complex joins and aggregations
    - Performance prediction and optimization recommendations
    """
    
    def __init__(
        self,
        schema_manager: MCPSchemaManager,
        semantic_mapper: SemanticSchemaMapper,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize intelligent query builder.
        
        Args:
            schema_manager: Schema manager for database operations
            semantic_mapper: Semantic mapper for business term mapping
            config: Optional configuration parameters
        """
        self.schema_manager = schema_manager
        self.semantic_mapper = semantic_mapper
        self.config = config or self._get_default_config()
        
        # Query building cache
        self.table_mappings_cache: Dict[str, List[TableMapping]] = {}
        self.join_paths_cache: Dict[Tuple[str, str], List[JoinPath]] = {}
        
        # Query templates and patterns
        self.common_patterns = self._initialize_common_patterns()
        
        logger.info("Initialized IntelligentQueryBuilder")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for query builder."""
        return {
            'max_joins': 5,
            'join_cost_threshold': 1000000,  # Estimated row threshold for joins
            'confidence_threshold': 0.6,
            'enable_query_optimization': True,
            'enable_index_hints': True,
            'max_where_conditions': 10,
            'default_limit': 1000,
            'query_timeout_seconds': 30,
            'enable_subqueries': True,
            'prefer_foreign_key_joins': True
        }
    
    def _initialize_common_patterns(self) -> Dict[str, Any]:
        """Initialize common SQL patterns and templates."""
        return {
            'time_filters': {
                'last_30_days': "DATE({column}) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)",
                'this_month': "MONTH({column}) = MONTH(CURDATE()) AND YEAR({column}) = YEAR(CURDATE())",
                'this_year': "YEAR({column}) = YEAR(CURDATE())",
                'last_quarter': """
                    QUARTER({column}) = QUARTER(DATE_SUB(CURDATE(), INTERVAL 3 MONTH)) 
                    AND YEAR({column}) = YEAR(DATE_SUB(CURDATE(), INTERVAL 3 MONTH))
                """,
                'ytd': "{column} >= DATE(CONCAT(YEAR(CURDATE()), '-01-01'))"
            },
            'aggregation_templates': {
                'sum': "SUM({column})",
                'count': "COUNT({column})",
                'avg': "AVG({column})",
                'max': "MAX({column})",
                'min': "MIN({column})",
                'count_distinct': "COUNT(DISTINCT {column})"
            },
            'common_measures': {
                'revenue': ['amount', 'value', 'price', 'total'],
                'quantity': ['qty', 'count', 'number', 'volume'],
                'profit': ['profit', 'margin', 'earnings', 'gain'],
                'cost': ['cost', 'expense', 'spending']
            }
        }
    
    async def build_query(
        self,
        intent: QueryIntent,
        context: QueryContext,
        schema_context: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """
        Build SQL query from intent using dynamic schema discovery.
        
        Args:
            intent: Parsed query intent
            context: Query context information
            schema_context: Optional schema context for optimization
            
        Returns:
            Query result with SQL and metadata
        """
        start_time = time.time()
        
        try:
            # Step 1: Find relevant tables for the metrics
            table_mappings = await self._find_tables_for_metrics(intent, context)
            
            if not table_mappings:
                # Try to suggest alternatives
                suggestions = await self._suggest_alternative_metrics(intent.metric_type)
                raise QueryBuildError(
                    f"No tables found for metric: {intent.metric_type}. "
                    f"Did you mean: {', '.join(suggestions)}?"
                )
            
            # Step 2: Select primary table and build query plan
            query_plan = await self._build_query_plan(intent, table_mappings, context)
            
            # Step 3: Generate SQL components
            sql_components = await self._generate_sql_components(query_plan, intent)
            
            # Step 4: Combine into final query
            final_sql = self._assemble_query(sql_components)
            
            # Step 5: Optimize query
            if self.config['enable_query_optimization']:
                final_sql = await self._optimize_query(final_sql, query_plan)
            
            # Step 6: Validate query
            validation_result = await self._validate_query(final_sql, query_plan)
            
            if not validation_result.is_valid:
                # Try to fix common issues
                final_sql = await self._attempt_query_fixes(final_sql, validation_result)
            
            # Step 7: Generate alternatives
            alternatives = await self._generate_alternative_queries(intent, table_mappings, context)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return QueryResult(
                sql=final_sql,
                parameters={},  # Parameters would be added for prepared statements
                estimated_rows=query_plan.estimated_cost,
                optimization_hints=query_plan.optimization_notes,
                alternative_queries=alternatives,
                confidence_score=self._calculate_query_confidence(query_plan),
                processing_time_ms=processing_time,
                used_mappings=self._extract_used_mappings(query_plan)
            )
            
        except Exception as e:
            logger.error(f"Query building failed: {e}")
            
            # Return error result with suggestions
            processing_time = int((time.time() - start_time) * 1000)
            return QueryResult(
                sql="",
                parameters={},
                estimated_rows=0,
                optimization_hints=[],
                alternative_queries=[],
                confidence_score=0.0,
                processing_time_ms=processing_time,
                used_mappings=[]
            )
    
    async def _find_tables_for_metrics(
        self,
        intent: QueryIntent,
        context: QueryContext
    ) -> List[TableMapping]:
        """
        Find database tables that contain the requested metrics.
        
        Args:
            intent: Query intent
            context: Query context
            
        Returns:
            List of table mappings for the metrics
        """
        cache_key = f"{intent.metric_type}_{context.business_context or ''}"
        
        if cache_key in self.table_mappings_cache:
            logger.debug(f"Using cached table mappings for {intent.metric_type}")
            return self.table_mappings_cache[cache_key]
        
        # Use semantic mapper to find relevant tables
        semantic_mappings = await self.semantic_mapper.map_business_term(
            intent.metric_type,
            context=context.business_context,
            schema_filter={'element_type': 'table'}
        )
        
        table_mappings = []
        
        for mapping in semantic_mappings:
            # Get table schema for each mapping
            schema_path = mapping.schema_element_path
            database, table = schema_path.split('.')[:2]
            
            table_schema = await self.schema_manager.get_table_schema(database, table)
            if table_schema:
                # Find semantic mappings for columns in this table
                column_mappings = await self._find_column_mappings_for_table(
                    intent, table_schema, context
                )
                
                table_mapping = TableMapping(
                    business_concept=intent.metric_type,
                    table_schema=table_schema,
                    confidence_score=mapping.confidence_score,
                    semantic_mappings=[mapping],
                    join_priority=self._calculate_join_priority(table_schema, column_mappings)
                )
                table_mappings.append(table_mapping)
        
        # Sort by confidence and join priority
        table_mappings.sort(
            key=lambda t: (t.confidence_score, -t.join_priority),
            reverse=True
        )
        
        # Cache the results
        self.table_mappings_cache[cache_key] = table_mappings
        
        logger.info(f"Found {len(table_mappings)} table mappings for {intent.metric_type}")
        return table_mappings
    
    async def _find_column_mappings_for_table(
        self,
        intent: QueryIntent,
        table_schema: TableSchema,
        context: QueryContext
    ) -> List[ColumnMapping]:
        """
        Find column mappings within a specific table.
        
        Args:
            intent: Query intent
            table_schema: Table schema to search
            context: Query context
            
        Returns:
            List of column mappings
        """
        column_mappings = []
        
        # Map metric to columns
        metric_mappings = await self.semantic_mapper.map_business_term(
            intent.metric_type,
            context=context.business_context,
            schema_filter={
                'element_type': 'column',
                'database': table_schema.database,
                'table': table_schema.table
            }
        )
        
        for mapping in metric_mappings:
            # Find the column in the table schema
            column_name = mapping.schema_element_path.split('.')[-1]
            column_info = None
            
            for col in table_schema.columns:
                if col.name == column_name:
                    column_info = col
                    break
            
            if column_info:
                column_mapping = ColumnMapping(
                    business_attribute=intent.metric_type,
                    column_info=column_info,
                    table_path=f"{table_schema.database}.{table_schema.table}",
                    confidence_score=mapping.confidence_score,
                    semantic_mapping=mapping,
                    is_metric=self._is_numeric_column(column_info),
                    is_dimension=self._is_dimension_column(column_info)
                )
                column_mappings.append(column_mapping)
        
        # Also map filters and group-by attributes
        for filter_attr in intent.filters.keys():
            filter_mappings = await self.semantic_mapper.map_business_term(
                filter_attr,
                context=context.business_context,
                schema_filter={
                    'element_type': 'column',
                    'database': table_schema.database,
                    'table': table_schema.table
                }
            )
            
            for mapping in filter_mappings:
                column_name = mapping.schema_element_path.split('.')[-1]
                column_info = None
                
                for col in table_schema.columns:
                    if col.name == column_name:
                        column_info = col
                        break
                
                if column_info:
                    column_mapping = ColumnMapping(
                        business_attribute=filter_attr,
                        column_info=column_info,
                        table_path=f"{table_schema.database}.{table_schema.table}",
                        confidence_score=mapping.confidence_score,
                        semantic_mapping=mapping,
                        is_metric=False,
                        is_dimension=True
                    )
                    column_mappings.append(column_mapping)
        
        return column_mappings
    
    def _is_numeric_column(self, column: ColumnInfo) -> bool:
        """Check if column contains numeric data suitable for metrics."""
        numeric_types = ['int', 'integer', 'bigint', 'decimal', 'numeric', 'float', 'double', 'real']
        return any(ntype in column.data_type.lower() for ntype in numeric_types)
    
    def _is_dimension_column(self, column: ColumnInfo) -> bool:
        """Check if column is suitable for dimensions (grouping/filtering)."""
        # Dimension columns are typically non-numeric or categorical
        dimension_indicators = ['varchar', 'char', 'text', 'enum', 'date', 'datetime', 'timestamp']
        return any(dtype in column.data_type.lower() for dtype in dimension_indicators) or column.is_foreign_key
    
    def _calculate_join_priority(
        self,
        table_schema: TableSchema,
        column_mappings: List[ColumnMapping]
    ) -> int:
        """
        Calculate join priority for a table based on its characteristics.
        
        Lower numbers indicate higher priority.
        """
        priority = 100  # Base priority
        
        # Boost priority for tables with many relevant columns
        priority -= len(column_mappings) * 10
        
        # Boost priority for smaller tables
        if table_schema.table_info:
            if table_schema.table_info.rows < 10000:
                priority -= 20
            elif table_schema.table_info.rows < 100000:
                priority -= 10
        
        # Boost priority for tables with primary keys
        if table_schema.primary_keys:
            priority -= 15
        
        # Boost priority for tables with indexes
        priority -= len(table_schema.indexes) * 5
        
        # Boost priority for fact tables (tables with many foreign keys)
        foreign_key_count = len(table_schema.foreign_keys)
        if foreign_key_count > 2:
            priority -= 25  # Likely a fact table
        
        return max(0, priority)
    
    async def _build_query_plan(
        self,
        intent: QueryIntent,
        table_mappings: List[TableMapping],
        context: QueryContext
    ) -> QueryPlan:
        """
        Build an execution plan for the query.
        
        Args:
            intent: Query intent
            table_mappings: Available table mappings
            context: Query context
            
        Returns:
            Query execution plan
        """
        # Select primary table (highest confidence, best column mappings)
        primary_table = await self._select_primary_table(intent, table_mappings, context)
        
        # Find required column mappings
        column_mappings = await self._find_column_mappings_for_table(
            intent, primary_table.table_schema, context
        )
        
        # Determine if joins are needed
        required_joins = []
        if len(table_mappings) > 1 and self.config.get('max_joins', 5) > 0:
            required_joins = await self._plan_joins(primary_table, table_mappings, column_mappings)
        
        # Build WHERE conditions
        where_conditions = self._build_where_conditions(intent, column_mappings)
        
        # Build GROUP BY clause
        group_by_columns = self._build_group_by_columns(intent, column_mappings)
        
        # Build ORDER BY clause
        order_by_clause = self._build_order_by_clause(intent, column_mappings)
        
        # Estimate query cost
        estimated_cost = self._estimate_query_cost(
            primary_table, required_joins, where_conditions
        )
        
        # Generate optimization notes
        optimization_notes = self._generate_optimization_notes(
            primary_table, required_joins, column_mappings
        )
        
        return QueryPlan(
            primary_table=primary_table,
            required_joins=required_joins,
            column_mappings=column_mappings,
            where_conditions=where_conditions,
            group_by_columns=group_by_columns,
            order_by_clause=order_by_clause,
            estimated_cost=estimated_cost,
            optimization_notes=optimization_notes
        )
    
    async def _select_primary_table(
        self,
        intent: QueryIntent,
        table_mappings: List[TableMapping],
        context: QueryContext
    ) -> TableMapping:
        """
        Select the primary table for the query.
        
        Args:
            intent: Query intent
            table_mappings: Available table mappings
            context: Query context
            
        Returns:
            Selected primary table mapping
        """
        if not table_mappings:
            raise QueryBuildError("No table mappings available for primary table selection")
        
        # Score each table based on multiple factors
        scored_tables = []
        
        for table_mapping in table_mappings:
            score = 0.0
            
            # Base confidence score
            score += table_mapping.confidence_score * 40
            
            # Column coverage score
            column_mappings = await self._find_column_mappings_for_table(
                intent, table_mapping.table_schema, context
            )
            
            metric_columns = [cm for cm in column_mappings if cm.is_metric]
            dimension_columns = [cm for cm in column_mappings if cm.is_dimension]
            
            # Prefer tables with good metric column coverage
            score += len(metric_columns) * 15
            
            # Prefer tables with good dimension coverage for filters/grouping
            score += len(dimension_columns) * 10
            
            # Prefer smaller tables (better performance)
            if table_mapping.table_schema.table_info:
                rows = table_mapping.table_schema.table_info.rows
                if rows < 10000:
                    score += 20
                elif rows < 100000:
                    score += 10
                elif rows > 1000000:
                    score -= 10
            
            # Prefer tables with good indexing
            score += len(table_mapping.table_schema.indexes) * 3
            
            # Join priority (lower is better, so subtract)
            score -= table_mapping.join_priority * 0.5
            
            scored_tables.append((table_mapping, score))
        
        # Sort by score and return the best
        scored_tables.sort(key=lambda x: x[1], reverse=True)
        
        selected_table = scored_tables[0][0]
        logger.info(f"Selected primary table: {selected_table.table_schema.table} "
                   f"(score: {scored_tables[0][1]:.2f})")
        
        return selected_table
    
    async def _plan_joins(
        self,
        primary_table: TableMapping,
        table_mappings: List[TableMapping],
        column_mappings: List[ColumnMapping]
    ) -> List[JoinPath]:
        """
        Plan the joins needed for the query.
        
        Args:
            primary_table: Primary table for the query
            table_mappings: All available table mappings
            column_mappings: Column mappings from primary table
            
        Returns:
            List of join paths
        """
        joins = []
        primary_table_path = f"{primary_table.table_schema.database}.{primary_table.table_schema.table}"
        
        # Check if we need additional tables for columns not found in primary table
        needed_attributes = set()
        for mapping in column_mappings:
            if mapping.table_path != primary_table_path:
                needed_attributes.add(mapping.business_attribute)
        
        if not needed_attributes:
            return joins  # No joins needed
        
        # Find join paths to tables containing needed attributes
        for table_mapping in table_mappings:
            if table_mapping == primary_table:
                continue
            
            target_table_path = f"{table_mapping.table_schema.database}.{table_mapping.table_schema.table}"
            
            # Check if this table has any needed attributes
            table_has_needed_attr = any(
                cm.table_path == target_table_path and cm.business_attribute in needed_attributes
                for cm in column_mappings
            )
            
            if table_has_needed_attr:
                join_path = await self._find_join_path(
                    primary_table.table_schema,
                    table_mapping.table_schema
                )
                
                if join_path:
                    joins.append(join_path)
                    if len(joins) >= self.config.get('max_joins', 5):
                        break
        
        return joins
    
    async def _find_join_path(
        self,
        from_table: TableSchema,
        to_table: TableSchema
    ) -> Optional[JoinPath]:
        """
        Find a join path between two tables.
        
        Args:
            from_table: Source table schema
            to_table: Target table schema
            
        Returns:
            Join path or None if no path found
        """
        from_path = f"{from_table.database}.{from_table.table}"
        to_path = f"{to_table.database}.{to_table.table}"
        
        cache_key = (from_path, to_path)
        if cache_key in self.join_paths_cache:
            cached_paths = self.join_paths_cache[cache_key]
            return cached_paths[0] if cached_paths else None
        
        # Look for foreign key relationships
        join_condition = None
        join_type = JoinType.INNER
        foreign_key_based = False
        
        # Check if from_table has a foreign key to to_table
        for fk in from_table.foreign_keys:
            if fk.referenced_table == to_table.table:
                join_condition = f"{from_table.table}.{fk.column} = {to_table.table}.{fk.referenced_column}"
                foreign_key_based = True
                break
        
        # Check if to_table has a foreign key to from_table
        if not join_condition:
            for fk in to_table.foreign_keys:
                if fk.referenced_table == from_table.table:
                    join_condition = f"{to_table.table}.{fk.column} = {from_table.table}.{fk.referenced_column}"
                    foreign_key_based = True
                    break
        
        # Look for common column names if no foreign key found
        if not join_condition:
            common_columns = self._find_common_columns(from_table, to_table)
            if common_columns:
                from_col, to_col = common_columns[0]  # Use first common column
                join_condition = f"{from_table.table}.{from_col} = {to_table.table}.{to_col}"
                join_type = JoinType.LEFT  # Use LEFT JOIN for inferred relationships
        
        if join_condition:
            cost_estimate = self._estimate_join_cost(from_table, to_table)
            
            join_path = JoinPath(
                from_table=from_path,
                to_table=to_path,
                join_type=join_type,
                join_condition=join_condition,
                cost_estimate=cost_estimate,
                foreign_key_based=foreign_key_based
            )
            
            # Cache the result
            self.join_paths_cache[cache_key] = [join_path]
            
            return join_path
        
        # Cache negative result
        self.join_paths_cache[cache_key] = []
        return None
    
    def _find_common_columns(
        self,
        table1: TableSchema,
        table2: TableSchema
    ) -> List[Tuple[str, str]]:
        """
        Find common columns between two tables that could be used for joins.
        
        Args:
            table1: First table schema
            table2: Second table schema
            
        Returns:
            List of (column1, column2) tuples for potential join columns
        """
        common_columns = []
        
        # Common patterns for join columns
        join_patterns = ['id', '_id', 'key', '_key']
        
        for col1 in table1.columns:
            for col2 in table2.columns:
                # Exact name match
                if col1.name == col2.name:
                    common_columns.append((col1.name, col2.name))
                    continue
                
                # Pattern matching (e.g., user_id matches id in users table)
                col1_lower = col1.name.lower()
                col2_lower = col2.name.lower()
                
                # Check if one column name contains the other table name
                if (table2.table.lower() in col1_lower and 
                    any(pattern in col1_lower for pattern in join_patterns)):
                    common_columns.append((col1.name, col2.name))
                elif (table1.table.lower() in col2_lower and 
                      any(pattern in col2_lower for pattern in join_patterns)):
                    common_columns.append((col1.name, col2.name))
        
        return common_columns
    
    def _estimate_join_cost(self, table1: TableSchema, table2: TableSchema) -> float:
        """
        Estimate the cost of joining two tables.
        
        Args:
            table1: First table schema
            table2: Second table schema
            
        Returns:
            Estimated join cost (lower is better)
        """
        # Simple cost estimation based on table sizes
        rows1 = table1.table_info.rows if table1.table_info else 1000
        rows2 = table2.table_info.rows if table2.table_info else 1000
        
        # Nested loop join estimate
        base_cost = rows1 * rows2
        
        # Reduce cost if there are indexes on join columns
        index_factor = 1.0
        if table1.indexes or table2.indexes:
            index_factor = 0.1  # Assume indexes significantly improve join performance
        
        return base_cost * index_factor
    
    def _build_where_conditions(
        self,
        intent: QueryIntent,
        column_mappings: List[ColumnMapping]
    ) -> List[str]:
        """
        Build WHERE conditions from query intent.
        
        Args:
            intent: Query intent
            column_mappings: Available column mappings
            
        Returns:
            List of WHERE condition strings
        """
        conditions = []
        
        # Process filters from intent
        for filter_attr, filter_value in intent.filters.items():
            # Find column mapping for this filter
            column_mapping = None
            for cm in column_mappings:
                if cm.business_attribute == filter_attr:
                    column_mapping = cm
                    break
            
            if column_mapping:
                condition = self._build_filter_condition(
                    column_mapping.column_info,
                    filter_value,
                    column_mapping.table_path.split('.')[1]  # Table name
                )
                if condition:
                    conditions.append(condition)
        
        # Add time period filters if specified
        if intent.time_period:
            time_condition = self._build_time_filter(intent.time_period, column_mappings)
            if time_condition:
                conditions.append(time_condition)
        
        return conditions
    
    def _build_filter_condition(
        self,
        column: ColumnInfo,
        filter_value: Any,
        table_alias: str
    ) -> Optional[str]:
        """
        Build a filter condition for a specific column.
        
        Args:
            column: Column information
            filter_value: Filter value
            table_alias: Table alias for the column
            
        Returns:
            Filter condition string or None
        """
        column_ref = f"{table_alias}.{column.name}"
        
        if isinstance(filter_value, (list, tuple)):
            # IN clause for multiple values
            if len(filter_value) == 1:
                return f"{column_ref} = '{filter_value[0]}'"
            else:
                values = "', '".join(str(v) for v in filter_value)
                return f"{column_ref} IN ('{values}')"
        
        elif isinstance(filter_value, dict):
            # Range or comparison filters
            conditions = []
            
            if 'min' in filter_value:
                conditions.append(f"{column_ref} >= {filter_value['min']}")
            if 'max' in filter_value:
                conditions.append(f"{column_ref} <= {filter_value['max']}")
            if 'gt' in filter_value:
                conditions.append(f"{column_ref} > {filter_value['gt']}")
            if 'lt' in filter_value:
                conditions.append(f"{column_ref} < {filter_value['lt']}")
            if 'ne' in filter_value:
                conditions.append(f"{column_ref} != '{filter_value['ne']}'")
            
            return " AND ".join(conditions) if conditions else None
        
        else:
            # Simple equality filter
            if self._is_numeric_column(column):
                return f"{column_ref} = {filter_value}"
            else:
                return f"{column_ref} = '{filter_value}'"
    
    def _build_time_filter(
        self,
        time_period: str,
        column_mappings: List[ColumnMapping]
    ) -> Optional[str]:
        """
        Build time-based filter condition.
        
        Args:
            time_period: Time period specification
            column_mappings: Available column mappings
            
        Returns:
            Time filter condition or None
        """
        # Find date/time columns
        time_columns = []
        for cm in column_mappings:
            if any(time_indicator in cm.column_info.data_type.lower() 
                   for time_indicator in ['date', 'time', 'timestamp']):
                time_columns.append(cm)
        
        if not time_columns:
            # Look for columns with time-related names
            for cm in column_mappings:
                if any(time_name in cm.column_info.name.lower() 
                       for time_name in ['date', 'time', 'created', 'updated', 'modified']):
                    time_columns.append(cm)
        
        if not time_columns:
            return None
        
        # Use the first available time column
        time_column = time_columns[0]
        table_name = time_column.table_path.split('.')[1]
        column_ref = f"{table_name}.{time_column.column_info.name}"
        
        # Apply time filter pattern
        time_period_lower = time_period.lower()
        
        if time_period_lower in self.common_patterns['time_filters']:
            pattern = self.common_patterns['time_filters'][time_period_lower]
            return pattern.format(column=column_ref)
        
        # Try to parse common time expressions
        if 'last' in time_period_lower and 'days' in time_period_lower:
            # Extract number of days
            import re
            match = re.search(r'(\d+)', time_period_lower)
            if match:
                days = int(match.group(1))
                return f"DATE({column_ref}) >= DATE_SUB(CURDATE(), INTERVAL {days} DAY)"
        
        return None
    
    def _build_group_by_columns(
        self,
        intent: QueryIntent,
        column_mappings: List[ColumnMapping]
    ) -> List[str]:
        """
        Build GROUP BY columns from query intent.
        
        Args:
            intent: Query intent
            column_mappings: Available column mappings
            
        Returns:
            List of GROUP BY column references
        """
        group_by_columns = []
        
        for group_attr in intent.group_by:
            # Find column mapping for this grouping attribute
            for cm in column_mappings:
                if cm.business_attribute == group_attr and cm.is_dimension:
                    table_name = cm.table_path.split('.')[1]
                    column_ref = f"{table_name}.{cm.column_info.name}"
                    group_by_columns.append(column_ref)
                    break
        
        return group_by_columns
    
    def _build_order_by_clause(
        self,
        intent: QueryIntent,
        column_mappings: List[ColumnMapping]
    ) -> Optional[str]:
        """
        Build ORDER BY clause from query intent.
        
        Args:
            intent: Query intent
            column_mappings: Available column mappings
            
        Returns:
            ORDER BY clause string or None
        """
        if not intent.order_by:
            return None
        
        # Find column for ordering
        for cm in column_mappings:
            if cm.business_attribute == intent.order_by:
                table_name = cm.table_path.split('.')[1]
                column_ref = f"{table_name}.{cm.column_info.name}"
                
                # Default to DESC for metrics, ASC for dimensions
                direction = "DESC" if cm.is_metric else "ASC"
                return f"{column_ref} {direction}"
        
        return None
    
    def _estimate_query_cost(
        self,
        primary_table: TableMapping,
        joins: List[JoinPath],
        where_conditions: List[str]
    ) -> float:
        """
        Estimate the execution cost of the query.
        
        Args:
            primary_table: Primary table mapping
            joins: Required joins
            where_conditions: WHERE conditions
            
        Returns:
            Estimated cost (number of rows to process)
        """
        # Start with primary table size
        base_rows = primary_table.table_schema.table_info.rows if primary_table.table_schema.table_info else 1000
        
        # Apply selectivity estimates for WHERE conditions
        selectivity = 1.0
        for condition in where_conditions:
            # Simple heuristic: each condition reduces result set
            if '=' in condition:
                selectivity *= 0.1  # Equality conditions are highly selective
            elif any(op in condition for op in ['>', '<', 'BETWEEN']):
                selectivity *= 0.3  # Range conditions are moderately selective
            elif 'IN' in condition:
                selectivity *= 0.2  # IN conditions depend on list size
        
        estimated_rows = base_rows * selectivity
        
        # Factor in joins
        for join in joins:
            estimated_rows *= 1.5  # Each join may increase result size
        
        return estimated_rows
    
    def _generate_optimization_notes(
        self,
        primary_table: TableMapping,
        joins: List[JoinPath],
        column_mappings: List[ColumnMapping]
    ) -> List[str]:
        """
        Generate optimization recommendations for the query.
        
        Args:
            primary_table: Primary table mapping
            joins: Required joins
            column_mappings: Column mappings used
            
        Returns:
            List of optimization notes
        """
        notes = []
        
        # Check for missing indexes
        indexed_columns = set()
        for index in primary_table.table_schema.indexes:
            indexed_columns.update(index.columns)
        
        for cm in column_mappings:
            if cm.table_path.split('.')[1] == primary_table.table_schema.table:
                if cm.column_info.name not in indexed_columns and cm.is_dimension:
                    notes.append(f"Consider adding index on {cm.column_info.name} for better filter performance")
        
        # Check join performance
        for join in joins:
            if not join.foreign_key_based:
                notes.append(f"Join to {join.to_table} is not based on foreign key - consider adding foreign key constraint")
            
            if join.cost_estimate > self.config.get('join_cost_threshold', 1000000):
                notes.append(f"Join to {join.to_table} may be expensive - estimated cost: {join.cost_estimate:.0f}")
        
        # Check for large result sets
        if len(joins) > 3:
            notes.append("Query involves multiple joins - consider breaking into smaller queries")
        
        return notes
    
    async def _generate_sql_components(
        self,
        query_plan: QueryPlan,
        intent: QueryIntent
    ) -> Dict[str, str]:
        """
        Generate SQL components from the query plan.
        
        Args:
            query_plan: Query execution plan
            intent: Original query intent
            
        Returns:
            Dictionary of SQL components
        """
        components = {}
        
        # SELECT clause
        select_parts = []
        
        # Add metric columns with aggregation
        for cm in query_plan.column_mappings:
            if cm.is_metric:
                table_name = cm.table_path.split('.')[1]
                column_ref = f"{table_name}.{cm.column_info.name}"
                
                # Apply aggregation
                if intent.aggregation_type in self.common_patterns['aggregation_templates']:
                    agg_template = self.common_patterns['aggregation_templates'][intent.aggregation_type]
                    aggregated = agg_template.format(column=column_ref)
                    select_parts.append(f"{aggregated} AS {cm.business_attribute}")
                else:
                    select_parts.append(f"{column_ref} AS {cm.business_attribute}")
        
        # Add dimension columns for grouping
        for group_col in query_plan.group_by_columns:
            if group_col not in [sp.split(' AS ')[0] for sp in select_parts]:
                # Find the business attribute name for this column
                attr_name = group_col.split('.')[1]  # Use column name as fallback
                for cm in query_plan.column_mappings:
                    if f"{cm.table_path.split('.')[1]}.{cm.column_info.name}" == group_col:
                        attr_name = cm.business_attribute
                        break
                
                select_parts.append(f"{group_col} AS {attr_name}")
        
        components['select'] = "SELECT " + ", ".join(select_parts)
        
        # FROM clause
        primary_table_name = query_plan.primary_table.table_schema.table
        components['from'] = f"FROM {primary_table_name}"
        
        # JOIN clauses
        join_parts = []
        for join in query_plan.required_joins:
            join_table = join.to_table.split('.')[1]  # Get table name without database
            join_parts.append(f"{join.join_type.value} JOIN {join_table} ON {join.join_condition}")
        
        components['joins'] = "\n".join(join_parts)
        
        # WHERE clause
        if query_plan.where_conditions:
            components['where'] = "WHERE " + " AND ".join(query_plan.where_conditions)
        else:
            components['where'] = ""
        
        # GROUP BY clause
        if query_plan.group_by_columns:
            components['group_by'] = "GROUP BY " + ", ".join(query_plan.group_by_columns)
        else:
            components['group_by'] = ""
        
        # ORDER BY clause
        if query_plan.order_by_clause:
            components['order_by'] = "ORDER BY " + query_plan.order_by_clause
        else:
            components['order_by'] = ""
        
        # LIMIT clause
        if intent.limit:
            components['limit'] = f"LIMIT {intent.limit}"
        else:
            components['limit'] = f"LIMIT {self.config['default_limit']}"
        
        return components
    
    def _assemble_query(self, components: Dict[str, str]) -> str:
        """
        Assemble SQL components into final query.
        
        Args:
            components: Dictionary of SQL components
            
        Returns:
            Complete SQL query
        """
        query_parts = [
            components['select'],
            components['from']
        ]
        
        if components['joins']:
            query_parts.append(components['joins'])
        
        if components['where']:
            query_parts.append(components['where'])
        
        if components['group_by']:
            query_parts.append(components['group_by'])
        
        if components['order_by']:
            query_parts.append(components['order_by'])
        
        if components['limit']:
            query_parts.append(components['limit'])
        
        return "\n".join(query_parts)
    
    async def _optimize_query(self, sql: str, query_plan: QueryPlan) -> str:
        """
        Apply query optimizations.
        
        Args:
            sql: Original SQL query
            query_plan: Query execution plan
            
        Returns:
            Optimized SQL query
        """
        optimized_sql = sql
        
        if self.config.get('enable_index_hints', True):
            # Add index hints if beneficial
            optimized_sql = self._add_index_hints(optimized_sql, query_plan)
        
        # Apply other optimizations...
        # - Query rewriting
        # - Subquery elimination
        # - Predicate pushdown
        
        return optimized_sql
    
    def _add_index_hints(self, sql: str, query_plan: QueryPlan) -> str:
        """
        Add index hints to improve query performance.
        
        Args:
            sql: Original SQL query
            query_plan: Query execution plan
            
        Returns:
            SQL with index hints
        """
        # This is a simplified implementation
        # In practice, you'd analyze the query plan and available indexes
        return sql
    
    async def _validate_query(self, sql: str, query_plan: QueryPlan) -> ValidationResult:
        """
        Validate the generated query.
        
        Args:
            sql: SQL query to validate
            query_plan: Query execution plan
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        # Basic syntax validation
        if not sql.strip():
            errors.append(ValidationError(
                field="sql",
                message="Generated SQL is empty",
                severity=ValidationSeverity.ERROR
            ))
        
        # Check for required components
        if "SELECT" not in sql.upper():
            errors.append(ValidationError(
                field="sql",
                message="SQL missing SELECT clause",
                severity=ValidationSeverity.ERROR
            ))
        
        if "FROM" not in sql.upper():
            errors.append(ValidationError(
                field="sql",
                message="SQL missing FROM clause",
                severity=ValidationSeverity.ERROR
            ))
        
        # Performance warnings
        if len(query_plan.required_joins) > 3:
            warnings.append(ValidationWarning(
                field="joins",
                message="Query has many joins which may impact performance",
                suggestion="Consider breaking into smaller queries"
            ))
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            validated_fields=["sql", "joins", "syntax"]
        )
    
    async def _attempt_query_fixes(
        self,
        sql: str,
        validation_result: ValidationResult
    ) -> str:
        """
        Attempt to fix common query issues.
        
        Args:
            sql: Original SQL query
            validation_result: Validation result with errors
            
        Returns:
            Fixed SQL query
        """
        fixed_sql = sql
        
        for error in validation_result.errors:
            if "missing SELECT" in error.message:
                fixed_sql = "SELECT *\n" + fixed_sql
            elif "missing FROM" in error.message and "FROM" not in fixed_sql.upper():
                # This shouldn't happen with proper query building, but handle it
                fixed_sql += "\nFROM dual"
        
        return fixed_sql
    
    async def _generate_alternative_queries(
        self,
        intent: QueryIntent,
        table_mappings: List[TableMapping],
        context: QueryContext
    ) -> List[str]:
        """
        Generate alternative query suggestions.
        
        Args:
            intent: Original query intent
            table_mappings: Available table mappings
            context: Query context
            
        Returns:
            List of alternative SQL queries
        """
        alternatives = []
        
        # Try different primary tables
        if len(table_mappings) > 1:
            for i, table_mapping in enumerate(table_mappings[1:3], 1):  # Try up to 2 alternatives
                try:
                    # Create modified intent for alternative table
                    alt_plan = QueryPlan(
                        primary_table=table_mapping,
                        required_joins=[],
                        column_mappings=await self._find_column_mappings_for_table(
                            intent, table_mapping.table_schema, context
                        ),
                        where_conditions=self._build_where_conditions(intent, []),
                        group_by_columns=[],
                        order_by_clause=None,
                        estimated_cost=0,
                        optimization_notes=[]
                    )
                    
                    alt_components = await self._generate_sql_components(alt_plan, intent)
                    alt_sql = self._assemble_query(alt_components)
                    alternatives.append(alt_sql)
                    
                except Exception as e:
                    logger.debug(f"Failed to generate alternative query {i}: {e}")
        
        return alternatives[:2]  # Limit to 2 alternatives
    
    def _calculate_query_confidence(self, query_plan: QueryPlan) -> float:
        """
        Calculate confidence score for the generated query.
        
        Args:
            query_plan: Query execution plan
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 0.0
        factors = 0
        
        # Primary table confidence
        confidence += query_plan.primary_table.confidence_score
        factors += 1
        
        # Column mapping confidence
        if query_plan.column_mappings:
            avg_col_confidence = sum(cm.confidence_score for cm in query_plan.column_mappings) / len(query_plan.column_mappings)
            confidence += avg_col_confidence
            factors += 1
        
        # Join quality (foreign key based joins are better)
        if query_plan.required_joins:
            fk_joins = sum(1 for join in query_plan.required_joins if join.foreign_key_based)
            join_quality = fk_joins / len(query_plan.required_joins)
            confidence += join_quality
            factors += 1
        
        # Complexity penalty
        complexity = len(query_plan.required_joins) + len(query_plan.where_conditions)
        if complexity > 5:
            confidence -= 0.1  # Slight penalty for complex queries
        
        return min(1.0, max(0.0, confidence / factors if factors > 0 else 0.0))
    
    def _extract_used_mappings(self, query_plan: QueryPlan) -> List[SemanticMapping]:
        """
        Extract all semantic mappings used in the query.
        
        Args:
            query_plan: Query execution plan
            
        Returns:
            List of semantic mappings used
        """
        used_mappings = []
        
        # Add mappings from primary table
        used_mappings.extend(query_plan.primary_table.semantic_mappings)
        
        # Add mappings from columns
        for cm in query_plan.column_mappings:
            used_mappings.append(cm.semantic_mapping)
        
        return used_mappings
    
    async def _suggest_alternative_metrics(self, failed_metric: str) -> List[str]:
        """
        Suggest alternative metrics when mapping fails.
        
        Args:
            failed_metric: Metric that failed to map
            
        Returns:
            List of suggested alternative metrics
        """
        return await self.semantic_mapper.suggest_alternative_terms(failed_metric)
