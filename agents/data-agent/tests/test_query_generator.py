"""
Unit tests for SQL Query Generator.
Tests query generation from QueryIntent objects with various financial metrics.
"""

import pytest
from datetime import datetime
from src.query.generator import QueryGenerator, SQLQuery


class TestQueryGenerator:
    """Test cases for QueryGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = QueryGenerator()
    
    def test_revenue_query_generation(self):
        """Test generating SQL query for revenue metrics."""
        query_intent = {
            'metric_type': 'revenue',
            'time_period': 'this year',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        }
        
        result = self.generator.generate_query(query_intent)
        
        assert isinstance(result, SQLQuery)
        assert 'financial_overview' in result.sql
        assert 'revenue' in result.sql
        assert 'GROUP BY' in result.sql
        assert 'ORDER BY' in result.sql
        assert result.params is not None
    
    def test_cash_flow_query_generation(self):
        """Test generating SQL query for cash flow metrics."""
        query_intent = {
            'metric_type': 'cash_flow',
            'time_period': 'Q1 2024',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        }
        
        result = self.generator.generate_query(query_intent)
        
        assert 'cash_flow' in result.sql
        assert 'net_cash_flow' in result.sql
        assert '2024' in str(result.params)
    
    def test_budget_query_with_filters(self):
        """Test generating SQL query with department filters."""
        query_intent = {
            'metric_type': 'budget',
            'time_period': 'this month',
            'aggregation_level': 'daily',
            'filters': {'department': 'sales'},
            'comparison_periods': []
        }
        
        result = self.generator.generate_query(query_intent)
        
        assert 'budget_tracking' in result.sql
        assert 'department' in result.sql
        assert 'sales' in result.sql
    
    def test_quarterly_time_period_parsing(self):
        """Test parsing quarterly time periods."""
        query_intent = {
            'metric_type': 'revenue',
            'time_period': 'Q2 2024',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        }
        
        result = self.generator.generate_query(query_intent)
        
        # Q2 should be April-June (months 4-6)
        assert 'start_date' in result.params
        assert 'end_date' in result.params
        assert '2024-04-01' in str(result.params['start_date'])
        assert '2024-06-30' in str(result.params['end_date'])
    
    def test_comparison_periods(self):
        """Test generating queries with comparison periods."""
        query_intent = {
            'metric_type': 'revenue',
            'time_period': 'this year',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': ['last year']
        }
        
        result = self.generator.generate_query(query_intent)
        
        assert 'UNION ALL' in result.sql
        assert len(result.params) > 2  # Should have params for both periods
    
    def test_unknown_metric_type(self):
        """Test handling of unknown metric types."""
        query_intent = {
            'metric_type': 'unknown_metric',
            'time_period': 'this year',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        }
        
        with pytest.raises(ValueError, match="Unknown metric type"):
            self.generator.generate_query(query_intent)
    
    def test_investment_roi_query(self):
        """Test generating query for investment ROI."""
        query_intent = {
            'metric_type': 'roi',
            'time_period': 'this year',
            'aggregation_level': 'monthly',
            'filters': {'status': 'active'},
            'comparison_periods': []
        }
        
        result = self.generator.generate_query(query_intent)
        
        assert 'investments' in result.sql
        assert 'roi_percentage' in result.sql
        assert 'status' in result.sql
        assert 'active' in result.sql
    
    def test_financial_ratios_query(self):
        """Test generating query for financial ratios."""
        query_intent = {
            'metric_type': 'debt_to_equity',
            'time_period': 'last 6 months',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        }
        
        result = self.generator.generate_query(query_intent)
        
        assert 'financial_ratios' in result.sql
        assert 'debt_to_equity' in result.sql
    
    def test_query_optimization_hints(self):
        """Test that optimization hints are generated."""
        query_intent = {
            'metric_type': 'revenue',
            'time_period': 'this year',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': ['last year']
        }
        
        result = self.generator.generate_query(query_intent)
        
        assert result.optimization_hints is not None
        assert len(result.optimization_hints) > 0
        assert result.complexity_score > 1.0  # Should be complex due to comparison
    
    def test_yearly_aggregation(self):
        """Test yearly aggregation level."""
        query_intent = {
            'metric_type': 'revenue',
            'time_period': 'last 5 years',
            'aggregation_level': 'yearly',
            'filters': {},
            'comparison_periods': []
        }
        
        result = self.generator.generate_query(query_intent)
        
        assert 'YEAR(period_date)' in result.sql
    
    def test_daily_aggregation(self):
        """Test daily aggregation level."""
        query_intent = {
            'metric_type': 'cash_flow',
            'time_period': 'this month',
            'aggregation_level': 'daily',
            'filters': {},
            'comparison_periods': []
        }
        
        result = self.generator.generate_query(query_intent)
        
        assert 'DATE(period_date)' in result.sql
    
    def test_metric_synonyms(self):
        """Test that metric synonyms are handled correctly."""
        # Test revenue synonyms
        for metric in ['sales', 'income', 'turnover']:
            query_intent = {
                'metric_type': metric,
                'time_period': 'this year',
                'aggregation_level': 'monthly',
                'filters': {},
                'comparison_periods': []
            }
            
            result = self.generator.generate_query(query_intent)
            assert 'financial_overview' in result.sql
            assert 'revenue' in result.sql
    
    def test_complex_filters(self):
        """Test handling of multiple filters."""
        query_intent = {
            'metric_type': 'budget',
            'time_period': 'this quarter',
            'aggregation_level': 'monthly',
            'filters': {
                'department': 'marketing',
                'status': 'active'
            },
            'comparison_periods': []
        }
        
        result = self.generator.generate_query(query_intent)
        
        assert 'department' in result.sql
        assert 'marketing' in result.sql
    
    def test_month_end_day_calculation(self):
        """Test calculation of month end days."""
        # Test February in leap year
        assert self.generator._get_month_end_day(2024, 2) == 29
        
        # Test February in non-leap year
        assert self.generator._get_month_end_day(2023, 2) == 28
        
        # Test April (30 days)
        assert self.generator._get_month_end_day(2024, 4) == 30
        
        # Test December (31 days)
        assert self.generator._get_month_end_day(2024, 12) == 31