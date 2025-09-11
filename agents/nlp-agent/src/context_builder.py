"""Simplified query context builder focused on inter-agent communication"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import QueryContext, QueryIntent, FinancialEntity

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Simplified context builder focused on structuring information for other agents.
    SQL generation is now handled by the MCP server.
    """
    
    def __init__(self):
        # Chart type suggestions based on metric types
        self.chart_type_mappings = {
            "revenue": "line",
            "profit": "bar",
            "gross_profit": "bar",
            "cash_flow": "line",
            "operating_cash_flow": "line",
            "budget": "bar",
            "investment": "pie",
            "debt_to_equity": "line",
            "current_ratio": "line"
        }
    
    def build_query_context(
        self,
        query: str,
        intent: QueryIntent,
        user_context: Optional[Dict[str, Any]] = None,
        session_context: Optional[Dict[str, Any]] = None,
        schema_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build comprehensive context for inter-agent communication"""
        
        context = {
            "query_metadata": {
                "original_query": query,
                "intent": intent.model_dump() if intent else None,
                "processing_timestamp": datetime.now().isoformat(),
                "confidence_score": intent.confidence_score if intent else 0.5
            },
            "data_agent_context": self._build_data_agent_context(intent, user_context),
            "visualization_agent_context": self._build_visualization_agent_context(intent),
            "personalization_agent_context": self._build_personalization_agent_context(
                query, intent, user_context
            ),
            "session_context": session_context or {},
            "schema_context": schema_context or {},
            "user_context": user_context or {}
        }
        
        logger.info(f"Built comprehensive query context for intent: {intent.metric_type if intent else 'unknown'}")
        return context
    
    def _build_data_agent_context(
        self,
        intent: QueryIntent,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build simplified context for Data Agent"""
        if not intent:
            return {"error": "No intent available for data context"}
        
        return {
            "metric_type": intent.metric_type,
            "time_period": intent.time_period,
            "aggregation_level": intent.aggregation_level,
            "filters": intent.filters,
            "comparison_periods": intent.comparison_periods,
            "confidence_score": intent.confidence_score,
            "user_context": user_context or {}
        }
    
    def _build_visualization_agent_context(self, intent: QueryIntent) -> Dict[str, Any]:
        """Build context for Visualization Agent"""
        if not intent:
            return {"error": "No intent available for visualization context"}
        
        # Get suggested chart type
        suggested_chart = intent.visualization_hint or self.chart_type_mappings.get(
            intent.metric_type, "bar"
        )
        
        return {
            "chart_type": suggested_chart,
            "metric_type": intent.metric_type,
            "time_period": intent.time_period,
            "aggregation_level": intent.aggregation_level,
            "show_comparisons": len(intent.comparison_periods) > 0,
            "comparison_periods": intent.comparison_periods,
            "title": self._generate_chart_title(intent),
            "styling": {
                "theme": "corporate",
                "color_scheme": "financial",
                "show_grid": True,
                "show_legend": len(intent.comparison_periods) > 0
            }
        }
    
    def _build_personalization_agent_context(
        self,
        query: str,
        intent: QueryIntent,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build context for Personalization Agent"""
        if not intent:
            return {"error": "No intent available for personalization context"}
        
        return {
            "query_text": query,
            "metric_type": intent.metric_type,
            "time_period": intent.time_period,
            "aggregation_level": intent.aggregation_level,
            "visualization_hint": intent.visualization_hint,
            "query_complexity": self._calculate_query_complexity(query, intent),
            "has_comparisons": len(intent.comparison_periods) > 0,
            "user_preferences": {
                "preferred_metrics": [intent.metric_type],
                "preferred_time_periods": [intent.time_period],
                "preferred_aggregation": intent.aggregation_level
            },
            "user_context": user_context or {}
        }
    
    def _generate_chart_title(self, intent: QueryIntent) -> str:
        """Generate appropriate chart title"""
        metric_name = intent.metric_type.replace("_", " ").title()
        time_name = intent.time_period.replace("_", " ").title()
        
        if intent.comparison_periods:
            return f"{metric_name} - {time_name} vs Comparisons"
        else:
            return f"{metric_name} - {time_name}"
    
    def _calculate_query_complexity(self, query: str, intent: QueryIntent) -> str:
        """Calculate query complexity level"""
        complexity_score = 1  # Base complexity
        
        # Add for query length
        query_words = len(query.split())
        if query_words > 10:
            complexity_score += 1
        if query_words > 20:
            complexity_score += 1
        
        # Add for comparisons
        if intent.comparison_periods:
            complexity_score += len(intent.comparison_periods) * 0.5
        
        # Add for filters
        if intent.filters:
            complexity_score += len(intent.filters) * 0.3
        
        # Check for abbreviations
        if self._uses_abbreviations(query):
            complexity_score += 0.5
        
        if complexity_score <= 2:
            return "simple"
        elif complexity_score <= 4:
            return "medium"
        else:
            return "complex"
    
    def _uses_abbreviations(self, query: str) -> bool:
        """Check if query uses financial abbreviations"""
        abbreviations = [
            "q1", "q2", "q3", "q4", "ytd", "mtd", "qtd", 
            "yoy", "mom", "qoq", "roi", "roa", "roe", 
            "ebitda", "capex", "opex", "cogs", "sga"
        ]
        
        query_lower = query.lower()
        return any(abbrev in query_lower for abbrev in abbreviations)