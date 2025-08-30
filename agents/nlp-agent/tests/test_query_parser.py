"""Tests for query parser"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.kimi_client import KimiClient
from src.models import ProcessingResult, QueryContext, QueryIntent, FinancialEntity
from src.query_parser import QueryParser, QueryPreprocessor


class TestQueryPreprocessor:
    """Test cases for QueryPreprocessor"""
    
    @pytest.fixture
    def preprocessor(self):
        """Create a QueryPreprocessor instance"""
        return QueryPreprocessor()
    
    def test_preprocess_abbreviations(self, preprocessor):
        """Test abbreviation expansion"""
        query = "Show me Q1 revenue and ROI"
        processed = preprocessor.preprocess(query)
        
        assert "first quarter" in processed
        assert "return on investment" in processed
        assert "q1" not in processed.lower()
        assert "roi" not in processed.lower()
    
    def test_preprocess_whitespace_normalization(self, preprocessor):
        """Test whitespace normalization"""
        query = "Show   me    revenue   for   this    year"
        processed = preprocessor.preprocess(query)
        
        assert "  " not in processed
        assert processed == "show me revenue for this year"
    
    def test_preprocess_punctuation_cleanup(self, preprocessor):
        """Test punctuation cleanup"""
        query = "Show me revenue!!! What's the profit???"
        processed = preprocessor.preprocess(query)
        
        # Should normalize the query to lowercase and clean up
        assert processed.lower() == processed  # Should be lowercase
        assert "whats" in processed  # Apostrophe should be removed


class TestQueryParser:
    """Test cases for QueryParser"""
    
    @pytest.fixture
    def mock_kimi_client(self):
        """Create a mock KimiClient"""
        return MagicMock(spec=KimiClient)
    
    @pytest.fixture
    def query_parser(self, mock_kimi_client):
        """Create a QueryParser instance with mock client"""
        return QueryParser(mock_kimi_client)
    
    @pytest.fixture
    def sample_intent_data(self):
        """Sample intent data from KIMI"""
        return {
            "metric_type": "revenue",
            "time_period": "this_year",
            "aggregation_level": "quarterly",
            "filters": {},
            "comparison_periods": ["last_year"],
            "visualization_hint": "line_chart",
            "confidence_score": 0.9
        }
    
    @pytest.fixture
    def sample_entities_data(self):
        """Sample entities data from KIMI"""
        return [
            {
                "entity_type": "metric",
                "entity_value": "revenue",
                "confidence_score": 0.9,
                "synonyms": ["sales", "income"],
                "original_text": "revenue"
            },
            {
                "entity_type": "time_period",
                "entity_value": "this_year",
                "confidence_score": 0.85,
                "synonyms": ["current year"],
                "original_text": "this year"
            }
        ]
    
    @pytest.fixture
    def sample_ambiguities_data(self):
        """Sample ambiguities data from KIMI"""
        return [
            {
                "ambiguity_type": "metric_type",
                "description": "Performance metric not specified",
                "possible_interpretations": ["revenue", "profit", "cash_flow"],
                "confidence_score": 0.8,
                "suggested_clarification": "Which performance metric?"
            }
        ]
    
    @pytest.mark.asyncio
    async def test_parse_query_success(
        self, 
        query_parser, 
        mock_kimi_client,
        sample_intent_data,
        sample_entities_data,
        sample_ambiguities_data
    ):
        """Test successful query parsing"""
        # Setup mock responses
        mock_kimi_client.extract_financial_intent = AsyncMock(return_value=sample_intent_data)
        mock_kimi_client.extract_financial_entities = AsyncMock(return_value=sample_entities_data)
        mock_kimi_client.detect_ambiguities = AsyncMock(return_value=sample_ambiguities_data)
        
        result = await query_parser.parse_query(
            query="Show me revenue for this year",
            user_id="user123",
            session_id="session456"
        )
        
        assert result.success is True
        assert result.query_context is not None
        assert result.processing_time_ms > 0
        
        context = result.query_context
        assert context.user_id == "user123"
        assert context.session_id == "session456"
        assert context.original_query == "Show me revenue for this year"
        assert context.intent is not None
        assert context.intent.metric_type == "revenue"
        assert context.intent.time_period == "this_year"
        assert len(context.entities) == 2
        assert len(context.ambiguities) == 1
    
    @pytest.mark.asyncio
    async def test_parse_query_kimi_error(self, query_parser, mock_kimi_client):
        """Test query parsing with KIMI API error"""
        from src.kimi_client import KimiAPIError
        
        mock_kimi_client.extract_financial_intent = AsyncMock(
            side_effect=KimiAPIError("API error")
        )
        
        result = await query_parser.parse_query(
            query="Show me revenue",
            user_id="user123", 
            session_id="session456"
        )
        
        assert result.success is False
        assert "KIMI API error" in result.error_message
        assert result.query_context is None
    
    @pytest.mark.asyncio
    async def test_parse_query_invalid_entity_data(
        self,
        query_parser,
        mock_kimi_client,
        sample_intent_data
    ):
        """Test parsing with invalid entity data"""
        # Setup mock responses with invalid entity data
        mock_kimi_client.extract_financial_intent = AsyncMock(return_value=sample_intent_data)
        mock_kimi_client.extract_financial_entities = AsyncMock(return_value=[
            {"invalid": "data"},  # Missing required fields
            {
                "entity_type": "metric",
                "entity_value": "revenue",
                "confidence_score": 0.9,
                "synonyms": ["sales"],
                "original_text": "revenue"
            }
        ])
        mock_kimi_client.detect_ambiguities = AsyncMock(return_value=[])
        
        result = await query_parser.parse_query(
            query="Show me revenue",
            user_id="user123",
            session_id="session456"
        )
        
        assert result.success is True
        # Should have only 1 valid entity (invalid one filtered out)
        assert len(result.query_context.entities) == 1
    
    def test_create_query_intent_valid_data(self, query_parser, sample_intent_data):
        """Test creating QueryIntent from valid data"""
        intent = query_parser._create_query_intent(sample_intent_data)
        
        assert isinstance(intent, QueryIntent)
        assert intent.metric_type == "revenue"
        assert intent.time_period == "this_year"
        assert intent.confidence_score == 0.9
    
    def test_create_query_intent_missing_data(self, query_parser):
        """Test creating QueryIntent from incomplete data"""
        incomplete_data = {"metric_type": "revenue"}  # Missing time_period
        
        intent = query_parser._create_query_intent(incomplete_data)
        
        assert isinstance(intent, QueryIntent)
        assert intent.metric_type == "revenue"
        assert intent.time_period == "unknown"  # Default value
    
    def test_create_query_intent_invalid_data(self, query_parser):
        """Test creating QueryIntent from invalid data"""
        invalid_data = {"invalid": "data"}
        
        intent = query_parser._create_query_intent(invalid_data)
        
        assert isinstance(intent, QueryIntent)
        assert intent.metric_type == "unknown"
        assert intent.time_period == "unknown"
        assert intent.confidence_score == 0.0
    
    @pytest.mark.asyncio
    async def test_validate_query_context_success(self, query_parser):
        """Test validation of successful query context"""
        context = QueryContext(
            user_id="user123",
            session_id="session456",
            query_id="query789",
            original_query="Show me revenue",
            processed_query="show me revenue",
            intent=QueryIntent(
                metric_type="revenue",
                time_period="this_year",
                confidence_score=0.9
            ),
            entities=[
                FinancialEntity(
                    entity_type="metric",
                    entity_value="revenue",
                    confidence_score=0.9,
                    original_text="revenue"
                )
            ]
        )
        
        issues = await query_parser.validate_query_context(context)
        assert len(issues) == 0
    
    @pytest.mark.asyncio
    async def test_validate_query_context_issues(self, query_parser):
        """Test validation with various issues"""
        context = QueryContext(
            user_id="user123",
            session_id="session456", 
            query_id="query789",
            original_query="Show me something",
            processed_query="show me something",
            intent=QueryIntent(
                metric_type="unknown",
                time_period="unknown",
                confidence_score=0.3
            ),
            entities=[],
            ambiguities=["unclear metric"]
        )
        
        issues = await query_parser.validate_query_context(context)
        
        assert len(issues) > 0
        assert any("Low confidence" in issue for issue in issues)
        assert any("unknown" in issue.lower() for issue in issues)
        assert any("ambiguities" in issue for issue in issues)
        assert any("No financial entities" in issue for issue in issues)
    
    @pytest.mark.asyncio
    async def test_suggest_query_improvements(self, query_parser):
        """Test query improvement suggestions"""
        context = QueryContext(
            user_id="user123",
            session_id="session456",
            query_id="query789", 
            original_query="Show me performance",
            processed_query="show me performance",
            intent=QueryIntent(
                metric_type="unknown",
                time_period="unknown",
                confidence_score=0.5
            ),
            clarifications=["Which metric?", "Which time period?"]
        )
        
        suggestions = await query_parser.suggest_query_improvements(context)
        
        assert len(suggestions) > 0
        assert any("metric" in suggestion.lower() for suggestion in suggestions)
        assert any("time period" in suggestion.lower() for suggestion in suggestions)