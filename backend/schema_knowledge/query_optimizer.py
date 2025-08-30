"""
Database-agnostic query optimizer with configuration-driven optimization strategies.
"""

import json
import re
import os
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from .types import (
    GeneratedQuery,
    OptimizationResult,
    OptimizationRule,
    DatabaseType
)


class QueryOptimizer:
    """Database-agnostic query optimizer with configurable strategies"""
    
    def __init__(self, config_path: Optional[str] = None, database_type: DatabaseType = DatabaseType.MYSQL):
        """Initialize query optimizer with configuration"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "config")
        
        self.config_path = Path(config_path)
        self.database_type = database_type
        self.optimization_config = self._load_optimization_config()
        self.optimization_rules = self._build_optimization_rules()
        
        # Performance tracking
        self.optimization_stats = {
            "total_optimizations": 0,
            "successful_optimizations": 0,
            "performance_improvements": 0
        }
    
    def _load_optimization_config(self) -> Dict[str, Any]:
        """Load optimization configuration from JSON file"""
        try:
            config_file = self.config_path / "optimization_config.json"
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Return default configuration if file not found
            return self._get_default_config()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in optimization config: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default optimization configuration"""
        return {
            "database_type": "mysql",
            "optimization_rules": {
                "result_limiting": {
                    "enabled": True,
                    "rules": [
                        {
                            "condition": {"complexity": "high", "no_existing_limit": True},
                            "default_limit": 1000
                        }
                    ]
                }
            },
            "performance_thresholds": {
                "complexity_scoring": {
                    "base_score": 0,
                    "join_penalty": 2,
                    "subquery_penalty": 3
                }
            }
        }
    
    def _build_optimization_rules(self) -> List[OptimizationRule]:
        """Build optimization rules from configuration"""
        rules = []
        
        # Index hint rules
        if self.optimization_config.get("optimization_rules", {}).get("index_hints", {}).get("enabled", False):
            for rule_config in self.optimization_config["optimization_rules"]["index_hints"].get("rules", []):
                rules.append(OptimizationRule(
                    name=f"index_hint_{len(rules)}",
                    condition=rule_config["condition"],
                    action=rule_config.get(self.database_type.value, {}),
                    priority=2
                ))
        
        # Result limiting rules
        if self.optimization_config.get("optimization_rules", {}).get("result_limiting", {}).get("enabled", False):
            for rule_config in self.optimization_config["optimization_rules"]["result_limiting"].get("rules", []):
                rules.append(OptimizationRule(
                    name=f"result_limit_{len(rules)}",
                    condition=rule_config["condition"],
                    action={"limit": rule_config.get("default_limit", 1000)},
                    priority=1
                ))
        
        # Query rewriting rules
        if self.optimization_config.get("optimization_rules", {}).get("query_rewriting", {}).get("enabled", False):
            for rule_config in self.optimization_config["optimization_rules"]["query_rewriting"].get("rules", []):
                rules.append(OptimizationRule(
                    name=rule_config["name"],
                    condition=rule_config.get("condition", {}),
                    action={
                        "pattern": rule_config["pattern"],
                        "replacement": rule_config["replacement"]
                    },
                    priority=3
                ))
        
        # Sort rules by priority
        rules.sort(key=lambda x: x.priority, reverse=True)
        return rules
    
    def optimize_query(self, generated_query: GeneratedQuery) -> OptimizationResult:
        """Optimize a generated query using configured rules"""
        self.optimization_stats["total_optimizations"] += 1
        
        original_sql = generated_query.sql
        optimized_sql = original_sql
        applied_optimizations = []
        warnings = []
        
        # Calculate performance score
        performance_score = self._calculate_performance_score(optimized_sql, generated_query)
        
        # Apply optimization rules based on complexity and conditions
        complexity = generated_query.estimated_complexity
        optimization_level = self._get_optimization_level(complexity, performance_score)
        
        for rule in self.optimization_rules:
            if not rule.enabled:
                continue
            
            if self._should_apply_rule(rule, optimized_sql, generated_query, optimization_level):
                try:
                    optimized_sql, rule_applied = self._apply_optimization_rule(rule, optimized_sql, generated_query)
                    if rule_applied:
                        applied_optimizations.append(rule.name)
                except Exception as e:
                    warnings.append(f"Failed to apply optimization rule '{rule.name}': {str(e)}")
        
        # Database-specific optimizations
        if self.database_type != DatabaseType.SQLITE:  # SQLite has limited optimization options
            optimized_sql, db_optimizations = self._apply_database_specific_optimizations(
                optimized_sql, generated_query
            )
            applied_optimizations.extend(db_optimizations)
        
        # Final cleanup
        optimized_sql = self._cleanup_sql(optimized_sql)
        
        # Update statistics
        if len(applied_optimizations) > 0:
            self.optimization_stats["successful_optimizations"] += 1
        
        return OptimizationResult(
            original_sql=original_sql,
            optimized_sql=optimized_sql,
            applied_optimizations=applied_optimizations,
            performance_score=performance_score,
            warnings=warnings,
            database_specific=(self.database_type != DatabaseType.MYSQL)
        )
    
    def _calculate_performance_score(self, sql: str, generated_query: GeneratedQuery) -> int:
        """Calculate performance score for the query"""
        scoring_config = self.optimization_config.get("performance_thresholds", {}).get("complexity_scoring", {})
        
        score = scoring_config.get("base_score", 0)
        
        # Check for performance-impacting patterns
        sql_upper = sql.upper()
        
        if "JOIN" in sql_upper:
            score += scoring_config.get("join_penalty", 2) * sql_upper.count("JOIN")
        
        if "(" in sql and "SELECT" in sql_upper:  # Subquery detection
            score += scoring_config.get("subquery_penalty", 3)
        
        if any(func in sql_upper for func in ["LAG(", "LEAD(", "ROW_NUMBER(", "RANK("]):
            score += scoring_config.get("window_function_penalty", 2)
        
        if "GROUP BY" in sql_upper:
            score += scoring_config.get("group_by_penalty", 1)
        
        if "ORDER BY" in sql_upper:
            score += scoring_config.get("order_by_penalty", 1)
        
        # Time range penalty
        if self._has_large_time_range(generated_query):
            score += scoring_config.get("large_time_range_penalty", 2)
        
        return score
    
    def _get_optimization_level(self, complexity: str, performance_score: int) -> str:
        """Determine optimization level based on complexity and performance score"""
        thresholds = self.optimization_config.get("performance_thresholds", {}).get("optimization_triggers", {})
        
        for level, config in thresholds.items():
            if performance_score <= config.get("max_score", 999):
                return level
        
        return "high_complexity"
    
    def _should_apply_rule(self, rule: OptimizationRule, sql: str, 
                          generated_query: GeneratedQuery, optimization_level: str) -> bool:
        """Determine if an optimization rule should be applied"""
        condition = rule.condition
        
        # Check complexity condition
        if "complexity" in condition:
            required_complexity = condition["complexity"]
            if isinstance(required_complexity, list):
                if generated_query.estimated_complexity not in required_complexity:
                    return False
            elif generated_query.estimated_complexity != required_complexity:
                return False
        
        # Check table condition
        if "table" in condition:
            required_table = condition["table"]
            if required_table not in sql.lower():
                return False
        
        # Check ORDER BY columns condition
        if "order_by_columns" in condition:
            required_columns = condition["order_by_columns"]
            sql_upper = sql.upper()
            if "ORDER BY" not in sql_upper:
                return False
            
            for column in required_columns:
                if column.upper() not in sql_upper:
                    return False
        
        # Check for existing LIMIT
        if condition.get("no_existing_limit", False):
            if "LIMIT" in sql.upper():
                return False
        
        # Check joins condition
        if condition.get("joins", False):
            if "JOIN" not in sql.upper():
                return False
        
        return True
    
    def _apply_optimization_rule(self, rule: OptimizationRule, sql: str, 
                               generated_query: GeneratedQuery) -> Tuple[str, bool]:
        """Apply a specific optimization rule"""
        action = rule.action
        
        # Handle index hints
        if "hint" in action and action["hint"]:
            position = action.get("position", "after_table")
            hint = action["hint"]
            
            if position == "after_table" and "table" in rule.condition:
                table_name = rule.condition["table"]
                old_pattern = f"FROM {table_name}"
                new_pattern = f"FROM {table_name} {hint}"
                
                if old_pattern in sql and hint not in sql:
                    sql = sql.replace(old_pattern, new_pattern)
                    return sql, True
            
            elif position == "comment":
                if hint not in sql:
                    sql = f"{hint}\n{sql}"
                    return sql, True
        
        # Handle result limiting
        if "limit" in action:
            limit_value = action["limit"]
            if "LIMIT" not in sql.upper():
                sql += f" LIMIT {limit_value}"
                return sql, True
        
        # Handle query rewriting
        if "pattern" in action and "replacement" in action:
            pattern = action["pattern"]
            replacement = action["replacement"]
            
            if re.search(pattern, sql, re.IGNORECASE):
                sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)
                return sql, True
        
        return sql, False
    
    def _apply_database_specific_optimizations(self, sql: str, 
                                             generated_query: GeneratedQuery) -> Tuple[str, List[str]]:
        """Apply database-specific optimizations"""
        optimizations = []
        db_settings = self.optimization_config.get("database_specific_settings", {}).get(self.database_type.value, {})
        
        # Check query length limits
        max_length = db_settings.get("max_query_length", 1000000)
        if len(sql) > max_length:
            optimizations.append("query_length_warning")
        
        # Database-specific date format optimization
        preferred_date_format = db_settings.get("preferred_date_format", "YYYY-MM-DD")
        if preferred_date_format and "date" in sql.lower():
            # This is a placeholder for more sophisticated date format optimization
            optimizations.append("date_format_optimization")
        
        # PostgreSQL specific optimizations
        if self.database_type == DatabaseType.POSTGRESQL:
            # Add query planner hints as comments
            if generated_query.estimated_complexity == "high":
                sql = f"/* QUERY PLANNER: Consider using parallel execution */\n{sql}"
                optimizations.append("postgresql_planner_hint")
        
        # MySQL specific optimizations
        elif self.database_type == DatabaseType.MYSQL:
            # Add SQL_CALC_FOUND_ROWS for pagination queries
            if "LIMIT" in sql.upper() and "SQL_CALC_FOUND_ROWS" not in sql.upper():
                sql = sql.replace("SELECT", "SELECT SQL_CALC_FOUND_ROWS", 1)
                optimizations.append("mysql_calc_found_rows")
        
        return sql, optimizations
    
    def _has_large_time_range(self, generated_query: GeneratedQuery) -> bool:
        """Check if query has a large time range"""
        parameters = generated_query.parameters
        
        if "start_date" in parameters and "end_date" in parameters:
            try:
                from datetime import datetime
                start = datetime.strptime(parameters["start_date"], "%Y-%m-%d")
                end = datetime.strptime(parameters["end_date"], "%Y-%m-%d")
                duration = (end - start).days
                return duration > 365  # More than a year
            except (ValueError, KeyError):
                pass
        
        return False
    
    def _cleanup_sql(self, sql: str) -> str:
        """Clean up the SQL query"""
        # Remove extra whitespace
        sql = re.sub(r'\s+', ' ', sql)
        
        # Remove trailing whitespace
        sql = sql.strip()
        
        # Ensure proper semicolon ending
        if not sql.endswith(';') and not sql.endswith('LIMIT'):
            sql += ';'
        
        return sql
    
    def set_database_type(self, database_type: DatabaseType) -> None:
        """Change the database type for optimization"""
        self.database_type = database_type
        self.optimization_rules = self._build_optimization_rules()
    
    def add_custom_rule(self, rule: OptimizationRule) -> None:
        """Add a custom optimization rule"""
        self.optimization_rules.append(rule)
        self.optimization_rules.sort(key=lambda x: x.priority, reverse=True)
    
    def get_optimization_statistics(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        total = self.optimization_stats["total_optimizations"]
        successful = self.optimization_stats["successful_optimizations"]
        
        return {
            "total_optimizations": total,
            "successful_optimizations": successful,
            "success_rate": successful / total if total > 0 else 0,
            "database_type": self.database_type.value,
            "active_rules": len([r for r in self.optimization_rules if r.enabled])
        }
    
    def validate_optimization_config(self) -> Dict[str, Any]:
        """Validate the optimization configuration"""
        errors = []
        warnings = []
        
        # Check if database type is supported
        if self.database_type.value not in ["mysql", "postgresql", "sqlite", "mssql"]:
            errors.append(f"Unsupported database type: {self.database_type.value}")
        
        # Check rule configurations
        for rule in self.optimization_rules:
            if not rule.condition:
                warnings.append(f"Rule '{rule.name}' has empty condition")
            
            if not rule.action:
                warnings.append(f"Rule '{rule.name}' has empty action")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "total_rules": len(self.optimization_rules),
            "enabled_rules": len([r for r in self.optimization_rules if r.enabled])
        }