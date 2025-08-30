"""
Unit tests for Data Validator.
Tests data validation and quality assessment for financial data.
"""

import pytest
from datetime import datetime, timedelta
from src.query.validator import DataValidator, ValidationResult


class TestDataValidator:
    """Test cases for DataValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DataValidator()
    
    def test_valid_revenue_data(self):
        """Test validation of valid revenue data."""
        query_result = {
            'data': [
                {'period_date': '2024-01-01', 'revenue': 1000000.00, 'record_count': 1},
                {'period_date': '2024-02-01', 'revenue': 1200000.00, 'record_count': 1},
                {'period_date': '2024-03-01', 'revenue': 1100000.00, 'record_count': 1}
            ],
            'columns': ['period_date', 'revenue', 'record_count']
        }
        
        result = self.validator.validate_query_result(query_result, 'revenue')
        
        assert result.is_valid
        assert result.quality_score > 0.8
        assert len(result.issues) == 0
    
    def test_negative_revenue_warning(self):
        """Test that negative revenue generates warnings."""
        query_result = {
            'data': [
                {'period_date': '2024-01-01', 'revenue': -100000.00, 'record_count': 1}
            ],
            'columns': ['period_date', 'revenue', 'record_count']
        }
        
        result = self.validator.validate_query_result(query_result, 'revenue')
        
        assert len(result.warnings) > 0
        assert any('negative revenue' in warning.lower() for warning in result.warnings)
    
    def test_missing_required_fields(self):
        """Test validation failure for missing required fields."""
        query_result = {
            'data': [
                {'revenue': 1000000.00}  # Missing period_date
            ],
            'columns': ['revenue']
        }
        
        result = self.validator.validate_query_result(query_result, 'revenue')
        
        assert not result.is_valid
        assert len(result.issues) > 0
        assert any('missing required fields' in issue.lower() for issue in result.issues)
    
    def test_empty_data_validation(self):
        """Test validation of empty data."""
        query_result = {
            'data': [],
            'columns': []
        }
        
        result = self.validator.validate_query_result(query_result, 'revenue')
        
        assert not result.is_valid
        assert result.quality_score == 0.0
        assert 'no data returned' in result.issues[0].lower()
    
    def test_cash_flow_consistency(self):
        """Test cash flow component consistency validation."""
        query_result = {
            'data': [
                {
                    'period_date': '2024-01-01',
                    'operating_cash_flow': 100000.00,
                    'investing_cash_flow': -50000.00,
                    'financing_cash_flow': -20000.00,
                    'net_cash_flow': 30000.00  # Should equal sum of components
                }
            ],
            'columns': ['period_date', 'operating_cash_flow', 'investing_cash_flow', 
                       'financing_cash_flow', 'net_cash_flow']
        }
        
        result = self.validator.validate_query_result(query_result, 'cash_flow')
        
        assert result.is_valid
        assert len(result.warnings) == 0  # Components sum correctly
    
    def test_cash_flow_inconsistency_warning(self):
        """Test warning for inconsistent cash flow components."""
        query_result = {
            'data': [
                {
                    'period_date': '2024-01-01',
                    'operating_cash_flow': 100000.00,
                    'investing_cash_flow': -50000.00,
                    'financing_cash_flow': -20000.00,
                    'net_cash_flow': 50000.00  # Incorrect sum
                }
            ],
            'columns': ['period_date', 'operating_cash_flow', 'investing_cash_flow', 
                       'financing_cash_flow', 'net_cash_flow']
        }
        
        result = self.validator.validate_query_result(query_result, 'cash_flow')
        
        assert len(result.warnings) > 0
        assert any('components don\'t sum' in warning.lower() for warning in result.warnings)
    
    def test_gross_profit_exceeds_revenue(self):
        """Test validation error when gross profit exceeds revenue."""
        query_result = {
            'data': [
                {
                    'period_date': '2024-01-01',
                    'revenue': 1000000.00,
                    'gross_profit': 1200000.00  # Exceeds revenue
                }
            ],
            'columns': ['period_date', 'revenue', 'gross_profit']
        }
        
        result = self.validator.validate_query_result(query_result, 'revenue')
        
        assert not result.is_valid
        assert len(result.issues) > 0
        assert any('gross profit exceeds revenue' in issue.lower() for issue in result.issues)
    
    def test_outlier_detection(self):
        """Test outlier detection in financial data."""
        # Create data with one clear outlier
        normal_values = [100000, 105000, 98000, 102000, 99000]
        outlier_value = 1000000  # 10x normal values
        
        query_result = {
            'data': [
                {'period_date': f'2024-0{i+1}-01', 'revenue': value, 'record_count': 1}
                for i, value in enumerate(normal_values)
            ] + [
                {'period_date': '2024-06-01', 'revenue': outlier_value, 'record_count': 1}
            ],
            'columns': ['period_date', 'revenue', 'record_count']
        }
        
        result = self.validator.validate_query_result(query_result, 'revenue')
        
        assert len(result.warnings) > 0
        assert any('outlier' in warning.lower() for warning in result.warnings)
    
    def test_data_freshness_validation(self):
        """Test data freshness validation."""
        # Create old data (more than 2 months old)
        old_date = (datetime.now() - timedelta(days=70)).strftime('%Y-%m-%d')
        
        query_result = {
            'data': [
                {'period_date': old_date, 'revenue': 1000000.00, 'record_count': 1}
            ],
            'columns': ['period_date', 'revenue', 'record_count']
        }
        
        result = self.validator.validate_query_result(query_result, 'revenue', 'monthly')
        
        # Should generate warnings for old data
        assert len(result.warnings) > 0 or len(result.issues) > 0
    
    def test_duplicate_periods_warning(self):
        """Test warning for duplicate time periods."""
        query_result = {
            'data': [
                {'period': '2024-01', 'revenue': 1000000.00, 'record_count': 1},
                {'period': '2024-01', 'revenue': 1100000.00, 'record_count': 1}  # Duplicate
            ],
            'columns': ['period', 'revenue', 'record_count']
        }
        
        result = self.validator.validate_query_result(query_result, 'revenue')
        
        assert len(result.warnings) > 0
        assert any('duplicate' in warning.lower() for warning in result.warnings)
    
    def test_invalid_numeric_values(self):
        """Test validation of invalid numeric values."""
        query_result = {
            'data': [
                {'period_date': '2024-01-01', 'revenue': 'invalid_number', 'record_count': 1}
            ],
            'columns': ['period_date', 'revenue', 'record_count']
        }
        
        result = self.validator.validate_query_result(query_result, 'revenue')
        
        assert not result.is_valid
        assert len(result.issues) > 0
        assert any('invalid numeric value' in issue.lower() for issue in result.issues)
    
    def test_null_values_handling(self):
        """Test handling of null values in data."""
        query_result = {
            'data': [
                {'period_date': '2024-01-01', 'revenue': None, 'record_count': 1},
                {'period_date': '2024-02-01', 'revenue': 1000000.00, 'record_count': 1}
            ],
            'columns': ['period_date', 'revenue', 'record_count']
        }
        
        result = self.validator.validate_query_result(query_result, 'revenue')
        
        # Should still be valid but with reduced quality score
        assert result.is_valid
        assert result.quality_score < 1.0
        assert result.metadata['quality_metrics'].null_count > 0
    
    def test_financial_ratio_validation(self):
        """Test validation of financial ratios."""
        query_result = {
            'data': [
                {
                    'period_date': '2024-01-01',
                    'debt_to_equity': 0.5,
                    'current_ratio': 2.1,
                    'quick_ratio': 1.8
                }
            ],
            'columns': ['period_date', 'debt_to_equity', 'current_ratio', 'quick_ratio']
        }
        
        result = self.validator.validate_query_result(query_result, 'debt_to_equity')
        
        assert result.is_valid
        assert result.quality_score > 0.8
    
    def test_excessive_decimal_places_warning(self):
        """Test warning for excessive decimal places."""
        query_result = {
            'data': [
                {'period_date': '2024-01-01', 'revenue': 1000000.123456789, 'record_count': 1}
            ],
            'columns': ['period_date', 'revenue', 'record_count']
        }
        
        result = self.validator.validate_query_result(query_result, 'revenue')
        
        assert len(result.warnings) > 0
        assert any('decimal places' in warning.lower() for warning in result.warnings)
    
    def test_invalid_date_format(self):
        """Test validation of invalid date formats."""
        query_result = {
            'data': [
                {'period_date': 'invalid-date', 'revenue': 1000000.00, 'record_count': 1}
            ],
            'columns': ['period_date', 'revenue', 'record_count']
        }
        
        result = self.validator.validate_query_result(query_result, 'revenue')
        
        assert not result.is_valid
        assert len(result.issues) > 0
        assert any('invalid date format' in issue.lower() for issue in result.issues)
    
    def test_quality_metrics_calculation(self):
        """Test calculation of comprehensive quality metrics."""
        query_result = {
            'data': [
                {'period_date': '2024-01-01', 'revenue': 1000000.00, 'record_count': 1},
                {'period_date': '2024-02-01', 'revenue': None, 'record_count': 1},  # Null value
                {'period_date': '2024-03-01', 'revenue': 1200000.00, 'record_count': 1}
            ],
            'columns': ['period_date', 'revenue', 'record_count']
        }
        
        result = self.validator.validate_query_result(query_result, 'revenue')
        
        quality_metrics = result.metadata['quality_metrics']
        
        assert hasattr(quality_metrics, 'completeness_score')
        assert hasattr(quality_metrics, 'accuracy_score')
        assert hasattr(quality_metrics, 'consistency_score')
        assert hasattr(quality_metrics, 'timeliness_score')
        assert hasattr(quality_metrics, 'overall_score')
        
        # Completeness should be less than 1.0 due to null value
        assert quality_metrics.completeness_score < 1.0
        assert quality_metrics.null_count == 1
        assert quality_metrics.total_records == 3
        assert quality_metrics.valid_records == 2