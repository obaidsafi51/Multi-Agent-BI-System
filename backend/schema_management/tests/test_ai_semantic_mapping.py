"""
Unit tests for AI-Enhanced Semantic Mapping with KIMI integration.

This module provides comprehensive tests for the AI semantic mapping
functionality including KIMI API integration, fallback mechanisms,
and performance validation.
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, List, Any

# Import the modules under test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ai_semantic_mapper import (
    AISemanticSchemaMapper,
    KIMIAPIClient,
    AISemanticMapping,
    KIMIResponse
)
from user_feedback_system import (
    UserFeedbackSystem,
    FeedbackType,
    MappingQuality,
    UserFeedback
)
from query_success_analysis import (
    QuerySuccessPatternAnalysis,
    QueryExecutionStatus,
    QueryComplexity
)
from config import MCPSchemaConfig


class TestKIMIAPIClient:
    """Test cases for KIMI API client."""
    
    @pytest.fixture
    def kimi_client(self):
        """Create KIMI client for testing."""
        config = {
            'model': 'moonshot-v1-8k',
            'temperature': 0.1,
            'max_tokens': 1000,
            'rate_limit_per_hour': 50,
            'rate_limit_per_day': 200
        }
        return KIMIAPIClient('test_api_key', config)
    
    @pytest.mark.asyncio
    async def test_rate_limit_checking(self, kimi_client):
        """Test rate limiting functionality."""
        # Initially should be within limits
        assert await kimi_client.check_rate_limit() == True
        
        # Simulate hitting hourly limit
        now = datetime.now()
        hour_key = f"kimi_{now.strftime('%Y%m%d%H')}"
        kimi_client.api_usage_tracker[hour_key] = 50
        
        assert await kimi_client.check_rate_limit() == False
    
    def test_increment_usage(self, kimi_client):
        """Test usage counter increment."""
        initial_count = len(kimi_client.api_usage_tracker)
        kimi_client.increment_usage()
        
        assert len(kimi_client.api_usage_tracker) >= initial_count
        
        # Check that both hour and day keys are created
        now = datetime.now()
        hour_key = f"kimi_{now.strftime('%Y%m%d%H')}"
        day_key = f"kimi_{now.strftime('%Y%m%d')}"
        
        assert hour_key in kimi_client.api_usage_tracker
        assert day_key in kimi_client.api_usage_tracker
    
    def test_system_prompt_generation(self, kimi_client):
        """Test system prompt generation."""
        prompt = kimi_client.get_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert 'database schema analyst' in prompt.lower()
        assert 'confidence scores' in prompt.lower()
    
    def test_mapping_prompt_building(self, kimi_client):
        """Test mapping prompt construction."""
        schema_elements = [
            {
                'table_name': 'sales',
                'column_name': 'revenue',
                'description': 'Total revenue amount'
            },
            {
                'table_name': 'customers',
                'column_name': 'customer_id',
                'description': 'Unique customer identifier'
            }
        ]
        
        prompt = kimi_client.build_mapping_prompt(
            'total sales',
            schema_elements,
            'Monthly revenue report'
        )
        
        assert 'total sales' in prompt
        assert 'sales.revenue' in prompt
        assert 'customers.customer_id' in prompt
        assert 'Monthly revenue report' in prompt
        assert 'JSON' in prompt
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_successful_api_request(self, mock_post, kimi_client):
        """Test successful KIMI API request."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'mappings': [{
                            'table_name': 'sales',
                            'column_name': 'revenue',
                            'confidence_score': 0.95,
                            'mapping_type': 'exact',
                            'explanation': 'Direct match for revenue data'
                        }]
                    })
                }
            }],
            'usage': {'total_tokens': 150}
        }
        
        mock_post.return_value.__aenter__.return_value = mock_response
        
        schema_elements = [
            {'table_name': 'sales', 'column_name': 'revenue', 'description': 'Revenue amount'}
        ]
        
        response = await kimi_client.semantic_mapping_request(
            'total sales',
            schema_elements
        )
        
        assert isinstance(response, KIMIResponse)
        assert len(response.mappings) == 1
        assert response.mappings[0]['table_name'] == 'sales'
        assert response.mappings[0]['confidence_score'] == 0.95
        assert response.total_tokens == 150
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_api_error_handling(self, mock_post, kimi_client):
        """Test API error handling."""
        # Mock error response
        mock_response = AsyncMock()
        mock_response.status = 429  # Rate limit error
        mock_response.text.return_value = 'Rate limit exceeded'
        
        mock_post.return_value.__aenter__.return_value = mock_response
        
        schema_elements = [
            {'table_name': 'sales', 'column_name': 'revenue', 'description': 'Revenue amount'}
        ]
        
        with pytest.raises(Exception) as excinfo:
            await kimi_client.semantic_mapping_request('total sales', schema_elements)
        
        assert 'KIMI API error 429' in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_rate_limit_prevention(self, kimi_client):
        """Test that rate limit checking prevents API calls."""
        # Set usage to exceed limit
        now = datetime.now()
        hour_key = f"kimi_{now.strftime('%Y%m%d%H')}"
        kimi_client.api_usage_tracker[hour_key] = 51  # Over limit
        
        schema_elements = [
            {'table_name': 'sales', 'column_name': 'revenue', 'description': 'Revenue amount'}
        ]
        
        with pytest.raises(Exception) as excinfo:
            await kimi_client.semantic_mapping_request('total sales', schema_elements)
        
        assert 'rate limit exceeded' in str(excinfo.value).lower()


class TestAISemanticSchemaMapper:
    """Test cases for AI-enhanced semantic schema mapper."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=MCPSchemaConfig)
        config.semantic_mapping = {
            'ai_config': {
                'enabled': True,
                'confidence_threshold': 0.7,
                'fallback_to_fuzzy': True,
                'fuzzy_threshold': 0.8,
                'max_suggestions': 5,
                'cache_ttl_hours': 24,
                'kimi': {
                    'model': 'moonshot-v1-8k',
                    'temperature': 0.1,
                    'rate_limit_per_hour': 50
                }
            }
        }
        return config
    
    @pytest.fixture
    def ai_mapper(self, mock_config):
        """Create AI semantic mapper for testing."""
        with patch.dict(os.environ, {'KIMI_API_KEY': 'test_key'}):
            return AISemanticSchemaMapper(mock_config)
    
    def test_initialization(self, ai_mapper):
        """Test mapper initialization."""
        assert ai_mapper.use_ai_for_mapping == True
        assert ai_mapper.ai_confidence_threshold == 0.7
        assert ai_mapper.fallback_to_fuzzy == True
        assert ai_mapper.kimi_client is not None
    
    def test_initialization_without_api_key(self, mock_config):
        """Test initialization without KIMI API key."""
        with patch.dict(os.environ, {}, clear=True):
            mapper = AISemanticSchemaMapper(mock_config)
            assert mapper.kimi_client is None
            assert mapper.use_ai_for_mapping == False
    
    def test_cache_key_generation(self, ai_mapper):
        """Test cache key generation."""
        schema_elements = [
            {'table_name': 'sales', 'column_name': 'revenue'}
        ]
        
        key1 = ai_mapper.generate_cache_key('revenue', schema_elements)
        key2 = ai_mapper.generate_cache_key('revenue', schema_elements)
        key3 = ai_mapper.generate_cache_key('sales', schema_elements)
        
        assert key1 == key2  # Same inputs should generate same key
        assert key1 != key3  # Different inputs should generate different keys
        assert len(key1) == 32  # MD5 hash length
    
    def test_cache_validity_checking(self, ai_mapper):
        """Test cache validity checking."""
        # Valid cache entry
        valid_entry = {
            'timestamp': datetime.now() - timedelta(hours=1),
            'mappings': []
        }
        assert ai_mapper.is_cache_valid(valid_entry) == True
        
        # Expired cache entry
        expired_entry = {
            'timestamp': datetime.now() - timedelta(hours=25),
            'mappings': []
        }
        assert ai_mapper.is_cache_valid(expired_entry) == False
        
        # Invalid cache entry (no timestamp)
        invalid_entry = {'mappings': []}
        assert ai_mapper.is_cache_valid(invalid_entry) == False
    
    @pytest.mark.asyncio
    async def test_fallback_fuzzy_mapping(self, ai_mapper):
        """Test fallback fuzzy matching."""
        schema_elements = [
            {'table_name': 'sales_data', 'column_name': 'total_revenue'},
            {'table_name': 'customer_info', 'column_name': 'customer_name'},
            {'table_name': 'sales_data', 'column_name': 'sales_amount'}
        ]
        
        mappings = await ai_mapper._fallback_fuzzy_mapping('sales', schema_elements)
        
        assert len(mappings) > 0
        
        # Should find sales-related mappings
        sales_mappings = [m for m in mappings if 'sales' in m.schema_element_path.lower()]
        assert len(sales_mappings) > 0
        
        # Check mapping properties
        for mapping in mappings:
            assert isinstance(mapping, AISemanticMapping)
            assert mapping.source_api == 'fallback'
            assert mapping.similarity_type == 'fuzzy'
            assert 0.0 <= mapping.confidence_score <= 1.0
    
    @pytest.mark.asyncio
    @patch('backend.schema_management.ai_semantic_mapper.KIMIAPIClient.semantic_mapping_request')
    async def test_kimi_mapping_success(self, mock_kimi_request, ai_mapper):
        """Test successful KIMI mapping."""
        # Mock KIMI response
        mock_response = KIMIResponse(
            mappings=[
                {
                    'table_name': 'sales',
                    'column_name': 'revenue',
                    'confidence_score': 0.95,
                    'mapping_type': 'exact',
                    'explanation': 'Direct revenue mapping'
                }
            ],
            total_tokens=120,
            processing_time_ms=800,
            confidence_scores=[0.95]
        )
        mock_kimi_request.return_value = mock_response
        
        schema_elements = [
            {'table_name': 'sales', 'column_name': 'revenue', 'description': 'Revenue data'}
        ]
        
        mappings = await ai_mapper.map_business_term_ai('revenue', schema_elements)
        
        assert len(mappings) == 1
        assert mappings[0].source_api == 'kimi'
        assert mappings[0].confidence_score == 0.95
        assert mappings[0].ai_explanation == 'Direct revenue mapping'
        assert mappings[0].cost_tokens == 120
    
    @pytest.mark.asyncio
    @patch('backend.schema_management.ai_semantic_mapper.KIMIAPIClient.semantic_mapping_request')
    async def test_kimi_mapping_with_fallback(self, mock_kimi_request, ai_mapper):
        """Test KIMI mapping failure with fallback."""
        # Mock KIMI failure
        mock_kimi_request.side_effect = Exception("API error")
        
        schema_elements = [
            {'table_name': 'sales_data', 'column_name': 'revenue_amount'}
        ]
        
        mappings = await ai_mapper.map_business_term_ai('revenue', schema_elements)
        
        # Should fallback to fuzzy matching
        assert len(mappings) > 0
        assert mappings[0].source_api == 'fallback'
        assert mappings[0].similarity_type == 'fuzzy'
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self, ai_mapper):
        """Test mapping result caching."""
        schema_elements = [
            {'table_name': 'sales', 'column_name': 'revenue'}
        ]
        
        # First call should populate cache
        with patch.object(ai_mapper, '_fallback_fuzzy_mapping') as mock_fallback:
            mock_fallback.return_value = [
                AISemanticMapping(
                    business_term='revenue',
                    schema_element_type='column',
                    schema_element_path='sales.revenue',
                    confidence_score=0.8,
                    similarity_type='fuzzy',
                    context_match=False,
                    metadata={},
                    created_at=datetime.now(),
                    ai_explanation='Test mapping',
                    source_api='fallback'
                )
            ]
            
            mappings1 = await ai_mapper.map_business_term_ai('revenue', schema_elements)
            assert mock_fallback.called
        
        # Second call should use cache
        with patch.object(ai_mapper, '_fallback_fuzzy_mapping') as mock_fallback:
            mappings2 = await ai_mapper.map_business_term_ai('revenue', schema_elements)
            assert not mock_fallback.called  # Should not be called due to cache
        
        assert len(mappings1) == len(mappings2)


class TestUserFeedbackSystem:
    """Test cases for user feedback system."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=MCPSchemaConfig)
        config.semantic_mapping = {
            'user_feedback': {
                'max_storage_size': 1000,
                'learning_config': {
                    'min_feedback_threshold': 5,
                    'confidence_adjustment_factor': 0.1,
                    'learning_rate': 0.05
                }
            }
        }
        return config
    
    @pytest.fixture
    def feedback_system(self, mock_config):
        """Create feedback system for testing."""
        return UserFeedbackSystem(mock_config)
    
    @pytest.mark.asyncio
    async def test_feedback_submission(self, feedback_system):
        """Test feedback submission."""
        feedback_id = await feedback_system.submit_feedback(
            user_id='user1',
            session_id='session1',
            business_term='revenue',
            suggested_mapping='sales.revenue',
            feedback_type=FeedbackType.POSITIVE,
            quality_rating=MappingQuality.EXCELLENT,
            ai_confidence=0.9,
            user_confidence=1.0
        )
        
        assert feedback_id.startswith('fb_')
        assert len(feedback_system.feedback_queue) == 1
    
    @pytest.mark.asyncio
    async def test_feedback_processing(self, feedback_system):
        """Test feedback processing."""
        await feedback_system.start()
        
        # Submit feedback
        await feedback_system.submit_feedback(
            user_id='user1',
            session_id='session1',
            business_term='revenue',
            suggested_mapping='sales.revenue',
            feedback_type=FeedbackType.POSITIVE,
            quality_rating=MappingQuality.GOOD
        )
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Check that feedback was processed
        assert len(feedback_system.feedback_storage) == 1
        assert len(feedback_system.feedback_queue) == 0
        
        await feedback_system.stop()
    
    def test_confidence_boost_calculation(self, feedback_system):
        """Test confidence boost from learned patterns."""
        # Add some feedback to learning engine
        feedback_system.learning_engine.term_success_rates['revenue'] = 0.9
        
        boost = feedback_system.get_mapping_confidence_boost('revenue', 'sales.revenue')
        assert boost > 0
        assert boost <= 0.25  # Should be capped at 25%
    
    def test_learned_mappings_retrieval(self, feedback_system):
        """Test retrieval of learned mappings."""
        # Add correction to learning engine
        from user_feedback_system import MappingCorrection
        correction = MappingCorrection(
            feedback_id='test',
            original_table='old_table',
            original_column='old_column',
            corrected_table='sales',
            corrected_column='revenue',
            reason='Better mapping'
        )
        feedback_system.learning_engine.mapping_corrections['revenue'].append(correction)
        
        suggestions = feedback_system.get_learned_mappings('revenue')
        assert 'sales.revenue' in suggestions
    
    def test_analytics_calculation(self, feedback_system):
        """Test feedback analytics calculation."""
        # Add sample feedback
        sample_feedback = [
            UserFeedback(
                id='fb1',
                user_id='user1',
                session_id='session1',
                timestamp=datetime.now(),
                feedback_type=FeedbackType.POSITIVE,
                mapping_id='map1',
                business_term='revenue',
                suggested_mapping='sales.revenue',
                quality_rating=MappingQuality.EXCELLENT
            ),
            UserFeedback(
                id='fb2',
                user_id='user2',
                session_id='session2',
                timestamp=datetime.now(),
                feedback_type=FeedbackType.NEGATIVE,
                mapping_id='map2',
                business_term='profit',
                suggested_mapping='finance.profit',
                quality_rating=MappingQuality.POOR
            )
        ]
        
        feedback_system.feedback_storage.extend(sample_feedback)
        
        analytics = feedback_system.get_feedback_analytics()
        
        assert analytics.total_feedback_count == 2
        assert analytics.positive_feedback_rate == 50.0  # 1 positive out of 2
        assert analytics.average_quality_rating == 3.0  # (5 + 1) / 2
        assert analytics.user_satisfaction_score > 0


class TestQuerySuccessPatternAnalysis:
    """Test cases for query success pattern analysis."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=MCPSchemaConfig)
        config.semantic_mapping = {
            'pattern_analysis': {
                'max_records': 1000,
                'analyzer_config': {
                    'min_pattern_threshold': 5,
                    'success_rate_threshold': 0.8,
                    'confidence_buckets': [0.5, 0.7, 0.8, 0.9]
                }
            }
        }
        return config
    
    @pytest.fixture
    def pattern_analysis(self, mock_config):
        """Create pattern analysis for testing."""
        return QuerySuccessPatternAnalysis(mock_config)
    
    @pytest.mark.asyncio
    async def test_query_execution_recording(self, pattern_analysis):
        """Test query execution recording."""
        record_id = await pattern_analysis.record_query_execution(
            user_id='user1',
            session_id='session1',
            business_query='Show me total revenue',
            generated_sql='SELECT SUM(revenue) FROM sales',
            execution_status=QueryExecutionStatus.SUCCESS,
            execution_time_ms=500,
            rows_returned=1,
            mapped_terms=['revenue'],
            used_mappings=[{'table_name': 'sales', 'column_name': 'revenue'}],
            ai_confidence_scores=[0.9],
            query_intent='aggregation'
        )
        
        assert record_id.startswith('qe_')
        assert len(pattern_analysis.execution_records) == 1
    
    def test_query_complexity_analysis(self, pattern_analysis):
        """Test query complexity analysis."""
        # Simple query
        simple_sql = "SELECT * FROM sales"
        complexity = pattern_analysis._analyze_query_complexity(simple_sql)
        assert complexity == QueryComplexity.SIMPLE
        
        # Complex query
        complex_sql = """
        SELECT s.customer_id, SUM(s.revenue) as total,
               CASE WHEN SUM(s.revenue) > 1000 THEN 'High Value' ELSE 'Low Value' END
        FROM sales s
        JOIN customers c ON s.customer_id = c.id
        GROUP BY s.customer_id
        HAVING SUM(s.revenue) > 100
        """
        complexity = pattern_analysis._analyze_query_complexity(complex_sql)
        assert complexity in [QueryComplexity.COMPLEX, QueryComplexity.VERY_COMPLEX]
    
    def test_confidence_threshold_optimization(self, pattern_analysis):
        """Test optimal confidence threshold calculation."""
        # Add sample success patterns
        pattern_analysis.pattern_analyzer.confidence_success_rates[0.7] = [True, True, False, True, True]
        pattern_analysis.pattern_analyzer.confidence_success_rates[0.8] = [True, True, True, True, False]
        pattern_analysis.pattern_analyzer.confidence_success_rates[0.9] = [True, True, True, True, True]
        
        optimal_threshold = pattern_analysis.get_optimal_confidence_threshold()
        assert 0.5 <= optimal_threshold <= 1.0
    
    def test_success_analytics_calculation(self, pattern_analysis):
        """Test success analytics calculation."""
        # Add sample execution records
        from query_success_analysis import QueryExecutionRecord
        
        records = [
            QueryExecutionRecord(
                id='qe1',
                user_id='user1',
                session_id='session1',
                timestamp=datetime.now(),
                business_query='revenue',
                generated_sql='SELECT revenue FROM sales',
                execution_status=QueryExecutionStatus.SUCCESS,
                execution_time_ms=300,
                rows_returned=10,
                mapped_terms=['revenue'],
                used_mappings=[{'table_name': 'sales', 'column_name': 'revenue'}],
                ai_confidence_scores=[0.9]
            ),
            QueryExecutionRecord(
                id='qe2',
                user_id='user2',
                session_id='session2',
                timestamp=datetime.now(),
                business_query='profit',
                generated_sql='SELECT profit FROM finance',
                execution_status=QueryExecutionStatus.FAILURE,
                execution_time_ms=1000,
                rows_returned=0,
                error_message='Table not found',
                mapped_terms=['profit'],
                used_mappings=[{'table_name': 'finance', 'column_name': 'profit'}],
                ai_confidence_scores=[0.6]
            )
        ]
        
        pattern_analysis.execution_records.extend(records)
        
        analytics = pattern_analysis.get_success_analytics()
        
        assert analytics.total_queries == 2
        assert analytics.success_rate == 50.0  # 1 success out of 2
        assert analytics.avg_execution_time_ms == 650.0  # (300 + 1000) / 2


class TestIntegration:
    """Integration tests for AI semantic mapping components."""
    
    @pytest.fixture
    def integrated_system(self):
        """Create integrated system for testing."""
        config = Mock(spec=MCPSchemaConfig)
        config.semantic_mapping = {
            'ai_config': {
                'enabled': True,
                'confidence_threshold': 0.7,
                'fallback_to_fuzzy': True,
                'fuzzy_threshold': 0.8,
                'max_suggestions': 5,
                'cache_ttl_hours': 24,
                'kimi': {
                    'model': 'moonshot-v1-8k',
                    'temperature': 0.1,
                    'rate_limit_per_hour': 50
                }
            },
            'user_feedback': {
                'max_storage_size': 1000,
                'learning_config': {
                    'min_feedback_threshold': 5,
                    'confidence_adjustment_factor': 0.1,
                    'learning_rate': 0.05
                }
            },
            'pattern_analysis': {
                'max_records': 1000,
                'analyzer_config': {
                    'min_pattern_threshold': 5,
                    'success_rate_threshold': 0.8,
                    'confidence_buckets': [0.5, 0.7, 0.8, 0.9]
                }
            }
        }
        
        with patch.dict(os.environ, {}, clear=True):  # No KIMI API key for fallback testing
            mapper = AISemanticSchemaMapper(config)
            feedback_system = UserFeedbackSystem(config)
            pattern_analysis = QuerySuccessPatternAnalysis(config)
        
        return {
            'mapper': mapper,
            'feedback_system': feedback_system,
            'pattern_analysis': pattern_analysis
        }
    
    @pytest.mark.asyncio
    async def test_end_to_end_mapping_with_feedback(self, integrated_system):
        """Test end-to-end mapping with feedback integration."""
        mapper = integrated_system['mapper']
        feedback_system = integrated_system['feedback_system']
        pattern_analysis = integrated_system['pattern_analysis']
        
        await feedback_system.start()
        
        try:
            # 1. Perform semantic mapping
            schema_elements = [
                {'table_name': 'sales_data', 'column_name': 'total_revenue'}
            ]
            
            mappings = await mapper.map_business_term_ai('revenue', schema_elements)
            assert len(mappings) > 0
            
            # 2. Submit feedback
            feedback_id = await feedback_system.submit_feedback(
                user_id='user1',
                session_id='session1',
                business_term='revenue',
                suggested_mapping=mappings[0].schema_element_path,
                feedback_type=FeedbackType.POSITIVE,
                quality_rating=MappingQuality.GOOD,
                ai_confidence=mappings[0].confidence_score,
                user_confidence=0.9
            )
            
            # 3. Record query execution
            record_id = await pattern_analysis.record_query_execution(
                user_id='user1',
                session_id='session1',
                business_query='Show me revenue',
                generated_sql='SELECT total_revenue FROM sales_data',
                execution_status=QueryExecutionStatus.SUCCESS,
                execution_time_ms=400,
                rows_returned=5,
                mapped_terms=['revenue'],
                used_mappings=[{'table_name': 'sales_data', 'column_name': 'total_revenue'}],
                ai_confidence_scores=[mappings[0].confidence_score]
            )
            
            # Wait for feedback processing
            await asyncio.sleep(0.2)
            
            # 4. Verify integration
            assert feedback_id is not None
            assert record_id is not None
            assert len(feedback_system.feedback_storage) == 1
            assert len(pattern_analysis.execution_records) == 1
            
            # 5. Check learned improvements
            confidence_boost = feedback_system.get_mapping_confidence_boost(
                'revenue', 
                mappings[0].schema_element_path
            )
            assert confidence_boost >= 0
            
        finally:
            await feedback_system.stop()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
