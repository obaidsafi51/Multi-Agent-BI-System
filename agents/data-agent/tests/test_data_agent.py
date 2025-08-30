"""
Unit tests for Data Agent integration.
Tests the main Data Agent service with mocked dependencies.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.agent import DataAgent


class TestDataAgent:
    """Test cases for DataAgent class."""
    
    @pytest.fixture
    async def mock_data_agent(self):
        """Create a DataAgent with mocked dependencies."""
        agent = DataAgent()
        
        # Mock all dependencies
        agent.connection_manager = AsyncMock()
        agent.query_generator = MagicMock()
        agent.data_validator = MagicMock()
        agent.cache_manager = AsyncMock()
        agent.query_optimizer = MagicMock()
        agent.is_initialized = True
        
        return agent
    
    @pytest.mark.asyncio
    async def test_process_query_success(self, mock_data_agent):
        """Test successful query processing."""
        # Setup mocks
        mock_data_agent.cache_manager.get.return_value = None  # Cache miss
        
        mock_data_agent.query_generator.generate_query.return_value = MagicMock(
            sql="SELECT * FROM financial_overview",
            params={'start_date': '2024-01-01', 'end_date': '2024-12-31'}
        )
        
        mock_data_agent.query_optimizer.optimize_query.return_value = MagicMock(
            optimized_query="SELECT * FROM financial_overview USE INDEX (idx_period_date)",
            applied_optimizations=['index_hint'],
            estimated_cost=100.0,
            optimization_confidence=0.8
        )
        
        mock_data_agent.connection_manager.execute_query.return_value = {
            'data': [
                {'period_date': '2024-01-01', 'revenue': 1000000.00},
                {'period_date': '2024-02-01', 'revenue': 1200000.00}
            ],
            'columns': ['period_date', 'revenue'],
            'row_count': 2,
            'execution_time_ms': 150
        }
        
        mock_data_agent.data_validator.validate_query_result.return_value = MagicMock(
            is_valid=True,
            quality_score=0.95,
            issues=[],
            warnings=[]
        )
        
        # Test query processing
        query_intent = {
            'metric_type': 'revenue',
            'time_period': 'this year',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        }
        
        result = await mock_data_agent.process_query(query_intent)
        
        # Verify result
        assert result['success'] is True
        assert len(result['data']) == 2
        assert result['row_count'] == 2
        assert 'metadata' in result
        assert result['metadata']['data_quality']['is_valid'] is True
        assert result['metadata']['cache_hit'] is False
    
    @pytest.mark.asyncio
    async def test_process_query_cache_hit(self, mock_data_agent):
        """Test query processing with cache hit."""
        # Setup cache hit
        cached_result = {
            'query_id': 'cached_query',
            'success': True,
            'data': [{'period_date': '2024-01-01', 'revenue': 1000000.00}],
            'metadata': {'cache_hit': False}
        }
        
        mock_data_agent.cache_manager.get.return_value = cached_result
        
        query_intent = {
            'metric_type': 'revenue',
            'time_period': 'this year',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        }
        
        result = await mock_data_agent.process_query(query_intent)
        
        # Verify cache hit
        assert result['success'] is True
        assert result['metadata']['cache_hit'] is True
        assert mock_data_agent.metrics['cache_hits'] == 1
        
        # Verify that database query was not executed
        mock_data_agent.connection_manager.execute_query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_query_validation_failure(self, mock_data_agent):
        """Test query processing with validation failure."""
        # Setup mocks for validation failure
        mock_data_agent.cache_manager.get.return_value = None
        
        mock_data_agent.query_generator.generate_query.return_value = MagicMock(
            sql="SELECT * FROM financial_overview",
            params={}
        )
        
        mock_data_agent.query_optimizer.optimize_query.return_value = MagicMock(
            optimized_query="SELECT * FROM financial_overview",
            applied_optimizations=[],
            estimated_cost=100.0,
            optimization_confidence=0.5
        )
        
        mock_data_agent.connection_manager.execute_query.return_value = {
            'data': [{'period_date': 'invalid-date', 'revenue': 'invalid'}],
            'columns': ['period_date', 'revenue'],
            'row_count': 1,
            'execution_time_ms': 50
        }
        
        mock_data_agent.data_validator.validate_query_result.return_value = MagicMock(
            is_valid=False,
            quality_score=0.2,
            issues=['Invalid data format'],
            warnings=[]
        )
        
        query_intent = {
            'metric_type': 'revenue',
            'time_period': 'this year',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        }
        
        result = await mock_data_agent.process_query(query_intent)
        
        # Should still return result but with validation issues
        assert result['success'] is True
        assert result['metadata']['data_quality']['is_valid'] is False
        assert len(result['metadata']['data_quality']['issues']) > 0
        
        # Should not cache invalid results
        mock_data_agent.cache_manager.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_query_database_error(self, mock_data_agent):
        """Test query processing with database error."""
        # Setup mocks
        mock_data_agent.cache_manager.get.return_value = None
        
        mock_data_agent.query_generator.generate_query.return_value = MagicMock(
            sql="SELECT * FROM financial_overview",
            params={}
        )
        
        mock_data_agent.query_optimizer.optimize_query.return_value = MagicMock(
            optimized_query="SELECT * FROM financial_overview",
            applied_optimizations=[],
            estimated_cost=100.0,
            optimization_confidence=0.5
        )
        
        # Simulate database error
        mock_data_agent.connection_manager.execute_query.side_effect = Exception("Database connection failed")
        
        query_intent = {
            'metric_type': 'revenue',
            'time_period': 'this year',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        }
        
        result = await mock_data_agent.process_query(query_intent)
        
        # Should return error response
        assert result['success'] is False
        assert 'error' in result
        assert result['error']['type'] == 'processing_error'
        assert mock_data_agent.metrics['errors'] == 1
    
    @pytest.mark.asyncio
    async def test_get_data_summary(self, mock_data_agent):
        """Test getting data summary for a table."""
        mock_data_agent.connection_manager.execute_query.return_value = {
            'data': [{
                'total_records': 1000,
                'earliest_date': '2023-01-01',
                'latest_date': '2024-12-31',
                'unique_periods': 24
            }],
            'execution_time_ms': 50
        }
        
        result = await mock_data_agent.get_data_summary('financial_overview')
        
        assert result['table_name'] == 'financial_overview'
        assert 'summary' in result
        assert result['summary']['total_records'] == 1000
        assert 'metadata' in result
    
    @pytest.mark.asyncio
    async def test_get_data_summary_with_date_range(self, mock_data_agent):
        """Test getting data summary with date range filter."""
        mock_data_agent.connection_manager.execute_query.return_value = {
            'data': [{
                'total_records': 100,
                'earliest_date': '2024-01-01',
                'latest_date': '2024-12-31',
                'unique_periods': 12
            }],
            'execution_time_ms': 30
        }
        
        date_range = {'start_date': '2024-01-01', 'end_date': '2024-12-31'}
        result = await mock_data_agent.get_data_summary('financial_overview', date_range)
        
        assert result['summary']['total_records'] == 100
        
        # Verify that date range was used in query
        call_args = mock_data_agent.connection_manager.execute_query.call_args
        assert 'WHERE period_date BETWEEN' in call_args[0][0]
        assert call_args[0][1] == date_range
    
    @pytest.mark.asyncio
    async def test_invalidate_cache(self, mock_data_agent):
        """Test cache invalidation."""
        mock_data_agent.cache_manager.invalidate_by_tags.return_value = 5
        
        result = await mock_data_agent.invalidate_cache(['metric:revenue', 'table:financial_overview'])
        
        assert result == 5
        mock_data_agent.cache_manager.invalidate_by_tags.assert_called_once_with(['metric:revenue', 'table:financial_overview'])
    
    @pytest.mark.asyncio
    async def test_invalidate_all_cache(self, mock_data_agent):
        """Test clearing all cache."""
        mock_data_agent.cache_manager.clear_all.return_value = None
        
        result = await mock_data_agent.invalidate_cache()
        
        assert result == -1  # Indicates full clear
        mock_data_agent.cache_manager.clear_all.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_data_agent):
        """Test health check with all components healthy."""
        mock_data_agent.connection_manager.health_check.return_value = {
            'status': 'healthy',
            'connection_stats': {}
        }
        
        mock_data_agent.cache_manager.health_check.return_value = {
            'status': 'healthy',
            'stats': {}
        }
        
        mock_data_agent.query_optimizer.get_optimization_stats.return_value = {
            'queries_optimized': 10
        }
        
        result = await mock_data_agent.health_check()
        
        assert result['status'] == 'healthy'
        assert 'components' in result
        assert 'database' in result['components']
        assert 'cache' in result['components']
        assert 'optimizer' in result['components']
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, mock_data_agent):
        """Test health check with degraded components."""
        mock_data_agent.connection_manager.health_check.return_value = {
            'status': 'degraded',
            'connection_stats': {}
        }
        
        mock_data_agent.cache_manager.health_check.return_value = {
            'status': 'healthy',
            'stats': {}
        }
        
        result = await mock_data_agent.health_check()
        
        assert result['status'] == 'degraded'
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, mock_data_agent):
        """Test getting performance metrics."""
        mock_data_agent.cache_manager.get_stats.return_value = MagicMock(
            hit_rate=75.0,
            total_requests=100,
            entry_count=50,
            total_size_bytes=1024000
        )
        
        mock_data_agent.query_optimizer.get_optimization_stats.return_value = {
            'queries_optimized': 25,
            'avg_improvement': 0.3
        }
        
        result = await mock_data_agent.get_metrics()
        
        assert 'queries_processed' in result
        assert 'cache_hits' in result
        assert 'cache_misses' in result
        assert 'cache' in result
        assert 'optimizer' in result
        assert result['cache']['hit_rate'] == 75.0
    
    def test_generate_cache_key(self, mock_data_agent):
        """Test cache key generation."""
        query_intent = {
            'metric_type': 'revenue',
            'time_period': 'this year',
            'aggregation_level': 'monthly',
            'filters': {'department': 'sales'},
            'comparison_periods': ['last year']
        }
        
        cache_key = mock_data_agent._generate_cache_key(query_intent)
        
        assert isinstance(cache_key, str)
        assert len(cache_key) > 0
        
        # Same intent should generate same key
        cache_key2 = mock_data_agent._generate_cache_key(query_intent)
        assert cache_key == cache_key2
    
    def test_generate_cache_tags(self, mock_data_agent):
        """Test cache tag generation."""
        query_intent = {
            'metric_type': 'revenue',
            'time_period': 'Q1 2024',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        }
        
        tags = mock_data_agent._generate_cache_tags(query_intent)
        
        assert isinstance(tags, list)
        assert 'metric:revenue' in tags
        assert 'table:financial_overview' in tags
        assert 'period:Q1 2024' in tags
    
    @pytest.mark.asyncio
    async def test_uninitialized_agent_error(self):
        """Test that uninitialized agent raises error."""
        agent = DataAgent()
        # Don't initialize
        
        query_intent = {
            'metric_type': 'revenue',
            'time_period': 'this year',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        }
        
        with pytest.raises(RuntimeError, match="Data Agent not initialized"):
            await agent.process_query(query_intent)
    
    def test_metrics_update_success(self, mock_data_agent):
        """Test metrics update for successful query."""
        initial_queries = mock_data_agent.metrics['queries_processed']
        initial_avg_time = mock_data_agent.metrics['avg_query_time']
        
        mock_data_agent._update_metrics(0.5, success=True)
        
        assert mock_data_agent.metrics['queries_processed'] == initial_queries + 1
        assert mock_data_agent.metrics['avg_query_time'] > initial_avg_time
        assert mock_data_agent.metrics['errors'] == 0
    
    def test_metrics_update_failure(self, mock_data_agent):
        """Test metrics update for failed query."""
        initial_errors = mock_data_agent.metrics['errors']
        
        mock_data_agent._update_metrics(0.5, success=False)
        
        assert mock_data_agent.metrics['errors'] == initial_errors + 1