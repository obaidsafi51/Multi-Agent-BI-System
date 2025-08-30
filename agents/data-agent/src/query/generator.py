"""
SQL Query Generator from structured QueryIntent objects.
Converts natural language intents into optimized SQL queries for financial data.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SQLQuery:
    """Generated SQL query with metadata"""
    sql: str
    params: Dict[str, Any]
    estimated_rows: Optional[int] = None
    complexity_score: float = 1.0
    optimization_hints: List[str] = None
    
    def __post_init__(self):
        if self.optimization_hints is None:
            self.optimization_hints = []


class QueryGenerator:
    """
    Generates optimized SQL queries from QueryIntent objects.
    Handles financial data queries with proper time period processing and optimization.
    """
    
    # Financial metric to table/column mappings
    METRIC_MAPPINGS = {
        'revenue': ('financial_overview', 'revenue'),
        'sales': ('financial_overview', 'revenue'),
        'income': ('financial_overview', 'revenue'),
        'turnover': ('financial_overview', 'revenue'),
        
        'gross_profit': ('financial_overview', 'gross_profit'),
        'gross_margin': ('financial_overview', 'gross_profit'),
        
        'net_profit': ('financial_overview', 'net_profit'),
        'net_income': ('financial_overview', 'net_profit'),
        'profit': ('financial_overview', 'net_profit'),
        
        'operating_expenses': ('financial_overview', 'operating_expenses'),
        'expenses': ('financial_overview', 'operating_expenses'),
        'costs': ('financial_overview', 'operating_expenses'),
        
        'operating_cash_flow': ('cash_flow', 'operating_cash_flow'),
        'investing_cash_flow': ('cash_flow', 'investing_cash_flow'),
        'financing_cash_flow': ('cash_flow', 'financing_cash_flow'),
        'net_cash_flow': ('cash_flow', 'net_cash_flow'),
        'cash_balance': ('cash_flow', 'cash_balance'),
        'cash_flow': ('cash_flow', 'net_cash_flow'),
        
        'budget': ('budget_tracking', 'budgeted_amount'),
        'actual': ('budget_tracking', 'actual_amount'),
        'variance': ('budget_tracking', 'variance_amount'),
        'budget_variance': ('budget_tracking', 'variance_percentage'),
        
        'roi': ('investments', 'roi_percentage'),
        'investment_value': ('investments', 'current_value'),
        'investment_return': ('investments', 'roi_percentage'),
        
        'debt_to_equity': ('financial_ratios', 'debt_to_equity'),
        'current_ratio': ('financial_ratios', 'current_ratio'),
        'quick_ratio': ('financial_ratios', 'quick_ratio'),
        'gross_margin_ratio': ('financial_ratios', 'gross_margin'),
        'net_margin_ratio': ('financial_ratios', 'net_margin'),
    }
    
    # Time period patterns and their SQL equivalents
    TIME_PATTERNS = {
        r'q1|quarter 1|first quarter': ('quarterly', 1),
        r'q2|quarter 2|second quarter': ('quarterly', 2),
        r'q3|quarter 3|third quarter': ('quarterly', 3),
        r'q4|quarter 4|fourth quarter': ('quarterly', 4),
        r'quarterly|quarter': ('quarterly', None),
        r'monthly|month': ('monthly', None),
        r'yearly|annual|year': ('yearly', None),
        r'daily|day': ('daily', None),
        r'ytd|year to date': ('ytd', None),
        r'mtd|month to date': ('mtd', None),
        r'this year': ('current_year', None),
        r'last year': ('previous_year', None),
        r'this month': ('current_month', None),
        r'last month': ('previous_month', None),
    }
    
    def __init__(self):
        """Initialize query generator with configuration."""
        self.current_date = datetime.now()
        self.current_year = self.current_date.year
        self.current_month = self.current_date.month
        self.current_quarter = (self.current_month - 1) // 3 + 1
    
    def generate_query(self, query_intent: Dict[str, Any]) -> SQLQuery:
        """
        Generate SQL query from QueryIntent object.
        
        Args:
            query_intent: Structured query intent from NLP agent
            
        Returns:
            SQLQuery: Generated SQL with parameters and metadata
        """
        try:
            metric_type = query_intent.get('metric_type', '').lower()
            time_period = query_intent.get('time_period', '').lower()
            aggregation_level = query_intent.get('aggregation_level', 'monthly').lower()
            filters = query_intent.get('filters', {})
            comparison_periods = query_intent.get('comparison_periods', [])
            
            # Get table and column mapping
            table_info = self._get_table_info(metric_type)
            if not table_info:
                raise ValueError(f"Unknown metric type: {metric_type}")
            
            table_name, column_name = table_info
            
            # Parse time period
            date_filter, params = self._parse_time_period(time_period, aggregation_level)
            
            # Build base query
            base_query = self._build_base_query(
                table_name, column_name, date_filter, aggregation_level, filters
            )
            
            # Add comparison periods if requested
            if comparison_periods:
                query, comparison_params = self._add_comparison_periods(
                    base_query, comparison_periods, table_name, column_name, aggregation_level
                )
                params.update(comparison_params)
            else:
                query = base_query
            
            # Optimize query
            optimized_query = self._optimize_query(query, table_name)
            
            # Calculate complexity score
            complexity_score = self._calculate_complexity(optimized_query, len(comparison_periods))
            
            # Generate optimization hints
            optimization_hints = self._generate_optimization_hints(
                table_name, date_filter, len(comparison_periods)
            )
            
            logger.info(
                "Generated SQL query",
                metric_type=metric_type,
                table=table_name,
                complexity_score=complexity_score
            )
            
            return SQLQuery(
                sql=optimized_query,
                params=params,
                complexity_score=complexity_score,
                optimization_hints=optimization_hints
            )
            
        except Exception as e:
            logger.error("Failed to generate SQL query", error=str(e), query_intent=query_intent)
            raise
    
    def _get_table_info(self, metric_type: str) -> Optional[Tuple[str, str]]:
        """
        Get table and column information for a metric type.
        
        Args:
            metric_type: Financial metric type
            
        Returns:
            Tuple of (table_name, column_name) or None if not found
        """
        return self.METRIC_MAPPINGS.get(metric_type.lower())
    
    def _parse_time_period(self, time_period: str, aggregation_level: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse time period string into SQL date filter.
        
        Args:
            time_period: Time period description
            aggregation_level: Data aggregation level
            
        Returns:
            Tuple of (date_filter_sql, parameters)
        """
        params = {}
        
        # Handle specific date ranges
        if re.search(r'\d{4}', time_period):  # Contains year
            year_match = re.search(r'(\d{4})', time_period)
            if year_match:
                year = int(year_match.group(1))
                params['target_year'] = year
                
                # Check for quarter
                quarter_match = re.search(r'q(\d)', time_period.lower())
                if quarter_match:
                    quarter = int(quarter_match.group(1))
                    start_month = (quarter - 1) * 3 + 1
                    end_month = quarter * 3
                    params['start_date'] = f"{year}-{start_month:02d}-01"
                    params['end_date'] = f"{year}-{end_month:02d}-{self._get_month_end_day(year, end_month)}"
                    return "period_date BETWEEN :start_date AND :end_date", params
                
                # Full year
                params['start_date'] = f"{year}-01-01"
                params['end_date'] = f"{year}-12-31"
                return "period_date BETWEEN :start_date AND :end_date", params
        
        # Handle relative time periods
        for pattern, (period_type, period_num) in self.TIME_PATTERNS.items():
            if re.search(pattern, time_period.lower()):
                return self._build_relative_date_filter(period_type, period_num, params)
        
        # Default to current year if no specific period found
        params['start_date'] = f"{self.current_year}-01-01"
        params['end_date'] = f"{self.current_year}-12-31"
        return "period_date BETWEEN :start_date AND :end_date", params
    
    def _build_relative_date_filter(
        self, period_type: str, period_num: Optional[int], params: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Build date filter for relative time periods."""
        
        if period_type == 'quarterly' and period_num:
            start_month = (period_num - 1) * 3 + 1
            end_month = period_num * 3
            params['start_date'] = f"{self.current_year}-{start_month:02d}-01"
            params['end_date'] = f"{self.current_year}-{end_month:02d}-{self._get_month_end_day(self.current_year, end_month)}"
            
        elif period_type == 'current_year':
            params['start_date'] = f"{self.current_year}-01-01"
            params['end_date'] = f"{self.current_year}-12-31"
            
        elif period_type == 'previous_year':
            prev_year = self.current_year - 1
            params['start_date'] = f"{prev_year}-01-01"
            params['end_date'] = f"{prev_year}-12-31"
            
        elif period_type == 'current_month':
            params['start_date'] = f"{self.current_year}-{self.current_month:02d}-01"
            params['end_date'] = f"{self.current_year}-{self.current_month:02d}-{self._get_month_end_day(self.current_year, self.current_month)}"
            
        elif period_type == 'previous_month':
            if self.current_month == 1:
                prev_month, prev_year = 12, self.current_year - 1
            else:
                prev_month, prev_year = self.current_month - 1, self.current_year
            params['start_date'] = f"{prev_year}-{prev_month:02d}-01"
            params['end_date'] = f"{prev_year}-{prev_month:02d}-{self._get_month_end_day(prev_year, prev_month)}"
            
        elif period_type == 'ytd':
            params['start_date'] = f"{self.current_year}-01-01"
            params['end_date'] = self.current_date.strftime('%Y-%m-%d')
            
        elif period_type == 'mtd':
            params['start_date'] = f"{self.current_year}-{self.current_month:02d}-01"
            params['end_date'] = self.current_date.strftime('%Y-%m-%d')
            
        else:
            # Default to current year
            params['start_date'] = f"{self.current_year}-01-01"
            params['end_date'] = f"{self.current_year}-12-31"
        
        return "period_date BETWEEN :start_date AND :end_date", params
    
    def _get_month_end_day(self, year: int, month: int) -> int:
        """Get the last day of a given month."""
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        last_day = next_month - timedelta(days=1)
        return last_day.day
    
    def _build_base_query(
        self, 
        table_name: str, 
        column_name: str, 
        date_filter: str, 
        aggregation_level: str,
        filters: Dict[str, Any]
    ) -> str:
        """Build base SQL query with proper aggregation."""
        
        # Determine date grouping based on aggregation level
        if aggregation_level == 'daily':
            date_group = "DATE(period_date)"
            date_alias = "period_date"
        elif aggregation_level == 'monthly':
            date_group = "DATE_FORMAT(period_date, '%Y-%m')"
            date_alias = "period"
        elif aggregation_level == 'quarterly':
            date_group = "CONCAT(YEAR(period_date), '-Q', QUARTER(period_date))"
            date_alias = "period"
        elif aggregation_level == 'yearly':
            date_group = "YEAR(period_date)"
            date_alias = "period"
        else:
            date_group = "DATE_FORMAT(period_date, '%Y-%m')"
            date_alias = "period"
        
        # Build SELECT clause
        select_clause = f"""
        SELECT 
            {date_group} as {date_alias},
            SUM({column_name}) as {column_name},
            COUNT(*) as record_count,
            MIN(period_date) as period_start,
            MAX(period_date) as period_end
        """
        
        # Build FROM clause
        from_clause = f"FROM {table_name}"
        
        # Build WHERE clause
        where_conditions = [date_filter]
        
        # Add additional filters
        for filter_key, filter_value in filters.items():
            if filter_key == 'department' and table_name == 'budget_tracking':
                where_conditions.append(f"department = '{filter_value}'")
            elif filter_key == 'investment_category' and table_name == 'investments':
                where_conditions.append(f"investment_category = '{filter_value}'")
            elif filter_key == 'status' and table_name == 'investments':
                where_conditions.append(f"status = '{filter_value}'")
        
        where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Build GROUP BY clause
        group_by_clause = f"GROUP BY {date_group}"
        
        # Build ORDER BY clause
        order_by_clause = "ORDER BY period_start ASC"
        
        # Combine all parts
        query = f"""
        {select_clause}
        {from_clause}
        {where_clause}
        {group_by_clause}
        {order_by_clause}
        """
        
        return query.strip()
    
    def _add_comparison_periods(
        self, 
        base_query: str, 
        comparison_periods: List[str], 
        table_name: str, 
        column_name: str,
        aggregation_level: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Add comparison periods to the query using UNION."""
        
        comparison_params = {}
        union_queries = [f"({base_query})"]
        
        for i, comparison_period in enumerate(comparison_periods):
            comp_date_filter, comp_params = self._parse_time_period(comparison_period, aggregation_level)
            
            # Rename parameters to avoid conflicts
            renamed_params = {}
            for key, value in comp_params.items():
                new_key = f"{key}_comp_{i}"
                renamed_params[new_key] = value
                comp_date_filter = comp_date_filter.replace(f":{key}", f":{new_key}")
            
            comparison_params.update(renamed_params)
            
            # Build comparison query
            comp_query = base_query.replace(
                "period_date BETWEEN :start_date AND :end_date",
                comp_date_filter
            )
            
            union_queries.append(f"({comp_query})")
        
        # Combine with UNION ALL
        final_query = " UNION ALL ".join(union_queries)
        final_query += " ORDER BY period_start ASC"
        
        return final_query, comparison_params
    
    def _optimize_query(self, query: str, table_name: str) -> str:
        """Apply query optimizations based on table and query characteristics."""
        
        optimizations = []
        
        # Add index hints for large tables
        if table_name in ['financial_overview', 'cash_flow', 'budget_tracking']:
            # Use index hints for date-based queries
            if 'period_date BETWEEN' in query:
                query = query.replace(
                    f"FROM {table_name}",
                    f"FROM {table_name} USE INDEX (idx_period_date)"
                )
                optimizations.append("Added date index hint")
        
        # Add LIMIT for very broad queries to prevent timeouts
        if 'UNION ALL' not in query and 'LIMIT' not in query:
            query += " LIMIT 1000"
            optimizations.append("Added result limit")
        
        if optimizations:
            logger.debug("Applied query optimizations", optimizations=optimizations)
        
        return query
    
    def _calculate_complexity(self, query: str, comparison_count: int) -> float:
        """Calculate query complexity score for performance estimation."""
        
        complexity = 1.0
        
        # Base complexity factors
        if 'UNION' in query:
            complexity += 0.5 * comparison_count
        
        if 'GROUP BY' in query:
            complexity += 0.3
        
        if 'ORDER BY' in query:
            complexity += 0.2
        
        # Count subqueries and joins
        subquery_count = query.count('(SELECT')
        complexity += 0.4 * subquery_count
        
        join_count = query.upper().count('JOIN')
        complexity += 0.3 * join_count
        
        return min(complexity, 5.0)  # Cap at 5.0
    
    def _generate_optimization_hints(
        self, table_name: str, date_filter: str, comparison_count: int
    ) -> List[str]:
        """Generate optimization hints for query execution."""
        
        hints = []
        
        if comparison_count > 2:
            hints.append("Consider limiting comparison periods for better performance")
        
        if table_name in ['financial_overview', 'cash_flow']:
            hints.append("Query uses indexed date columns for optimal performance")
        
        if 'BETWEEN' in date_filter:
            hints.append("Date range query will use period_date index")
        
        return hints


# Global query generator instance
_query_generator: Optional[QueryGenerator] = None


def get_query_generator() -> QueryGenerator:
    """Get or create global query generator instance."""
    global _query_generator
    
    if _query_generator is None:
        _query_generator = QueryGenerator()
    
    return _query_generator