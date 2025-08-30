"""
Query template engine with dynamic SQL generation and parameter substitution.
"""

import json
import os
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, timedelta

from ..models.core import QueryIntent, QueryResult
from .types import QueryTemplate, GeneratedQuery


class QueryTemplateEngine:
    """Dynamic SQL query generation engine using templates"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the query template engine"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "config")
        
        self.config_path = Path(config_path)
        self.templates: Dict[str, QueryTemplate] = {}
        self.template_categories: Dict[str, List[str]] = {}
        
        self._load_templates()
        self._categorize_templates()
    
    def _load_templates(self) -> None:
        """Load query templates from configuration file"""
        try:
            templates_file = self.config_path / "query_templates.json"
            with open(templates_file, 'r') as f:
                config = json.load(f)
                
            # Process each category of templates
            for category, templates in config.items():
                for template_name, template_config in templates.items():
                    query_template = QueryTemplate(
                        name=template_name,
                        template=template_config["template"],
                        description=template_config["description"],
                        parameters=template_config["parameters"],
                        supports_aggregation=template_config.get("supports_aggregation", False),
                        supports_comparison=template_config.get("supports_comparison", False),
                        category=category
                    )
                    
                    # Use full name with category prefix for uniqueness
                    full_name = f"{category}.{template_name}"
                    self.templates[full_name] = query_template
                    
        except FileNotFoundError:
            raise FileNotFoundError(f"Query templates file not found: {templates_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in templates file: {e}")
    
    def _categorize_templates(self) -> None:
        """Organize templates by category for easier lookup"""
        for template_name, template in self.templates.items():
            category = template.category
            if category not in self.template_categories:
                self.template_categories[category] = []
            self.template_categories[category].append(template_name)
    
    def select_template(self, query_intent: QueryIntent) -> Optional[str]:
        """Select the most appropriate template based on query intent"""
        metric_type = query_intent.metric_type.lower()
        
        # Template selection logic based on metric type
        template_mapping = {
            "revenue": "financial_overview_queries.revenue_analysis",
            "profit": "financial_overview_queries.profitability_analysis", 
            "net_profit": "financial_overview_queries.profitability_analysis",
            "gross_profit": "financial_overview_queries.profitability_analysis",
            "operating_expenses": "financial_overview_queries.basic_metric",
            "cash_flow": "cash_flow_queries.cash_flow_summary",
            "operating_cash_flow": "cash_flow_queries.operating_cash_trend",
            "investing_cash_flow": "cash_flow_queries.cash_flow_summary",
            "financing_cash_flow": "cash_flow_queries.cash_flow_summary",
            "cash_balance": "cash_flow_queries.cash_position",
            "budget_variance": "budget_queries.budget_variance",
            "budget": "budget_queries.budget_performance",
            "roi": "investment_queries.roi_analysis",
            "investment": "investment_queries.investment_performance",
            "debt_to_equity": "ratio_queries.leverage_analysis",
            "current_ratio": "ratio_queries.liquidity_analysis",
            "gross_margin": "ratio_queries.financial_ratios",
            "net_margin": "ratio_queries.financial_ratios"
        }
        
        # Check for comparison queries
        if query_intent.comparison_periods:
            comparison_type = self._detect_comparison_type(query_intent.comparison_periods)
            if comparison_type:
                return f"comparison_queries.{comparison_type}"
        
        # Default template selection
        template_name = template_mapping.get(metric_type)
        if template_name and template_name in self.templates:
            return template_name
        
        # Fallback to basic metric template
        return "financial_overview_queries.basic_metric"
    
    def _detect_comparison_type(self, comparison_periods: List[str]) -> Optional[str]:
        """Detect the type of comparison from comparison periods"""
        for period in comparison_periods:
            period_lower = period.lower()
            if any(term in period_lower for term in ["last year", "previous year", "yoy", "year over year"]):
                return "year_over_year"
            elif any(term in period_lower for term in ["last quarter", "previous quarter", "qoq", "quarter over quarter"]):
                return "quarter_over_quarter"
        return None
    
    def generate_query(self, query_intent: QueryIntent, template_name: Optional[str] = None) -> GeneratedQuery:
        """Generate SQL query from template and query intent"""
        if template_name is None:
            template_name = self.select_template(query_intent)
        
        if not template_name or template_name not in self.templates:
            raise ValueError(f"Template not found: {template_name}")
        
        template = self.templates[template_name]
        
        # Build parameters for substitution
        substitution_params = self._build_substitution_parameters(query_intent, template)
        
        # Perform template substitution
        sql = self._substitute_template(template.template, substitution_params)
        
        # Estimate query complexity
        complexity = self._estimate_complexity(sql, query_intent)
        
        return GeneratedQuery(
            sql=sql,
            parameters=substitution_params,
            template_name=template_name,
            estimated_complexity=complexity,
            supports_caching=self._supports_caching(template, query_intent)
        )
    
    def _build_substitution_parameters(self, query_intent: QueryIntent, template: QueryTemplate) -> Dict[str, Any]:
        """Build parameters for template substitution"""
        params = {}
        
        # Time-related parameters
        time_range = self._parse_time_period(query_intent.time_period)
        params.update(time_range)
        
        # Metric-related parameters
        params["metric"] = query_intent.metric_type
        params["metric_columns"] = self._get_metric_columns(query_intent.metric_type)
        
        # Aggregation parameters
        aggregation_level = query_intent.aggregation_level
        params["group_by"] = self._get_group_by_clause(aggregation_level)
        params["time_column"] = "period_date"
        
        # Filter parameters
        params.update(self._build_filter_parameters(query_intent.filters))
        
        # Template-specific parameters
        template_params = template.parameters.copy()
        for key, value in template_params.items():
            if key not in params:
                params[key] = value
        
        return params
    
    def _parse_time_period(self, time_period: str) -> Dict[str, str]:
        """Parse time period string into start and end dates"""
        time_period_lower = time_period.lower().strip()
        current_date = datetime.now()
        
        # Handle specific patterns
        if "q1" in time_period_lower:
            year = self._extract_year(time_period, current_date.year)
            return {
                "start_date": f"{year}-01-01",
                "end_date": f"{year}-03-31"
            }
        elif "q2" in time_period_lower:
            year = self._extract_year(time_period, current_date.year)
            return {
                "start_date": f"{year}-04-01",
                "end_date": f"{year}-06-30"
            }
        elif "q3" in time_period_lower:
            year = self._extract_year(time_period, current_date.year)
            return {
                "start_date": f"{year}-07-01",
                "end_date": f"{year}-09-30"
            }
        elif "q4" in time_period_lower:
            year = self._extract_year(time_period, current_date.year)
            return {
                "start_date": f"{year}-10-01",
                "end_date": f"{year}-12-31"
            }
        elif "ytd" in time_period_lower or "year to date" in time_period_lower:
            year = self._extract_year(time_period, current_date.year)
            return {
                "start_date": f"{year}-01-01",
                "end_date": current_date.strftime("%Y-%m-%d")
            }
        elif "this year" in time_period_lower:
            return {
                "start_date": f"{current_date.year}-01-01",
                "end_date": f"{current_date.year}-12-31"
            }
        elif "last year" in time_period_lower:
            last_year = current_date.year - 1
            return {
                "start_date": f"{last_year}-01-01",
                "end_date": f"{last_year}-12-31"
            }
        elif "last 6 months" in time_period_lower:
            six_months_ago = current_date - timedelta(days=180)
            return {
                "start_date": six_months_ago.strftime("%Y-%m-%d"),
                "end_date": current_date.strftime("%Y-%m-%d")
            }
        elif "last 12 months" in time_period_lower:
            twelve_months_ago = current_date - timedelta(days=365)
            return {
                "start_date": twelve_months_ago.strftime("%Y-%m-%d"),
                "end_date": current_date.strftime("%Y-%m-%d")
            }
        else:
            # Check if it's a standalone year (e.g., "2024")
            year = self._extract_year(time_period, current_date.year)
            if year != current_date.year:  # Year was explicitly provided
                return {
                    "start_date": f"{year}-01-01",
                    "end_date": f"{year}-12-31"
                }
            # Default to current year
            return {
                "start_date": f"{current_date.year}-01-01",
                "end_date": f"{current_date.year}-12-31"
            }
    
    def _extract_year(self, time_period: str, default_year: int) -> int:
        """Extract year from time period string"""
        year_match = re.search(r'\b(20\d{2})\b', time_period)
        return int(year_match.group(1)) if year_match else default_year
    
    def _get_metric_columns(self, metric_type: str) -> str:
        """Get appropriate column names for metric type"""
        metric_columns = {
            "revenue": "revenue",
            "profit": "net_profit",
            "net_profit": "net_profit", 
            "gross_profit": "gross_profit",
            "operating_expenses": "operating_expenses",
            "cash_flow": "net_cash_flow",
            "operating_cash_flow": "operating_cash_flow",
            "cash_balance": "cash_balance"
        }
        
        return metric_columns.get(metric_type.lower(), metric_type)
    
    def _get_group_by_clause(self, aggregation_level: str) -> str:
        """Get GROUP BY clause based on aggregation level"""
        aggregation_mapping = {
            "daily": "period_date",
            "weekly": "YEARWEEK(period_date)",
            "monthly": "YEAR(period_date), MONTH(period_date)",
            "quarterly": "YEAR(period_date), QUARTER(period_date)",
            "yearly": "YEAR(period_date)"
        }
        
        return aggregation_mapping.get(aggregation_level.lower(), "period_date")
    
    def _build_filter_parameters(self, filters: Dict[str, Any]) -> Dict[str, str]:
        """Build filter parameters from query intent filters"""
        filter_params = {}
        
        if "department" in filters:
            filter_params["department_filter"] = f"AND department = '{filters['department']}'"
            filter_params["department"] = filters["department"]
        else:
            filter_params["department_filter"] = ""
        
        if "status" in filters:
            filter_params["status_filter"] = f"status = '{filters['status']}'"
            filter_params["status"] = filters["status"]
        else:
            filter_params["status_filter"] = "status = 'active'"
        
        return filter_params
    
    def _substitute_template(self, template: str, params: Dict[str, Any]) -> str:
        """Perform parameter substitution in template"""
        sql = template
        
        # First pass: replace template-specific parameters that may contain placeholders
        template_params = {}
        regular_params = {}
        
        for key, value in params.items():
            if isinstance(value, str) and '{' in value and '}' in value:
                template_params[key] = value
            else:
                regular_params[key] = value
        
        # Replace placeholders in template-specific parameters first
        for key, value in template_params.items():
            for param_key, param_value in regular_params.items():
                placeholder = f"{{{param_key}}}"
                if placeholder in value:
                    value = value.replace(placeholder, str(param_value))
            template_params[key] = value
        
        # Now replace all parameters in the main template
        all_params = {**regular_params, **template_params}
        for key, value in all_params.items():
            placeholder = f"{{{key}}}"
            if placeholder in sql:
                sql = sql.replace(placeholder, str(value))
        
        # Clean up any remaining empty filters
        # Remove 'WHERE AND' (with any whitespace)
        sql = re.sub(r'\bWHERE\s+AND\b', 'WHERE', sql, flags=re.IGNORECASE)
        # Remove multiple consecutive ANDs
        sql = re.sub(r'\bAND\s+AND\b', 'AND', sql, flags=re.IGNORECASE)
        # Remove trailing AND after WHERE or at end of WHERE clause
        sql = re.sub(r'(WHERE\s*)(AND\s*)+', r'\1', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\s+AND\s*($|;)', r'\1', sql, flags=re.IGNORECASE)
        # Remove empty WHERE clauses (i.e., 'WHERE' followed by nothing or only whitespace)
        sql = re.sub(r'\bWHERE\s*($|;)', r'\1', sql, flags=re.IGNORECASE)
        # Normalize whitespace
        sql = re.sub(r'\s+', ' ', sql)
        
        return sql.strip()
    
    def _estimate_complexity(self, sql: str, query_intent: QueryIntent) -> str:
        """Estimate query complexity for performance optimization"""
        complexity_score = 0
        
        # Check for complex operations
        if "JOIN" in sql.upper():
            complexity_score += 2
        if "SUBQUERY" in sql.upper() or "(" in sql:
            complexity_score += 2
        if "GROUP BY" in sql.upper():
            complexity_score += 1
        if "ORDER BY" in sql.upper():
            complexity_score += 1
        if "LAG(" in sql.upper() or "LEAD(" in sql.upper():
            complexity_score += 3
        
        # Check time range complexity
        time_period = query_intent.time_period.lower()
        if any(term in time_period for term in ["year", "ytd", "12 months"]):
            complexity_score += 2
        elif any(term in time_period for term in ["quarter", "6 months"]):
            complexity_score += 1
        
        # Determine complexity level
        if complexity_score <= 2:
            return "low"
        elif complexity_score <= 5:
            return "medium"
        else:
            return "high"
    
    def _supports_caching(self, template: QueryTemplate, query_intent: QueryIntent) -> bool:
        """Determine if query results can be cached"""
        # Don't cache real-time or current period queries
        time_period = query_intent.time_period.lower()
        if any(term in time_period for term in ["today", "current", "now", "real-time"]):
            return False
        
        # Cache historical data queries
        return True
    
    def get_template_by_name(self, template_name: str) -> Optional[QueryTemplate]:
        """Get template by name"""
        return self.templates.get(template_name)
    
    def get_templates_by_category(self, category: str) -> List[QueryTemplate]:
        """Get all templates in a category"""
        template_names = self.template_categories.get(category, [])
        return [self.templates[name] for name in template_names]
    
    def validate_template(self, template_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate template and parameters"""
        if template_name not in self.templates:
            return {
                "is_valid": False,
                "errors": [f"Template '{template_name}' not found"]
            }
        
        template = self.templates[template_name]
        errors = []
        warnings = []
        
        # Check required parameters
        required_params = self._extract_template_parameters(template.template)
        missing_params = [param for param in required_params if param not in parameters]
        
        if missing_params:
            errors.append(f"Missing required parameters: {missing_params}")
        
        # Check for SQL injection risks
        for key, value in parameters.items():
            if isinstance(value, str) and any(dangerous in value.lower() for dangerous in ["drop", "delete", "truncate", "alter"]):
                warnings.append(f"Potentially dangerous SQL in parameter '{key}': {value}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "required_parameters": required_params
        }
    
    def _extract_template_parameters(self, template: str) -> List[str]:
        """Extract parameter names from template"""
        return re.findall(r'\{(\w+)\}', template)
    
    def get_available_templates(self) -> Dict[str, List[str]]:
        """Get all available templates organized by category"""
        return self.template_categories.copy()
    
    def optimize_query(self, generated_query: GeneratedQuery) -> GeneratedQuery:
        """
        Apply query optimizations using configurable, database-agnostic optimizer.
        
        This method now uses a configuration-driven approach instead of hard-coded
        database-specific optimizations. The optimizer supports:
        - Multiple database types (MySQL, PostgreSQL, SQLite, MSSQL)
        - Configurable optimization rules
        - Performance-based optimization strategies
        - Database-agnostic query improvements
        """
        # Import here to avoid circular imports
        from .query_optimizer import QueryOptimizer
        from .types import DatabaseType
        
        # Initialize optimizer (could be cached as instance variable)
        optimizer = QueryOptimizer(
            config_path=os.path.join(os.path.dirname(__file__), "config"),
            database_type=DatabaseType.MYSQL  # Could be configurable via settings
        )
        
        # Apply optimizations using configuration-driven rules
        optimization_result = optimizer.optimize_query(generated_query)
        
        return GeneratedQuery(
            sql=optimization_result.optimized_sql,
            parameters=generated_query.parameters,
            template_name=generated_query.template_name,
            estimated_complexity=generated_query.estimated_complexity,
            supports_caching=generated_query.supports_caching
        )