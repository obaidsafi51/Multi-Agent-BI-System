"""
Query optimization logic for analytical workloads and large datasets.
Implements intelligent query optimization strategies for TiDB financial data queries.
"""

import re
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class OptimizationStrategy(Enum):
    """Query optimization strategies"""
    INDEX_HINT = "index_hint"
    PARTITION_PRUNING = "partition_pruning"
    QUERY_REWRITE = "query_rewrite"
    RESULT_LIMITING = "result_limiting"
    AGGREGATION_PUSHDOWN = "aggregation_pushdown"
    PARALLEL_EXECUTION = "parallel_execution"


@dataclass
class OptimizationRule:
    """Query optimization rule definition"""
    name: str
    strategy: OptimizationStrategy
    condition: str
    action: str
    priority: int
    estimated_improvement: float


@dataclass
class QueryPlan:
    """Query execution plan with optimization metadata"""
    original_query: str
    optimized_query: str
    applied_optimizations: List[str]
    estimated_cost: float
    estimated_rows: int
    execution_time_estimate: float
    optimization_confidence: float


class QueryOptimizer:
    """
    Intelligent query optimizer for TiDB analytical workloads.
    Implements cost-based optimization and performance tuning strategies.
    """
    
    # Table statistics for cost estimation
    TABLE_STATS = {
        'financial_overview': {
            'row_count': 50000,
            'avg_row_size': 256,
            'index_selectivity': {
                'idx_period_date': 0.1,
                'idx_period_type': 0.25,
                'idx_period_date_type': 0.05
            }
        },
        'cash_flow': {
            'row_count': 30000,
            'avg_row_size': 192,
            'index_selectivity': {
                'idx_period_date': 0.1
            }
        },
        'budget_tracking': {
            'row_count': 100000,
            'avg_row_size': 128,
            'index_selectivity': {
                'idx_department_period': 0.02,
                'idx_period_date': 0.1
            }
        },
        'investments': {
            'row_count': 5000,
            'avg_row_size': 320,
            'index_selectivity': {
                'idx_status': 0.33,
                'idx_category': 0.2,
                'idx_start_date': 0.1
            }
        },
        'financial_ratios': {
            'row_count': 20000,
            'avg_row_size': 160,
            'index_selectivity': {
                'idx_period_date': 0.1
            }
        }
    }
    
    # Optimization rules
    OPTIMIZATION_RULES = [
        OptimizationRule(
            name="date_range_index_hint",
            strategy=OptimizationStrategy.INDEX_HINT,
            condition="period_date BETWEEN",
            action="USE INDEX (idx_period_date)",
            priority=1,
            estimated_improvement=0.4
        ),
        OptimizationRule(
            name="department_budget_index",
            strategy=OptimizationStrategy.INDEX_HINT,
            condition="department = .* AND .*period_date",
            action="USE INDEX (idx_department_period)",
            priority=2,
            estimated_improvement=0.6
        ),
        OptimizationRule(
            name="limit_large_results",
            strategy=OptimizationStrategy.RESULT_LIMITING,
            condition="SELECT .* FROM .* WHERE",
            action="LIMIT 10000",
            priority=3,
            estimated_improvement=0.3
        ),
        OptimizationRule(
            name="aggregation_with_index",
            strategy=OptimizationStrategy.AGGREGATION_PUSHDOWN,
            condition="GROUP BY .*period_date",
            action="USE INDEX FOR GROUP BY (idx_period_date)",
            priority=2,
            estimated_improvement=0.5
        )
    ]
    
    def __init__(self):
        """Initialize query optimizer with configuration."""
        self.optimization_history = {}
        self.performance_stats = {
            'queries_optimized': 0,
            'avg_improvement': 0.0,
            'total_time_saved': 0.0
        }
    
    def optimize_query(
        self, 
        query: str, 
        query_context: Optional[Dict[str, Any]] = None
    ) -> QueryPlan:
        """
        Optimize SQL query for better performance.
        
        Args:
            query: Original SQL query
            query_context: Additional context for optimization
            
        Returns:
            QueryPlan: Optimized query with execution plan
        """
        try:
            start_time = time.time()
            
            # Analyze query structure
            query_analysis = self._analyze_query(query)
            
            # Apply optimization rules
            optimized_query, applied_optimizations = self._apply_optimizations(
                query, query_analysis, query_context
            )
            
            # Estimate query cost and performance
            cost_estimate = self._estimate_query_cost(optimized_query, query_analysis)
            
            # Calculate optimization confidence
            confidence = self._calculate_optimization_confidence(
                applied_optimizations, query_analysis
            )
            
            optimization_time = time.time() - start_time
            
            # Update performance statistics
            self.performance_stats['queries_optimized'] += 1
            
            logger.info(
                "Query optimization completed",
                applied_optimizations=len(applied_optimizations),
                estimated_improvement=cost_estimate.get('improvement_factor', 1.0),
                optimization_time_ms=optimization_time * 1000
            )
            
            return QueryPlan(
                original_query=query,
                optimized_query=optimized_query,
                applied_optimizations=applied_optimizations,
                estimated_cost=cost_estimate['total_cost'],
                estimated_rows=cost_estimate['estimated_rows'],
                execution_time_estimate=cost_estimate['execution_time_ms'],
                optimization_confidence=confidence
            )
            
        except Exception as e:
            logger.error("Query optimization failed", error=str(e), query=query[:100])
            
            # Return original query if optimization fails
            return QueryPlan(
                original_query=query,
                optimized_query=query,
                applied_optimizations=[],
                estimated_cost=1000.0,
                estimated_rows=1000,
                execution_time_estimate=5000.0,
                optimization_confidence=0.0
            )
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query structure and characteristics.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Dictionary containing query analysis results
        """
        analysis = {
            'tables': [],
            'columns': [],
            'where_conditions': [],
            'joins': [],
            'aggregations': [],
            'order_by': [],
            'group_by': [],
            'has_limit': False,
            'query_type': 'SELECT',
            'complexity_score': 1.0
        }
        
        query_upper = query.upper()
        
        # Extract tables
        table_pattern = r'FROM\s+(\w+)'
        tables = re.findall(table_pattern, query_upper)
        analysis['tables'] = tables
        
        # Extract columns
        select_pattern = r'SELECT\s+(.*?)\s+FROM'
        select_match = re.search(select_pattern, query_upper, re.DOTALL)
        if select_match:
            columns_str = select_match.group(1)
            # Simple column extraction (could be improved)
            columns = [col.strip() for col in columns_str.split(',')]
            analysis['columns'] = columns
        
        # Check for WHERE conditions
        if 'WHERE' in query_upper:
            where_pattern = r'WHERE\s+(.*?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|$)'
            where_match = re.search(where_pattern, query_upper, re.DOTALL)
            if where_match:
                where_clause = where_match.group(1).strip()
                analysis['where_conditions'] = [where_clause]
        
        # Check for JOINs
        join_pattern = r'(INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+JOIN|JOIN)'
        joins = re.findall(join_pattern, query_upper)
        analysis['joins'] = joins
        
        # Check for aggregations
        agg_functions = ['SUM', 'COUNT', 'AVG', 'MIN', 'MAX']
        for func in agg_functions:
            if func in query_upper:
                analysis['aggregations'].append(func)
        
        # Check for GROUP BY
        if 'GROUP BY' in query_upper:
            group_pattern = r'GROUP\s+BY\s+(.*?)(?:\s+ORDER\s+BY|\s+LIMIT|$)'
            group_match = re.search(group_pattern, query_upper, re.DOTALL)
            if group_match:
                group_clause = group_match.group(1).strip()
                analysis['group_by'] = [group_clause]
        
        # Check for ORDER BY
        if 'ORDER BY' in query_upper:
            order_pattern = r'ORDER\s+BY\s+(.*?)(?:\s+LIMIT|$)'
            order_match = re.search(order_pattern, query_upper, re.DOTALL)
            if order_match:
                order_clause = order_match.group(1).strip()
                analysis['order_by'] = [order_clause]
        
        # Check for LIMIT
        analysis['has_limit'] = 'LIMIT' in query_upper
        
        # Calculate complexity score
        complexity = 1.0
        complexity += len(analysis['tables']) * 0.2
        complexity += len(analysis['joins']) * 0.5
        complexity += len(analysis['aggregations']) * 0.3
        complexity += 0.2 if analysis['group_by'] else 0
        complexity += 0.1 if analysis['order_by'] else 0
        
        analysis['complexity_score'] = complexity
        
        return analysis
    
    def _apply_optimizations(
        self, 
        query: str, 
        analysis: Dict[str, Any], 
        context: Optional[Dict[str, Any]]
    ) -> Tuple[str, List[str]]:
        """
        Apply optimization rules to the query.
        
        Args:
            query: Original query
            analysis: Query analysis results
            context: Additional context
            
        Returns:
            Tuple of (optimized_query, applied_optimizations)
        """
        optimized_query = query
        applied_optimizations = []
        
        # Sort rules by priority
        sorted_rules = sorted(self.OPTIMIZATION_RULES, key=lambda r: r.priority)
        
        for rule in sorted_rules:
            if self._rule_applies(rule, query, analysis):
                optimized_query = self._apply_rule(rule, optimized_query, analysis)
                applied_optimizations.append(rule.name)
                
                logger.debug(
                    "Applied optimization rule",
                    rule_name=rule.name,
                    strategy=rule.strategy.value
                )
        
        # Apply additional context-based optimizations
        if context:
            optimized_query, context_optimizations = self._apply_context_optimizations(
                optimized_query, analysis, context
            )
            applied_optimizations.extend(context_optimizations)
        
        return optimized_query, applied_optimizations
    
    def _rule_applies(
        self, 
        rule: OptimizationRule, 
        query: str, 
        analysis: Dict[str, Any]
    ) -> bool:
        """Check if an optimization rule applies to the query."""
        
        query_upper = query.upper()
        
        # Check condition pattern
        if re.search(rule.condition, query_upper):
            return True
        
        # Additional rule-specific checks
        if rule.strategy == OptimizationStrategy.INDEX_HINT:
            # Only apply index hints if we have relevant tables
            relevant_tables = set(analysis['tables']) & set(self.TABLE_STATS.keys())
            return len(relevant_tables) > 0
        
        elif rule.strategy == OptimizationStrategy.RESULT_LIMITING:
            # Only apply limits if query doesn't already have one
            return not analysis['has_limit']
        
        elif rule.strategy == OptimizationStrategy.AGGREGATION_PUSHDOWN:
            # Only apply if we have aggregations and group by
            return len(analysis['aggregations']) > 0 and len(analysis['group_by']) > 0
        
        return False
    
    def _apply_rule(
        self, 
        rule: OptimizationRule, 
        query: str, 
        analysis: Dict[str, Any]
    ) -> str:
        """Apply a specific optimization rule to the query."""
        
        if rule.strategy == OptimizationStrategy.INDEX_HINT:
            return self._apply_index_hint(rule, query, analysis)
        
        elif rule.strategy == OptimizationStrategy.RESULT_LIMITING:
            return self._apply_result_limit(rule, query)
        
        elif rule.strategy == OptimizationStrategy.AGGREGATION_PUSHDOWN:
            return self._apply_aggregation_optimization(rule, query, analysis)
        
        elif rule.strategy == OptimizationStrategy.QUERY_REWRITE:
            return self._apply_query_rewrite(rule, query, analysis)
        
        return query
    
    def _apply_index_hint(
        self, 
        rule: OptimizationRule, 
        query: str, 
        analysis: Dict[str, Any]
    ) -> str:
        """Apply index hints to the query."""
        
        # Find the best index for each table
        for table in analysis['tables']:
            if table in self.TABLE_STATS:
                # Determine best index based on WHERE conditions
                best_index = self._select_best_index(table, analysis['where_conditions'])
                
                if best_index:
                    # Add index hint after table name
                    pattern = f'FROM\\s+{table}'
                    replacement = f'FROM {table} USE INDEX ({best_index})'
                    query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
        
        return query
    
    def _apply_result_limit(self, rule: OptimizationRule, query: str) -> str:
        """Apply result limiting to prevent large result sets."""
        
        # Add LIMIT clause if not present
        if 'LIMIT' not in query.upper():
            # Determine appropriate limit based on query type
            if 'GROUP BY' in query.upper():
                limit = 1000  # Aggregated results
            else:
                limit = 10000  # Detail results
            
            query = f"{query.rstrip(';')} LIMIT {limit}"
        
        return query
    
    def _apply_aggregation_optimization(
        self, 
        rule: OptimizationRule, 
        query: str, 
        analysis: Dict[str, Any]
    ) -> str:
        """Optimize aggregation queries."""
        
        # Add index hints for GROUP BY columns
        if analysis['group_by']:
            for table in analysis['tables']:
                if table in self.TABLE_STATS:
                    # Look for date-based grouping
                    if 'period_date' in analysis['group_by'][0].lower():
                        pattern = f'FROM\\s+{table}'
                        replacement = f'FROM {table} USE INDEX FOR GROUP BY (idx_period_date)'
                        query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
        
        return query
    
    def _apply_query_rewrite(
        self, 
        rule: OptimizationRule, 
        query: str, 
        analysis: Dict[str, Any]
    ) -> str:
        """Apply query rewriting optimizations."""
        
        # Example: Convert correlated subqueries to JOINs
        # This is a simplified example
        if 'EXISTS' in query.upper():
            # Could rewrite EXISTS to JOIN for better performance
            pass
        
        return query
    
    def _select_best_index(
        self, 
        table: str, 
        where_conditions: List[str]
    ) -> Optional[str]:
        """Select the best index for a table based on WHERE conditions."""
        
        if table not in self.TABLE_STATS:
            return None
        
        table_stats = self.TABLE_STATS[table]
        available_indexes = table_stats['index_selectivity']
        
        if not where_conditions:
            return None
        
        where_clause = ' '.join(where_conditions).lower()
        
        # Score indexes based on condition matching
        index_scores = {}
        
        for index_name, selectivity in available_indexes.items():
            score = 0.0
            
            # Check if index columns are used in WHERE clause
            if 'period_date' in index_name and 'period_date' in where_clause:
                score += 1.0
            
            if 'department' in index_name and 'department' in where_clause:
                score += 1.0
            
            if 'status' in index_name and 'status' in where_clause:
                score += 1.0
            
            # Factor in selectivity (lower is better)
            score = score / selectivity if selectivity > 0 else score
            
            index_scores[index_name] = score
        
        # Return index with highest score
        if index_scores:
            best_index = max(index_scores.items(), key=lambda x: x[1])
            return best_index[0] if best_index[1] > 0 else None
        
        return None
    
    def _apply_context_optimizations(
        self, 
        query: str, 
        analysis: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """Apply context-specific optimizations."""
        
        optimizations = []
        
        # Time-based optimizations
        if context.get('time_sensitive', False):
            # Add query timeout hint
            query = f"/*+ MAX_EXECUTION_TIME(30000) */ {query}"
            optimizations.append("execution_timeout")
        
        # User-specific optimizations
        user_id = context.get('user_id')
        if user_id:
            # Could apply user-specific query patterns
            pass
        
        # Data freshness optimizations
        if context.get('allow_stale_data', False):
            # Add read from follower hint for TiDB
            query = f"/*+ READ_FROM_STORAGE(TIKV[{', '.join(analysis['tables'])}]) */ {query}"
            optimizations.append("stale_read")
        
        return query, optimizations
    
    def _estimate_query_cost(
        self, 
        query: str, 
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estimate query execution cost and performance.
        
        Args:
            query: SQL query
            analysis: Query analysis results
            
        Returns:
            Dictionary containing cost estimates
        """
        base_cost = 100.0
        estimated_rows = 1000
        
        # Calculate cost based on tables involved
        for table in analysis['tables']:
            if table in self.TABLE_STATS:
                table_stats = self.TABLE_STATS[table]
                base_cost += table_stats['row_count'] * 0.001
                estimated_rows += table_stats['row_count'] * 0.1
        
        # Adjust for query complexity
        complexity_multiplier = analysis['complexity_score']
        total_cost = base_cost * complexity_multiplier
        
        # Adjust for joins
        join_cost = len(analysis['joins']) * base_cost * 0.5
        total_cost += join_cost
        
        # Adjust for aggregations
        agg_cost = len(analysis['aggregations']) * base_cost * 0.3
        total_cost += agg_cost
        
        # Estimate execution time (simplified model)
        execution_time_ms = total_cost * 10  # Rough conversion
        
        # Apply optimization improvements
        if 'USE INDEX' in query:
            total_cost *= 0.7  # 30% improvement with index
            execution_time_ms *= 0.7
        
        if 'LIMIT' in query:
            total_cost *= 0.8  # 20% improvement with limit
            execution_time_ms *= 0.8
        
        return {
            'total_cost': total_cost,
            'estimated_rows': int(estimated_rows),
            'execution_time_ms': execution_time_ms,
            'improvement_factor': base_cost / total_cost if total_cost > 0 else 1.0
        }
    
    def _calculate_optimization_confidence(
        self, 
        applied_optimizations: List[str], 
        analysis: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for applied optimizations."""
        
        if not applied_optimizations:
            return 0.0
        
        confidence = 0.0
        
        # Base confidence from number of optimizations
        confidence += len(applied_optimizations) * 0.2
        
        # Boost confidence for high-impact optimizations
        high_impact_optimizations = [
            'date_range_index_hint',
            'department_budget_index',
            'aggregation_with_index'
        ]
        
        for opt in applied_optimizations:
            if opt in high_impact_optimizations:
                confidence += 0.3
        
        # Adjust based on query complexity
        if analysis['complexity_score'] > 2.0:
            confidence *= 0.8  # Lower confidence for complex queries
        
        return min(confidence, 1.0)
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization performance statistics."""
        return self.performance_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset optimization statistics."""
        self.performance_stats = {
            'queries_optimized': 0,
            'avg_improvement': 0.0,
            'total_time_saved': 0.0
        }


# Global optimizer instance
_query_optimizer: Optional[QueryOptimizer] = None


def get_query_optimizer() -> QueryOptimizer:
    """Get or create global query optimizer instance."""
    global _query_optimizer
    
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer()
    
    return _query_optimizer