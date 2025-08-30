"""
Unit tests for Query Optimizer.
Tests query optimization strategies and performance improvements.
"""

import pytest
from src.optimization.optimizer import QueryOptimizer, QueryPlan, OptimizationStrategy


class TestQueryOptimizer:
    """Test cases for QueryOptimizer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = QueryOptimizer()
    
    def test_basic_query_optimization(self):
        """Test basic query optimization with index hints."""
        query = """
        SELECT period_date, SUM(revenue) as revenue
        FROM financial_overview
        WHERE period_date BETWEEN '2024-01-01' AND '2024-12-31'
        GROUP BY period_date
        ORDER BY period_date
        """
        
        result = self.optimizer.optimize_query(query)
        
        assert isinstance(result, QueryPlan)
        assert result.optimized_query != result.original_query
        assert len(result.applied_optimizations) > 0
        assert result.optimization_confidence > 0
    
    def test_index_hint_application(self):
        """Test that index hints are applied correctly."""
        query = """
        SELECT * FROM financial_overview
        WHERE period_date BETWEEN '2024-01-01' AND '2024-12-31'
        """
        
        result = self.optimizer.optimize_query(query)
        
        assert 'USE INDEX' in result.optimized_query
        assert 'idx_period_date' in result.optimized_query
        assert 'date_range_index_hint' in result.applied_optimizations
    
    def test_result_limiting_optimization(self):
        """Test that result limiting is applied to queries without LIMIT."""
        query = """
        SELECT * FROM financial_overview
        WHERE period_date > '2024-01-01'
        """
        
        result = self.optimizer.optimize_query(query)
        
        assert 'LIMIT' in result.optimized_query
        assert 'limit_large_results' in result.applied_optimizations
    
    def test_aggregation_optimization(self):
        """Test optimization of aggregation queries."""
        query = """
        SELECT DATE_FORMAT(period_date, '%Y-%m') as period, SUM(revenue)
        FROM financial_overview
        WHERE period_date BETWEEN '2024-01-01' AND '2024-12-31'
        GROUP BY DATE_FORMAT(period_date, '%Y-%m')
        """
        
        result = self.optimizer.optimize_query(query)
        
        # Should apply aggregation optimization
        assert any('aggregation' in opt for opt in result.applied_optimizations)
    
    def test_department_budget_optimization(self):
        """Test optimization for department-specific budget queries."""
        query = """
        SELECT * FROM budget_tracking
        WHERE department = 'sales' AND period_date BETWEEN '2024-01-01' AND '2024-12-31'
        """
        
        result = self.optimizer.optimize_query(query)
        
        # Should use department-period composite index
        assert 'idx_department_period' in result.optimized_query or 'USE INDEX' in result.optimized_query
    
    def test_complex_query_optimization(self):
        """Test optimization of complex queries with multiple tables."""
        query = """
        SELECT fo.period_date, fo.revenue, cf.net_cash_flow
        FROM financial_overview fo
        JOIN cash_flow cf ON fo.period_date = cf.period_date
        WHERE fo.period_date BETWEEN '2024-01-01' AND '2024-12-31'
        GROUP BY fo.period_date, fo.revenue, cf.net_cash_flow
        ORDER BY fo.period_date
        """
        
        result = self.optimizer.optimize_query(query)
        
        # Complex query should have higher complexity score
        assert result.estimated_cost > 100
        assert result.optimization_confidence > 0
        assert len(result.applied_optimizations) > 0
    
    def test_query_analysis(self):
        """Test query structure analysis."""
        query = """
        SELECT SUM(revenue), COUNT(*)
        FROM financial_overview
        WHERE period_date BETWEEN '2024-01-01' AND '2024-12-31'
        GROUP BY YEAR(period_date)
        ORDER BY YEAR(period_date)
        """
        
        analysis = self.optimizer._analyze_query(query)
        
        assert 'financial_overview' in analysis['tables']
        assert len(analysis['aggregations']) == 2  # SUM and COUNT
        assert len(analysis['group_by']) > 0
        assert len(analysis['order_by']) > 0
        assert analysis['complexity_score'] > 1.0
    
    def test_best_index_selection(self):
        """Test selection of best index for query conditions."""
        # Test date-based query
        best_index = self.optimizer._select_best_index(
            'financial_overview',
            ['period_date between 2024-01-01 and 2024-12-31']
        )
        
        assert best_index is not None
        assert 'period_date' in best_index
    
    def test_cost_estimation(self):
        """Test query cost estimation."""
        query = """
        SELECT * FROM financial_overview
        WHERE period_date BETWEEN '2024-01-01' AND '2024-12-31'
        """
        
        analysis = self.optimizer._analyze_query(query)
        cost_estimate = self.optimizer._estimate_query_cost(query, analysis)
        
        assert cost_estimate['total_cost'] > 0
        assert cost_estimate['estimated_rows'] > 0
        assert cost_estimate['execution_time_ms'] > 0
        assert cost_estimate['improvement_factor'] > 0
    
    def test_optimization_with_context(self):
        """Test optimization with additional context."""
        query = """
        SELECT * FROM financial_overview
        WHERE period_date BETWEEN '2024-01-01' AND '2024-12-31'
        """
        
        context = {
            'time_sensitive': True,
            'user_id': 'cfo_001',
            'allow_stale_data': True
        }
        
        result = self.optimizer.optimize_query(query, context)
        
        # Should apply context-specific optimizations
        assert 'MAX_EXECUTION_TIME' in result.optimized_query or len(result.applied_optimizations) > 0
    
    def test_union_query_optimization(self):
        """Test optimization of UNION queries."""
        query = """
        (SELECT period_date, revenue FROM financial_overview WHERE period_date BETWEEN '2024-01-01' AND '2024-12-31')
        UNION ALL
        (SELECT period_date, revenue FROM financial_overview WHERE period_date BETWEEN '2023-01-01' AND '2023-12-31')
        ORDER BY period_date
        """
        
        result = self.optimizer.optimize_query(query)
        
        # UNION queries should have higher complexity
        assert result.estimated_cost > 200
        assert result.optimization_confidence > 0
    
    def test_investment_query_optimization(self):
        """Test optimization for investment-related queries."""
        query = """
        SELECT * FROM investments
        WHERE status = 'active' AND start_date >= '2024-01-01'
        """
        
        result = self.optimizer.optimize_query(query)
        
        # Should optimize for status and date indexes
        assert len(result.applied_optimizations) > 0
        assert result.optimization_confidence > 0
    
    def test_no_optimization_needed(self):
        """Test queries that don't need optimization."""
        query = """
        SELECT * FROM financial_overview
        WHERE id = 1
        LIMIT 1
        """
        
        result = self.optimizer.optimize_query(query)
        
        # Simple query with specific ID and LIMIT may not need much optimization
        assert result.estimated_cost < 200
    
    def test_optimization_confidence_calculation(self):
        """Test calculation of optimization confidence scores."""
        # High-impact optimizations should have higher confidence
        high_impact_optimizations = ['date_range_index_hint', 'aggregation_with_index']
        low_impact_optimizations = ['limit_large_results']
        
        analysis = {'complexity_score': 1.5}
        
        high_confidence = self.optimizer._calculate_optimization_confidence(
            high_impact_optimizations, analysis
        )
        
        low_confidence = self.optimizer._calculate_optimization_confidence(
            low_impact_optimizations, analysis
        )
        
        assert high_confidence > low_confidence
        assert 0 <= high_confidence <= 1.0
        assert 0 <= low_confidence <= 1.0
    
    def test_optimization_stats_tracking(self):
        """Test that optimization statistics are tracked."""
        initial_stats = self.optimizer.get_optimization_stats()
        
        query = """
        SELECT * FROM financial_overview
        WHERE period_date BETWEEN '2024-01-01' AND '2024-12-31'
        """
        
        self.optimizer.optimize_query(query)
        
        updated_stats = self.optimizer.get_optimization_stats()
        
        assert updated_stats['queries_optimized'] == initial_stats['queries_optimized'] + 1
    
    def test_rule_application_conditions(self):
        """Test that optimization rules are applied under correct conditions."""
        # Test rule that should apply
        from src.optimization.optimizer import OptimizationRule, OptimizationStrategy
        
        rule = OptimizationRule(
            name="test_rule",
            strategy=OptimizationStrategy.INDEX_HINT,
            condition="period_date BETWEEN",
            action="USE INDEX (idx_period_date)",
            priority=1,
            estimated_improvement=0.4
        )
        
        query_with_condition = "SELECT * FROM financial_overview WHERE period_date BETWEEN '2024-01-01' AND '2024-12-31'"
        query_without_condition = "SELECT * FROM financial_overview WHERE id = 1"
        
        analysis = self.optimizer._analyze_query(query_with_condition)
        
        assert self.optimizer._rule_applies(rule, query_with_condition, analysis)
        assert not self.optimizer._rule_applies(rule, query_without_condition, analysis)
    
    def test_query_rewrite_optimization(self):
        """Test query rewriting optimizations."""
        # Test EXISTS to JOIN conversion (simplified)
        query = """
        SELECT * FROM financial_overview fo
        WHERE EXISTS (SELECT 1 FROM cash_flow cf WHERE cf.period_date = fo.period_date)
        """
        
        result = self.optimizer.optimize_query(query)
        
        # Should still optimize even if rewrite doesn't happen
        assert result.optimization_confidence >= 0
        assert isinstance(result, QueryPlan)