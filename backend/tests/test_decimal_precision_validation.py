"""
Tests for decimal precision validation logic.
"""

import pytest
from decimal import Decimal
from backend.database.validation import DataValidator, ValidationError


class TestDecimalPrecisionValidation:
    """Test decimal precision validation with detailed understanding of digits tuple"""
    
    def test_digits_tuple_understanding(self):
        """Test understanding of how Decimal.as_tuple() digits work"""
        test_cases = [
            # (value, expected_digits_tuple, expected_digit_count, description)
            ("123.45", (1, 2, 3, 4, 5), 5, "Normal decimal"),
            ("0.00123", (1, 2, 3), 3, "Leading zeros ignored"),
            ("1230000", (1, 2, 3, 0, 0, 0, 0), 7, "Trailing zeros included"),
            ("0.10", (1, 0), 2, "Trailing zero after decimal"),
            ("1000.00", (1, 0, 0, 0, 0, 0), 6, "Multiple trailing zeros"),
            ("999999999999999", tuple([9] * 15), 15, "15 digits exactly"),
            ("0.000000000000001", (1,), 1, "Very small number"),
        ]
        
        for value_str, expected_digits, expected_count, description in test_cases:
            decimal_value = Decimal(value_str)
            sign, digits, exponent = decimal_value.as_tuple()
            
            assert digits == expected_digits, f"{description}: Expected digits {expected_digits}, got {digits}"
            assert len(digits) == expected_count, f"{description}: Expected {expected_count} digits, got {len(digits)}"
    
    def test_precision_validation_passes(self):
        """Test cases that should pass precision validation"""
        test_cases = [
            # (value, max_digits, max_decimal_places, description)
            ("123.45", 5, 2, "5 digits exactly"),
            ("123.45", 6, 2, "5 digits with higher limit"),
            ("12345", 5, 0, "5 integer digits"),
            ("0.12", 3, 2, "3 significant digits with leading zero"),
            ("12300", 5, 0, "5 digits including trailing zeros"),
            ("1", 1, 0, "Single digit"),
            ("0.1", 1, 1, "Single significant digit"),
        ]
        
        for value, max_digits, max_decimal_places, description in test_cases:
            result = DataValidator.validate_decimal(value, "test_field", max_digits=max_digits, decimal_places=max_decimal_places)
            assert result == Decimal(value), f"{description}: Expected {value}, got {result}"
    
    def test_precision_validation_fails(self):
        """Test cases that should fail precision validation"""
        test_cases = [
            # (value, max_digits, description)
            ("123456", 5, "6 digits exceeds limit of 5"),
            ("0.123456", 5, "6 significant digits exceeds limit"),
            ("123000", 5, "6 digits including trailing zeros"),
            ("1000000000000000", 15, "16 digits exceeds limit of 15"),
            ("12", 1, "2 digits exceeds limit of 1"),
        ]
        
        for value, max_digits, description in test_cases:
            with pytest.raises(ValidationError) as exc_info:
                DataValidator.validate_decimal(value, "test_field", max_digits=max_digits)
            
            assert "too many digits" in exc_info.value.message, f"{description}: Expected 'too many digits' error"
            assert f"max {max_digits}" in exc_info.value.message, f"{description}: Expected max digits in error message"
    
    def test_precision_vs_decimal_places_independence(self):
        """Test that precision and decimal places are validated independently"""
        # High precision, low decimal places - should pass precision, fail decimal places
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_decimal("123.456", "test_field", max_digits=10, decimal_places=2)
        assert "decimal places" in exc_info.value.message
        
        # Low precision, high decimal places - should fail precision, not reach decimal places check
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_decimal("123456.12", "test_field", max_digits=5, decimal_places=10)
        assert "too many digits" in exc_info.value.message
        
        # Both within limits - should pass
        result = DataValidator.validate_decimal("123.45", "test_field", max_digits=10, decimal_places=2)
        assert result == Decimal("123.45")
    
    def test_edge_cases(self):
        """Test edge cases for decimal precision validation"""
        # Zero should pass
        result = DataValidator.validate_decimal("0", "test_field", max_digits=1, decimal_places=0)
        assert result == Decimal("0")
        
        # Negative numbers (sign doesn't count toward digits)
        result = DataValidator.validate_decimal("-123.45", "test_field", max_digits=5, decimal_places=2)
        assert result == Decimal("-123.45")
        
        # Very large exponent (scientific notation)
        result = DataValidator.validate_decimal("1E+10", "test_field", max_digits=1, decimal_places=0)
        assert result == Decimal("1E+10")
        
        # Very small exponent
        result = DataValidator.validate_decimal("1E-10", "test_field", max_digits=1, decimal_places=15)
        assert result == Decimal("1E-10")
    
    def test_trailing_zeros_behavior(self):
        """Test specific behavior with trailing zeros"""
        # Trailing zeros in decimal representation count toward precision
        test_cases = [
            ("1.00", 3, True, "3 digits including trailing zeros"),
            ("1.00", 2, False, "3 digits exceeds limit of 2"),
            ("100.0", 4, True, "4 digits including trailing zero"),
            ("100.0", 3, False, "4 digits exceeds limit of 3"),
        ]
        
        for value, max_digits, should_pass, description in test_cases:
            if should_pass:
                result = DataValidator.validate_decimal(value, "test_field", max_digits=max_digits)
                assert result == Decimal(value), f"{description}: Should pass"
            else:
                with pytest.raises(ValidationError):
                    DataValidator.validate_decimal(value, "test_field", max_digits=max_digits)
    
    def test_leading_zeros_behavior(self):
        """Test that leading zeros don't count toward precision"""
        # Leading zeros should not count toward digit limit
        test_cases = [
            ("0.12", 3, 2, "Leading zero doesn't count"),
            ("0.012", 3, 3, "Multiple leading zeros don't count"),
            ("0.000012", 3, 6, "Many leading zeros don't count"),
        ]
        
        for value, max_digits, max_decimal_places, description in test_cases:
            result = DataValidator.validate_decimal(value, "test_field", max_digits=max_digits, decimal_places=max_decimal_places)
            assert result == Decimal(value), f"{description}: Should pass with {max_digits} digit limit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])