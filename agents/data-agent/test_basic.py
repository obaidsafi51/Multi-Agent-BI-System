#!/usr/bin/env python3
"""
Basic functionality test for Data Agent components.
Tests core functionality without external dependencies.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_query_generator():
    """Test basic query generation functionality."""
    print("Testing Query Generator...")
    
    try:
        from query.generator import QueryGenerator
        
        generator = QueryGenerator()
        
        # Test basic revenue query
        query_intent = {
            'metric_type': 'revenue',
            'time_period': 'this year',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        }
        
        result = generator.generate_query(query_intent)
        
        assert result.sql is not None
        assert 'financial_overview' in result.sql
        assert 'revenue' in result.sql
        assert result.params is not None
        
        print("✓ Query Generator basic functionality works")
        return True
        
    except Exception as e:
        print(f"✗ Query Generator test failed: {e}")
        return False

def test_data_validator():
    """Test basic data validation functionality."""
    print("Testing Data Validator...")
    
    try:
        from query.validator import DataValidator
        
        validator = DataValidator()
        
        # Test valid data
        query_result = {
            'data': [
                {'period_date': '2024-01-01', 'revenue': 1000000.00, 'record_count': 1},
                {'period_date': '2024-02-01', 'revenue': 1200000.00, 'record_count': 1}
            ],
            'columns': ['period_date', 'revenue', 'record_count']
        }
        
        result = validator.validate_query_result(query_result, 'revenue')
        
        # The validator might flag issues but should still have reasonable quality score
        assert result.quality_score > 0.5
        assert isinstance(result.issues, list)
        assert isinstance(result.warnings, list)
        
        # Check that validation completed successfully (even if data has issues)
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'quality_score')
        
        print("✓ Data Validator basic functionality works")
        return True
        
    except Exception as e:
        print(f"✗ Data Validator test failed: {e}")
        return False

def test_query_optimizer():
    """Test basic query optimization functionality."""
    print("Testing Query Optimizer...")
    
    try:
        from optimization.optimizer import QueryOptimizer
        
        optimizer = QueryOptimizer()
        
        # Test basic query optimization
        query = """
        SELECT period_date, SUM(revenue) as revenue
        FROM financial_overview
        WHERE period_date BETWEEN '2024-01-01' AND '2024-12-31'
        GROUP BY period_date
        ORDER BY period_date
        """
        
        result = optimizer.optimize_query(query)
        
        assert result.original_query == query
        assert result.optimized_query is not None
        assert isinstance(result.applied_optimizations, list)
        assert result.optimization_confidence >= 0
        
        print("✓ Query Optimizer basic functionality works")
        return True
        
    except Exception as e:
        print(f"✗ Query Optimizer test failed: {e}")
        return False

def test_metric_mappings():
    """Test metric to table mappings."""
    print("Testing Metric Mappings...")
    
    try:
        from query.generator import QueryGenerator
        
        generator = QueryGenerator()
        
        # Test various metric mappings
        test_cases = [
            ('revenue', 'financial_overview', 'revenue'),
            ('cash_flow', 'cash_flow', 'net_cash_flow'),
            ('budget', 'budget_tracking', 'budgeted_amount'),
            ('roi', 'investments', 'roi_percentage'),
            ('debt_to_equity', 'financial_ratios', 'debt_to_equity')
        ]
        
        for metric, expected_table, expected_column in test_cases:
            table_info = generator._get_table_info(metric)
            assert table_info is not None, f"No mapping found for {metric}"
            assert table_info[0] == expected_table, f"Wrong table for {metric}"
            assert table_info[1] == expected_column, f"Wrong column for {metric}"
        
        print("✓ Metric mappings work correctly")
        return True
        
    except Exception as e:
        print(f"✗ Metric mappings test failed: {e}")
        return False

def test_time_period_parsing():
    """Test time period parsing functionality."""
    print("Testing Time Period Parsing...")
    
    try:
        from query.generator import QueryGenerator
        
        generator = QueryGenerator()
        
        # Test quarterly parsing
        date_filter, params = generator._parse_time_period('Q1 2024', 'monthly')
        
        assert 'BETWEEN' in date_filter
        assert 'start_date' in params
        assert 'end_date' in params
        assert '2024-01-01' in params['start_date']
        assert '2024-03-31' in params['end_date']
        
        print("✓ Time period parsing works correctly")
        return True
        
    except Exception as e:
        print(f"✗ Time period parsing test failed: {e}")
        return False

def main():
    """Run all basic tests."""
    print("Running Data Agent Basic Functionality Tests")
    print("=" * 50)
    
    tests = [
        test_query_generator,
        test_data_validator,
        test_query_optimizer,
        test_metric_mappings,
        test_time_period_parsing
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic functionality tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())