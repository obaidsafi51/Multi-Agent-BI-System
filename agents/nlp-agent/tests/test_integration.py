"""Integration tests for NLP Agent"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models import QueryContext, QueryIntent, FinancialEntity
from src.query_parser import QueryPreprocessor
from src.context_builder import ContextBuilder


class TestNLPAgentIntegration:
    """Integration tests for NLP Agent components"""
    
    def test_end_to_end_query_processing_flow(self):
        """Test the complete flow from query preprocessing to context building"""
        # Step 1: Preprocess query
        preprocessor = QueryPreprocessor()
        original_query = "Show me Q1 revenue vs last year"
        processed_query = preprocessor.preprocess(original_query)
        
        assert "first quarter" in processed_query
        assert "revenue" in processed_query
        
        # Step 2: Create mock query context (simulating parser output)
        query_context = QueryContext(
            user_id="test_user",
            session_id="test_session",
            query_id="test_query",
            original_query=original_query,
            processed_query=processed_query,
            intent=QueryIntent(
                metric_type="revenue",
                time_period="first_quarter",
                aggregation_level="quarterly",
                comparison_periods=["last_year"],
                visualization_hint="line_chart",
                confidence_score=0.9
            ),
            entities=[
                FinancialEntity(
                    entity_type="metric",
                    entity_value="revenue",
                    confidence_score=0.9,
                    synonyms=["sales", "income"],
                    original_text="revenue"
                ),
                FinancialEntity(
                    entity_type="time_period",
                    entity_value="first_quarter",
                    confidence_score=0.85,
                    synonyms=["Q1"],
                    original_text="Q1"
                )
            ]
        )
        
        # Step 3: Build contexts for other agents
        context_builder = ContextBuilder()
        
        # Test data agent context
        data_context = context_builder.build_data_agent_context(query_context)
        assert data_context["query_id"] == "test_query"
        assert data_context["sql_context"]["table"] == "financial_overview"
        assert data_context["sql_context"]["primary_field"] == "revenue"
        assert data_context["sql_context"]["aggregation_level"] == "quarterly"
        assert "last_year" in data_context["sql_context"]["comparison_periods"]
        
        # Test visualization agent context
        viz_context = context_builder.build_visualization_agent_context(query_context)
        assert viz_context["chart_config"]["chart_type"] == "line_chart"
        assert viz_context["chart_config"]["show_comparisons"] is True
        assert "Revenue" in viz_context["styling_config"]["title"]
        
        # Test personalization agent context
        personal_context = context_builder.build_personalization_agent_context(query_context)
        assert personal_context["behavior_data"]["metric_type"] == "revenue"
        assert personal_context["behavior_data"]["has_comparisons"] is True
        assert "revenue" in personal_context["learning_context"]["user_preferences"]["preferred_metrics"]
        
        # Test MCP context
        mcp_context = context_builder.build_mcp_context(query_context)
        assert mcp_context["context_type"] == "nlp_processing"
        assert "data_agent" in mcp_context["agent_contexts"]
        assert "visualization_agent" in mcp_context["agent_contexts"]
        assert "personalization_agent" in mcp_context["agent_contexts"]
    
    def test_complex_query_processing(self):
        """Test processing of a complex financial query"""
        preprocessor = QueryPreprocessor()
        context_builder = ContextBuilder()
        
        # Complex query with multiple entities and comparisons
        original_query = "Compare YTD cash flow and profit margins by department vs budget and last year"
        processed_query = preprocessor.preprocess(original_query)
        
        # Verify preprocessing
        assert "year to date" in processed_query
        assert "cash flow" in processed_query
        assert "profit margins" in processed_query
        
        # Create complex query context
        query_context = QueryContext(
            user_id="cfo_user",
            session_id="complex_session",
            query_id="complex_query",
            original_query=original_query,
            processed_query=processed_query,
            intent=QueryIntent(
                metric_type="cash_flow",  # Primary metric
                time_period="year_to_date",
                aggregation_level="monthly",
                filters={"department": "all"},
                comparison_periods=["budget", "last_year"],
                visualization_hint="bar_chart",
                confidence_score=0.8
            ),
            entities=[
                FinancialEntity(
                    entity_type="metric",
                    entity_value="cash_flow",
                    confidence_score=0.9,
                    original_text="cash flow"
                ),
                FinancialEntity(
                    entity_type="metric",
                    entity_value="profit_margin",
                    confidence_score=0.85,
                    original_text="profit margins"
                ),
                FinancialEntity(
                    entity_type="time_period",
                    entity_value="year_to_date",
                    confidence_score=0.9,
                    original_text="YTD"
                ),
                FinancialEntity(
                    entity_type="dimension",
                    entity_value="department",
                    confidence_score=0.8,
                    original_text="by department"
                )
            ],
            ambiguities=["Multiple metrics requested"],
            clarifications=["Which metric should be primary?"]
        )
        
        # Test that contexts handle complexity appropriately
        data_context = context_builder.build_data_agent_context(query_context)
        assert data_context["sql_context"]["table"] == "cash_flow"
        assert len(data_context["sql_context"]["comparison_periods"]) == 2
        
        viz_context = context_builder.build_visualization_agent_context(query_context)
        assert viz_context["chart_config"]["show_comparisons"] is True
        assert viz_context["chart_config"]["chart_type"] == "bar_chart"
        
        personal_context = context_builder.build_personalization_agent_context(query_context)
        complexity = context_builder._calculate_query_complexity(query_context)
        assert complexity in ["medium", "complex"]
        assert personal_context["behavior_data"]["query_complexity"] == complexity
    
    def test_error_handling_flow(self):
        """Test error handling in the processing flow"""
        context_builder = ContextBuilder()
        
        # Create context with missing intent
        incomplete_context = QueryContext(
            user_id="test_user",
            session_id="test_session",
            query_id="incomplete_query",
            original_query="Show me something",
            processed_query="show me something"
            # No intent provided
        )
        
        # Test that context builders handle missing intent gracefully
        data_context = context_builder.build_data_agent_context(incomplete_context)
        assert "error" in data_context
        
        viz_context = context_builder.build_visualization_agent_context(incomplete_context)
        assert "error" in viz_context
        
        personal_context = context_builder.build_personalization_agent_context(incomplete_context)
        assert "error" in personal_context
    
    def test_financial_terminology_mapping(self):
        """Test that financial terminology is properly mapped"""
        context_builder = ContextBuilder()
        
        # Test various financial metrics
        test_cases = [
            ("revenue", "financial_overview", "revenue"),
            ("cash_flow", "cash_flow", "net_cash_flow"),
            ("debt_to_equity", "financial_ratios", "debt_to_equity"),
            ("budget", "budget_tracking", "actual_amount"),
            ("investment", "investments", "current_value")
        ]
        
        for metric_type, expected_table, expected_field in test_cases:
            query_context = QueryContext(
                user_id="test_user",
                session_id="test_session",
                query_id=f"test_{metric_type}",
                original_query=f"Show me {metric_type}",
                processed_query=f"show me {metric_type}",
                intent=QueryIntent(
                    metric_type=metric_type,
                    time_period="this_year",
                    confidence_score=0.9
                )
            )
            
            data_context = context_builder.build_data_agent_context(query_context)
            sql_context = data_context["sql_context"]
            
            assert sql_context["table"] == expected_table, f"Wrong table for {metric_type}"
            assert sql_context["primary_field"] == expected_field, f"Wrong field for {metric_type}"