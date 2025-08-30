"""
Tests for flexible percentage validation system.
"""

import pytest
from decimal import Decimal
from database.validation import (
    DataValidator, 
    PercentageType, 
    ValidationError, 
    ValidationWarning,
    FinancialDataValidator
)


class TestPercentageValidation:
    """Test the flexible percentage validation system"""
    
    def test_standard_percentage_validation(self):
        """Test standard percentage validation (-100% to 100%)"""
        # Valid values
        assert DataValidator.validate_percentage(50.0, "test_field") == Decimal('50.0')
        assert DataValidator.validate_percentage(-75.5, "test_field") == Decimal('-75.5')
        assert DataValidator.validate_percentage(100, "test_field") == Decimal('100')
        assert DataValidator.validate_percentage(-100, "test_field") == Decimal('-100')
        
        # Invalid values
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_percentage(150.0, "test_field")
        assert "must be <= 100%" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_percentage(-150.0, "test_field")
        assert "must be >= -100%" in str(exc_info.value)
    
    def test_roi_percentage_validation(self):
        """Test ROI percentage validation (unlimited range)"""
        # Valid values including high ROI
        result, warning = DataValidator.validate_percentage_typed(
            250.0, "roi_field", PercentageType.ROI
        )
        assert result == Decimal('250.0')
        assert warning is None
        
        result, warning = DataValidator.validate_percentage_typed(
            -75.0, "roi_field", PercentageType.ROI
        )
        assert result == Decimal('-75.0')
        assert warning is None
        
        # Very high ROI should generate warning
        result, warning = DataValidator.validate_percentage_typed(
            1500.0, "roi_field", PercentageType.ROI
        )
        assert result == Decimal('1500.0')
        assert warning is not None
        assert "Unusual roi percentage" in warning.message
        assert "1500.0%" in warning.message
        
        # Extreme negative ROI (total loss and more)
        result, warning = DataValidator.validate_percentage_typed(
            -150.0, "roi_field", PercentageType.ROI
        )
        assert result == Decimal('-150.0')
        assert warning is None
    
    def test_growth_rate_percentage_validation(self):
        """Test growth rate percentage validation (-100% to unlimited positive)"""
        # Valid positive growth rates
        result, warning = DataValidator.validate_percentage_typed(
            150.0, "growth_field", PercentageType.GROWTH_RATE
        )
        assert result == Decimal('150.0')
        assert warning is None
        
        # Valid negative growth (decline)
        result, warning = DataValidator.validate_percentage_typed(
            -50.0, "growth_field", PercentageType.GROWTH_RATE
        )
        assert result == Decimal('-50.0')
        assert warning is None
        
        # Complete loss (-100%)
        result, warning = DataValidator.validate_percentage_typed(
            -100.0, "growth_field", PercentageType.GROWTH_RATE
        )
        assert result == Decimal('-100.0')
        assert warning is None
        
        # Invalid: below -100%
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_percentage_typed(
                -120.0, "growth_field", PercentageType.GROWTH_RATE
            )
        assert "must be >= -100%" in str(exc_info.value)
        
        # High growth rate should generate warning
        result, warning = DataValidator.validate_percentage_typed(
            600.0, "growth_field", PercentageType.GROWTH_RATE
        )
        assert result == Decimal('600.0')
        assert warning is not None
        assert "Unusual growth_rate percentage" in warning.message
    
    def test_variance_percentage_validation(self):
        """Test variance percentage validation (unlimited range)"""
        # Normal variance
        result, warning = DataValidator.validate_percentage_typed(
            25.0, "variance_field", PercentageType.VARIANCE
        )
        assert result == Decimal('25.0')
        assert warning is None
        
        # High positive variance should generate warning
        result, warning = DataValidator.validate_percentage_typed(
            250.0, "variance_field", PercentageType.VARIANCE
        )
        assert result == Decimal('250.0')
        assert warning is not None
        assert "Unusual variance percentage" in warning.message
        
        # High negative variance should generate warning
        result, warning = DataValidator.validate_percentage_typed(
            -250.0, "variance_field", PercentageType.VARIANCE
        )
        assert result == Decimal('-250.0')
        assert warning is not None
        assert "Unusual variance percentage" in warning.message
    
    def test_margin_percentage_validation(self):
        """Test margin percentage validation (0% to 100%)"""
        # Valid margins
        result, warning = DataValidator.validate_percentage_typed(
            25.5, "margin_field", PercentageType.MARGIN
        )
        assert result == Decimal('25.5')
        assert warning is None
        
        result, warning = DataValidator.validate_percentage_typed(
            0, "margin_field", PercentageType.MARGIN
        )
        assert result == Decimal('0')
        assert warning is None
        
        result, warning = DataValidator.validate_percentage_typed(
            100, "margin_field", PercentageType.MARGIN
        )
        assert result == Decimal('100')
        assert warning is None
        
        # Invalid: negative margin
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_percentage_typed(
                -10.0, "margin_field", PercentageType.MARGIN
            )
        assert "must be >= 0%" in str(exc_info.value)
        
        # Invalid: margin over 100%
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_percentage_typed(
                110.0, "margin_field", PercentageType.MARGIN
            )
        assert "must be <= 100%" in str(exc_info.value)
    
    def test_null_values(self):
        """Test handling of null values"""
        result, warning = DataValidator.validate_percentage_typed(
            None, "test_field", PercentageType.ROI
        )
        assert result is None
        assert warning is None
        
        # Legacy method should also handle null
        result = DataValidator.validate_percentage(None, "test_field")
        assert result is None


class TestFinancialDataValidation:
    """Test financial data validation with new percentage types"""
    
    def test_investment_validation_with_high_roi(self):
        """Test investment validation with high ROI values"""
        data = {
            'investment_name': 'High Growth Stock',
            'investment_category': 'Equity',
            'initial_amount': 1000.0,
            'current_value': 3500.0,  # 250% ROI
            'status': 'active',
            'start_date': '2023-01-01'
        }
        
        validated = FinancialDataValidator.validate_investment(data)
        
        assert validated['roi_percentage'] == Decimal('250.0')
        assert validated['investment_name'] == 'High Growth Stock'
    
    def test_investment_validation_with_extreme_roi(self):
        """Test investment validation with extreme ROI that should generate warning"""
        data = {
            'investment_name': 'Crypto Investment',
            'investment_category': 'Cryptocurrency',
            'initial_amount': 100.0,
            'current_value': 1200.0,  # 1100% ROI - should warn
            'status': 'active',
            'start_date': '2023-01-01'
        }
        
        # This should not raise an exception but should log a warning
        validated = FinancialDataValidator.validate_investment(data)
        assert validated['roi_percentage'] == Decimal('1100.0')
    
    def test_budget_tracking_with_high_variance(self):
        """Test budget tracking with high variance values"""
        data = {
            'department': 'Marketing',
            'period_date': '2024-01-01',
            'budgeted_amount': 1000.0,
            'actual_amount': 3000.0  # 200% variance
        }
        
        validated = FinancialDataValidator.validate_budget_tracking(data)
        
        assert validated['variance_percentage'] == Decimal('200.0')
        assert validated['variance_amount'] == Decimal('2000.0')
    
    def test_budget_tracking_with_extreme_variance(self):
        """Test budget tracking with extreme variance that should generate warning"""
        data = {
            'department': 'R&D',
            'period_date': '2024-01-01',
            'budgeted_amount': 500.0,
            'actual_amount': 2000.0  # 300% variance - should warn
        }
        
        # This should not raise an exception but should log a warning
        validated = FinancialDataValidator.validate_budget_tracking(data)
        assert validated['variance_percentage'] == Decimal('300.0')
    
    def test_backward_compatibility(self):
        """Test that existing code using validate_percentage still works"""
        # This should work exactly as before for standard percentages
        result = DataValidator.validate_percentage(75.0, "test_field")
        assert result == Decimal('75.0')
        
        # This should still fail for values outside -100 to 100
        with pytest.raises(ValidationError):
            DataValidator.validate_percentage(150.0, "test_field")
    
    def test_epsilon_based_calculations(self):
        """Test epsilon-based calculations for floating-point safety"""
        # Test budget tracking with zero budgeted amount
        data_zero_budget = {
            'department': 'Test',
            'period_date': '2024-01-01',
            'budgeted_amount': 0.00,  # Zero budget
            'actual_amount': 100.0
        }
        
        validated = FinancialDataValidator.validate_budget_tracking(data_zero_budget)
        # Should not calculate percentage for zero budget
        assert validated['variance_percentage'] is None
        assert validated['variance_amount'] == Decimal('100.00')
        
        # Test budget tracking with budget exactly at epsilon
        data_epsilon_budget = {
            'department': 'Test',
            'period_date': '2024-01-01',
            'budgeted_amount': 0.01,  # Exactly epsilon
            'actual_amount': 0.02
        }
        
        validated = FinancialDataValidator.validate_budget_tracking(data_epsilon_budget)
        # Should calculate percentage for budget at epsilon
        assert validated['variance_percentage'] == Decimal('100.0')  # 100% increase
        
        # Test budget tracking with budget just above epsilon
        data_above_epsilon_budget = {
            'department': 'Test',
            'period_date': '2024-01-01',
            'budgeted_amount': 0.02,  # Above epsilon
            'actual_amount': 0.04
        }
        
        validated = FinancialDataValidator.validate_budget_tracking(data_above_epsilon_budget)
        # Should calculate percentage for budget above epsilon
        assert validated['variance_percentage'] == Decimal('100.0')  # 100% increase
        
        # Test investment with zero initial amount
        data_zero_investment = {
            'investment_name': 'Zero Investment',
            'investment_category': 'Test',
            'initial_amount': 0.00,  # Zero initial amount
            'current_value': 100.0,
            'status': 'active'
        }
        
        validated = FinancialDataValidator.validate_investment(data_zero_investment)
        # Should not calculate ROI for zero initial investment
        assert validated['roi_percentage'] is None
        
        # Test investment with initial amount exactly at epsilon
        data_epsilon_investment = {
            'investment_name': 'Small Investment',
            'investment_category': 'Test',
            'initial_amount': 0.01,  # Exactly epsilon
            'current_value': 0.02,
            'status': 'active'
        }
        
        validated = FinancialDataValidator.validate_investment(data_epsilon_investment)
        # Should calculate ROI for investment at epsilon
        assert validated['roi_percentage'] == Decimal('100.0')  # 100% ROI


class TestPercentageValidationConfig:
    """Test percentage validation configuration"""
    
    def test_get_percentage_config(self):
        """Test getting percentage configuration"""
        roi_config = DataValidator.get_percentage_config(PercentageType.ROI)
        assert roi_config.min_value is None
        assert roi_config.max_value is None
        assert roi_config.warning_threshold == Decimal('1000')
        assert "Return on Investment" in roi_config.description
        
        standard_config = DataValidator.get_percentage_config(PercentageType.STANDARD)
        assert standard_config.min_value == Decimal('-100')
        assert standard_config.max_value == Decimal('100')
        assert standard_config.warning_threshold is None
    
    def test_validation_error_with_percentage_type(self):
        """Test that ValidationError includes percentage type information"""
        try:
            DataValidator.validate_percentage_typed(
                -150.0, "growth_field", PercentageType.GROWTH_RATE
            )
        except ValidationError as e:
            assert e.percentage_type == PercentageType.GROWTH_RATE
            assert "growth_rate" in str(e)
            assert "Growth rate" in str(e)


if __name__ == "__main__":
    pytest.main([__file__])