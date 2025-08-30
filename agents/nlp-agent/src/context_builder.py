"""Query context builder that structures information for other agents"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import QueryContext, QueryIntent, FinancialEntity

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds structured context for inter-agent communication"""
    
    def __init__(self):
        # Mapping of metric types to database tables/fields
        self.metric_mappings = {
            "revenue": {
                "table": "financial_overview",
                "field": "revenue",
                "chart_type": "line"
            },
            "profit": {
                "table": "financial_overview", 
                "field": "net_profit",
                "chart_type": "bar"
            },
            "gross_profit": {
                "table": "financial_overview",
                "field": "gross_profit", 
                "chart_type": "bar"
            },
            "cash_flow": {
                "table": "cash_flow",
                "field": "net_cash_flow",
                "chart_type": "line"
            },
            "operating_cash_flow": {
                "table": "cash_flow",
                "field": "operating_cash_flow",
                "chart_type": "line"
            },
            "budget": {
                "table": "budget_tracking",
                "field": "actual_amount",
                "chart_type": "bar"
            },
            "investment": {
                "table": "investments",
                "field": "current_value",
                "chart_type": "pie"
            },
            "debt_to_equity": {
                "table": "financial_ratios",
                "field": "debt_to_equity",
                "chart_type": "line"
            },
            "current_ratio": {
                "table": "financial_ratios",
                "field": "current_ratio",
                "chart_type": "line"
            }
        }
        
        # Time period to SQL date filter mappings
        self.time_mappings = {
            "this_year": "YEAR(period_date) = YEAR(CURDATE())",
            "last_year": "YEAR(period_date) = YEAR(CURDATE()) - 1",
            "this_quarter": "QUARTER(period_date) = QUARTER(CURDATE()) AND YEAR(period_date) = YEAR(CURDATE())",
            "last_quarter": "QUARTER(period_date) = QUARTER(CURDATE()) - 1 AND YEAR(period_date) = YEAR(CURDATE())",
            "this_month": "MONTH(period_date) = MONTH(CURDATE()) AND YEAR(period_date) = YEAR(CURDATE())",
            "last_month": "MONTH(period_date) = MONTH(CURDATE()) - 1 AND YEAR(period_date) = YEAR(CURDATE())",
            "ytd": "period_date >= DATE(CONCAT(YEAR(CURDATE()), '-01-01'))",
            "mtd": "period_date >= DATE(CONCAT(YEAR(CURDATE()), '-', MONTH(CURDATE()), '-01'))",
            "qtd": "period_date >= DATE(CONCAT(YEAR(CURDATE()), '-', (QUARTER(CURDATE())-1)*3+1, '-01'))"
        }
    
    def build_data_agent_context(self, query_context: QueryContext) -> Dict[str, Any]:
        """Build context for Data Agent"""
        if not query_context.intent:
            return {"error": "No intent available for data context"}
        
        intent = query_context.intent
        
        # Get metric mapping
        metric_mapping = self.metric_mappings.get(intent.metric_type, {
            "table": "financial_overview",
            "field": "revenue",
            "chart_type": "bar"
        })
        
        # Get time filter
        time_filter = self.time_mappings.get(intent.time_period, "1=1")
        
        # Build SQL context
        sql_context = {
            "table": metric_mapping["table"],
            "primary_field": metric_mapping["field"],
            "time_filter": time_filter,
            "aggregation_level": intent.aggregation_level,
            "filters": intent.filters,
            "comparison_periods": intent.comparison_periods
        }
        
        # Add entity-based filters
        entity_filters = self._extract_entity_filters(query_context.entities)
        if entity_filters:
            sql_context["entity_filters"] = entity_filters
        
        data_context = {
            "query_id": query_context.query_id,
            "user_id": query_context.user_id,
            "session_id": query_context.session_id,
            "sql_context": sql_context,
            "intent": intent.model_dump(),
            "processing_metadata": {
                "source": "nlp_agent",
                "timestamp": datetime.now().isoformat(),
                "confidence_score": intent.confidence_score
            }
        }
        
        logger.info(f"Built data agent context for query {query_context.query_id}")
        return data_context
    
    def build_visualization_agent_context(self, query_context: QueryContext) -> Dict[str, Any]:
        """Build context for Visualization Agent"""
        if not query_context.intent:
            return {"error": "No intent available for visualization context"}
        
        intent = query_context.intent
        
        # Get suggested chart type
        metric_mapping = self.metric_mappings.get(intent.metric_type, {})
        suggested_chart = intent.visualization_hint or metric_mapping.get("chart_type", "bar")
        
        # Determine chart configuration based on intent
        chart_config = {
            "chart_type": suggested_chart,
            "metric_type": intent.metric_type,
            "time_period": intent.time_period,
            "aggregation_level": intent.aggregation_level,
            "show_comparisons": len(intent.comparison_periods) > 0,
            "comparison_periods": intent.comparison_periods
        }
        
        # Add styling preferences
        styling_config = {
            "theme": "corporate",
            "color_scheme": "financial",
            "show_grid": True,
            "show_legend": len(intent.comparison_periods) > 0,
            "title": self._generate_chart_title(intent),
            "x_axis_label": self._get_x_axis_label(intent),
            "y_axis_label": self._get_y_axis_label(intent)
        }
        
        viz_context = {
            "query_id": query_context.query_id,
            "user_id": query_context.user_id,
            "session_id": query_context.session_id,
            "chart_config": chart_config,
            "styling_config": styling_config,
            "intent": intent.model_dump(),
            "entities": [entity.model_dump() for entity in query_context.entities],
            "processing_metadata": {
                "source": "nlp_agent",
                "timestamp": datetime.now().isoformat(),
                "confidence_score": intent.confidence_score
            }
        }
        
        logger.info(f"Built visualization agent context for query {query_context.query_id}")
        return viz_context
    
    def build_personalization_agent_context(self, query_context: QueryContext) -> Dict[str, Any]:
        """Build context for Personalization Agent"""
        if not query_context.intent:
            return {"error": "No intent available for personalization context"}
        
        intent = query_context.intent
        
        # Extract user behavior patterns
        behavior_data = {
            "query_text": query_context.original_query,
            "metric_type": intent.metric_type,
            "time_period": intent.time_period,
            "aggregation_level": intent.aggregation_level,
            "visualization_hint": intent.visualization_hint,
            "entities_used": [entity.entity_type for entity in query_context.entities],
            "query_complexity": self._calculate_query_complexity(query_context),
            "has_comparisons": len(intent.comparison_periods) > 0
        }
        
        # Learning context for personalization
        learning_context = {
            "user_preferences": {
                "preferred_metrics": [intent.metric_type],
                "preferred_time_periods": [intent.time_period],
                "preferred_aggregation": intent.aggregation_level,
                "uses_comparisons": len(intent.comparison_periods) > 0
            },
            "query_patterns": {
                "entity_types": list(set(entity.entity_type for entity in query_context.entities)),
                "query_length": len(query_context.original_query.split()),
                "uses_abbreviations": self._uses_abbreviations(query_context.original_query),
                "ambiguity_level": len(query_context.ambiguities)
            }
        }
        
        personalization_context = {
            "query_id": query_context.query_id,
            "user_id": query_context.user_id,
            "session_id": query_context.session_id,
            "behavior_data": behavior_data,
            "learning_context": learning_context,
            "intent": intent.model_dump(),
            "processing_metadata": {
                "source": "nlp_agent",
                "timestamp": datetime.now().isoformat(),
                "confidence_score": intent.confidence_score
            }
        }
        
        logger.info(f"Built personalization agent context for query {query_context.query_id}")
        return personalization_context
    
    def build_mcp_context(self, query_context: QueryContext) -> Dict[str, Any]:
        """Build context for MCP (Model Context Protocol) storage"""
        mcp_context = {
            "context_id": query_context.query_id,
            "user_id": query_context.user_id,
            "session_id": query_context.session_id,
            "context_type": "nlp_processing",
            "context_data": {
                "original_query": query_context.original_query,
                "processed_query": query_context.processed_query,
                "intent": query_context.intent.model_dump() if query_context.intent else None,
                "entities": [entity.model_dump() for entity in query_context.entities],
                "ambiguities": query_context.ambiguities,
                "clarifications": query_context.clarifications,
                "processing_metadata": query_context.processing_metadata
            },
            "agent_contexts": {
                "data_agent": self.build_data_agent_context(query_context),
                "visualization_agent": self.build_visualization_agent_context(query_context),
                "personalization_agent": self.build_personalization_agent_context(query_context)
            },
            "created_at": query_context.created_at.isoformat(),
            "expires_at": None,  # Set by MCP store based on TTL
            "version": "1.0"
        }
        
        logger.info(f"Built MCP context for query {query_context.query_id}")
        return mcp_context
    
    def _extract_entity_filters(self, entities: List[FinancialEntity]) -> Dict[str, Any]:
        """Extract database filters from recognized entities"""
        filters = {}
        
        for entity in entities:
            if entity.entity_type == "department":
                filters["department"] = entity.entity_value
            elif entity.entity_type == "currency":
                filters["currency"] = entity.entity_value
            elif entity.entity_type == "investment_category":
                filters["investment_category"] = entity.entity_value
            elif entity.entity_type == "status":
                filters["status"] = entity.entity_value
        
        return filters
    
    def _generate_chart_title(self, intent: QueryIntent) -> str:
        """Generate appropriate chart title"""
        metric_name = intent.metric_type.replace("_", " ").title()
        time_name = intent.time_period.replace("_", " ").title()
        
        if intent.comparison_periods:
            return f"{metric_name} - {time_name} vs Comparisons"
        else:
            return f"{metric_name} - {time_name}"
    
    def _get_x_axis_label(self, intent: QueryIntent) -> str:
        """Get appropriate X-axis label"""
        if intent.aggregation_level == "daily":
            return "Date"
        elif intent.aggregation_level == "monthly":
            return "Month"
        elif intent.aggregation_level == "quarterly":
            return "Quarter"
        elif intent.aggregation_level == "yearly":
            return "Year"
        else:
            return "Period"
    
    def _get_y_axis_label(self, intent: QueryIntent) -> str:
        """Get appropriate Y-axis label"""
        ratio_metrics = ["ratio", "margin", "debt_to_equity", "current_ratio", "quick_ratio"]
        if any(metric in intent.metric_type for metric in ratio_metrics):
            return "Ratio"
        elif "percentage" in intent.metric_type or "%" in intent.metric_type:
            return "Percentage"
        else:
            return "Amount ($)"
    
    def _calculate_query_complexity(self, query_context: QueryContext) -> str:
        """Calculate query complexity level"""
        complexity_score = 0
        
        # Base complexity
        complexity_score += 1
        
        # Add for entities
        complexity_score += len(query_context.entities) * 0.5
        
        # Add for comparisons
        if query_context.intent and query_context.intent.comparison_periods:
            complexity_score += len(query_context.intent.comparison_periods)
        
        # Add for filters
        if query_context.intent and query_context.intent.filters:
            complexity_score += len(query_context.intent.filters) * 0.5
        
        # Add for ambiguities
        complexity_score += len(query_context.ambiguities) * 0.3
        
        if complexity_score <= 2:
            return "simple"
        elif complexity_score <= 4:
            return "medium"
        else:
            return "complex"
    
    def _uses_abbreviations(self, query: str) -> bool:
        """Check if query uses financial abbreviations"""
        abbreviations = ["q1", "q2", "q3", "q4", "ytd", "mtd", "qtd", "yoy", "mom", "qoq", 
                        "roi", "roa", "roe", "ebitda", "capex", "opex", "cogs", "sga"]
        
        query_lower = query.lower()
        return any(abbrev in query_lower for abbrev in abbreviations)