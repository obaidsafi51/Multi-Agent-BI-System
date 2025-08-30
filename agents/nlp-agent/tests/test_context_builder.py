"""Tests for context builder"""

import pytest
from datetime import datetime

from src.context_builder import ContextBuilder
from src.models import QueryContext, QueryIntent, FinancialEntity


class TestContextBuilder:
    """Test cases for ContextBuilder"""
    
    @pytest.fixture
    def context_builder(self):
        """Create a ContextBuilder instance"""
        return ContextBuilder()
    
    @pytest.fixture
    def sample_query_context(self):
        """Create a sample QueryContext for testing"""
        return QueryContext(
            user_id="user123",
            session_id="session456",
            query_id="query789",
            original_query="Show me quarterly revenue for this year",
            processed_query="show me quarterly revenue for this year",
            intent=QueryIntent(
                metric_type="revenue",
                time_period="this_year",
                aggregation_level="quarterly",
                filters={"department": "sales"},
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
                    entity_value="this_year",
                    confidence_score=0.85,
                    synonyms=["current year"],
                    original_text="this year"
                ),
                FinancialEntity(
                    entity_type="department",
                    entity_value="sales",
                    confidence_score=0.8,
                    synonyms=["sales team"],
                    original_text="sales"
                )
            ],
            ambiguities=[],
            clarifications=[]
        )
    
    def test_build_data_agent_context(self, context_builder, sample_query_context):
        """Test building context for Data Agent"""
        data_context = context_builder.build_data_agent_context(sample_query_context)
        
        assert data_context["query_id"] == "query789"
        assert data_context["user_id"] == "user123"
        assert data_context["session_id"] == "session456"
        
        sql_context = data_context["sql_context"]
        assert sql_context["table"] == "financial_overview"
        assert sql_context["primary_field"] == "revenue"
        assert sql_context["aggregation_level"] == "quarterly"
        assert "YEAR(period_date) = YEAR(CURDATE())" in sql_context["time_filter"]
        assert sql_context["comparison_periods"] == ["last_year"]
        
        # Check entity filters
        assert "entity_filters" in sql_context
        assert sql_context["entity_filters"]["department"] == "sales"
        
        # Check metadata
        assert data_context["processing_metadata"]["source"] == "nlp_agent"
        assert data_context["processing_metadata"]["confidence_score"] == 0.9
    
    def test_build_data_agent_context_no_intent(self, context_builder):
        """Test building data context without intent"""
        context = QueryContext(
            user_id="user123",
            session_id="session456",
            query_id="query789",
            original_query="test",
            processed_query="test"
        )
        
        data_context = context_builder.build_data_agent_context(context)
        assert "error" in data_context
    
    def test_build_visualization_agent_context(self, context_builder, sample_query_context):
        """Test building context for Visualization Agent"""
        viz_context = context_builder.build_visualization_agent_context(sample_query_context)
        
        assert viz_context["query_id"] == "query789"
        assert viz_context["user_id"] == "user123"
        
        chart_config = viz_context["chart_config"]
        assert chart_config["chart_type"] == "line_chart"  # From visualization_hint
        assert chart_config["metric_type"] == "revenue"
        assert chart_config["time_period"] == "this_year"
        assert chart_config["aggregation_level"] == "quarterly"
        assert chart_config["show_comparisons"] is True
        assert chart_config["comparison_periods"] == ["last_year"]
        
        styling_config = viz_context["styling_config"]
        assert styling_config["theme"] == "corporate"
        assert styling_config["color_scheme"] == "financial"
        assert styling_config["show_legend"] is True  # Because has comparisons
        assert "Revenue" in styling_config["title"]
        assert styling_config["x_axis_label"] == "Quarter"
        assert styling_config["y_axis_label"] == "Amount ($)"
    
    def test_build_personalization_agent_context(self, context_builder, sample_query_context):
        """Test building context for Personalization Agent"""
        personal_context = context_builder.build_personalization_agent_context(sample_query_context)
        
        assert personal_context["query_id"] == "query789"
        assert personal_context["user_id"] == "user123"
        
        behavior_data = personal_context["behavior_data"]
        assert behavior_data["query_text"] == "Show me quarterly revenue for this year"
        assert behavior_data["metric_type"] == "revenue"
        assert behavior_data["time_period"] == "this_year"
        assert behavior_data["has_comparisons"] is True
        assert behavior_data["query_complexity"] in ["simple", "medium", "complex"]
        
        learning_context = personal_context["learning_context"]
        user_prefs = learning_context["user_preferences"]
        assert user_prefs["preferred_metrics"] == ["revenue"]
        assert user_prefs["preferred_time_periods"] == ["this_year"]
        assert user_prefs["uses_comparisons"] is True
        
        query_patterns = learning_context["query_patterns"]
        assert "metric" in query_patterns["entity_types"]
        assert "time_period" in query_patterns["entity_types"]
        assert "department" in query_patterns["entity_types"]
        assert query_patterns["query_length"] > 0
    
    def test_build_mcp_context(self, context_builder, sample_query_context):
        """Test building MCP context"""
        mcp_context = context_builder.build_mcp_context(sample_query_context)
        
        assert mcp_context["context_id"] == "query789"
        assert mcp_context["user_id"] == "user123"
        assert mcp_context["session_id"] == "session456"
        assert mcp_context["context_type"] == "nlp_processing"
        assert mcp_context["version"] == "1.0"
        
        context_data = mcp_context["context_data"]
        assert context_data["original_query"] == "Show me quarterly revenue for this year"
        assert context_data["intent"]["metric_type"] == "revenue"
        assert len(context_data["entities"]) == 3
        
        agent_contexts = mcp_context["agent_contexts"]
        assert "data_agent" in agent_contexts
        assert "visualization_agent" in agent_contexts
        assert "personalization_agent" in agent_contexts
    
    def test_extract_entity_filters(self, context_builder):
        """Test extracting entity filters"""
        entities = [
            FinancialEntity(
                entity_type="department",
                entity_value="sales",
                confidence_score=0.9,
                original_text="sales"
            ),
            FinancialEntity(
                entity_type="currency",
                entity_value="USD",
                confidence_score=0.8,
                original_text="USD"
            ),
            FinancialEntity(
                entity_type="metric",  # Should not be included in filters
                entity_value="revenue",
                confidence_score=0.9,
                original_text="revenue"
            )
        ]
        
        filters = context_builder._extract_entity_filters(entities)
        
        assert filters["department"] == "sales"
        assert filters["currency"] == "USD"
        assert "metric" not in filters
    
    def test_generate_chart_title(self, context_builder):
        """Test chart title generation"""
        intent = QueryIntent(
            metric_type="cash_flow",
            time_period="this_quarter",
            comparison_periods=["last_quarter"]
        )
        
        title = context_builder._generate_chart_title(intent)
        assert "Cash Flow" in title
        assert "This Quarter" in title
        assert "vs Comparisons" in title
        
        # Test without comparisons
        intent.comparison_periods = []
        title = context_builder._generate_chart_title(intent)
        assert "vs Comparisons" not in title
    
    def test_get_axis_labels(self, context_builder):
        """Test axis label generation"""
        # Test X-axis labels
        intent = QueryIntent(metric_type="revenue", time_period="this_year")
        
        intent.aggregation_level = "daily"
        assert context_builder._get_x_axis_label(intent) == "Date"
        
        intent.aggregation_level = "monthly"
        assert context_builder._get_x_axis_label(intent) == "Month"
        
        intent.aggregation_level = "quarterly"
        assert context_builder._get_x_axis_label(intent) == "Quarter"
        
        intent.aggregation_level = "yearly"
        assert context_builder._get_x_axis_label(intent) == "Year"
        
        # Test Y-axis labels
        intent.metric_type = "debt_to_equity"
        assert context_builder._get_y_axis_label(intent) == "Ratio"
        
        intent.metric_type = "profit_margin"
        assert context_builder._get_y_axis_label(intent) == "Ratio"
        
        intent.metric_type = "revenue"
        assert context_builder._get_y_axis_label(intent) == "Amount ($)"
    
    def test_calculate_query_complexity(self, context_builder, sample_query_context):
        """Test query complexity calculation"""
        # Test with sample context (should be medium/complex)
        complexity = context_builder._calculate_query_complexity(sample_query_context)
        assert complexity in ["simple", "medium", "complex"]
        
        # Test simple query
        simple_context = QueryContext(
            user_id="user123",
            session_id="session456",
            query_id="query789",
            original_query="revenue",
            processed_query="revenue",
            intent=QueryIntent(metric_type="revenue", time_period="this_year"),
            entities=[],
            ambiguities=[]
        )
        
        complexity = context_builder._calculate_query_complexity(simple_context)
        assert complexity == "simple"
    
    def test_uses_abbreviations(self, context_builder):
        """Test abbreviation detection"""
        assert context_builder._uses_abbreviations("Show me Q1 revenue") is True
        assert context_builder._uses_abbreviations("Show me YTD performance") is True
        assert context_builder._uses_abbreviations("What's our ROI?") is True
        assert context_builder._uses_abbreviations("Show me revenue this year") is False