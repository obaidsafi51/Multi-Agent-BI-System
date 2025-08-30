#!/usr/bin/env python3
"""
Demonstration of decimal precision validation logic.
"""

from decimal import Decimal
from database.validation import DataValidator, ValidationError


def demo_decimal_precision():
    """Demonstrate how decimal precision validation works"""
    
    print("=== Decimal Precision Validation Demo ===\n")
    
    print("1. Understanding Decimal.as_tuple():")
    print("   The as_tuple() method returns (sign, digits, exponent)")
    print("   - sign: 0 for positive, 1 for negative")
    print("   - digits: tuple of individual digits (0-9)")
    print("   - exponent: power of 10 to apply")
    print()
    
    # Test cases to demonstrate digits tuple behavior
    test_values = [
        "123.45",      # Normal decimal
        "0.00123",     # Leading zeros (ignored in digits)
        "1230000",     # Trailing zeros (included in digits)
        "0.10",        # Trailing zero after decimal
        "1000.00",     # Multiple trailing zeros
        "999999999999999",  # 15 digits (max)
        "1000000000000000", # 16 digits (over max)
        "0.000000000000001", # Very small number
    ]
    
    print("2. Decimal precision analysis:")
    for value_str in test_values:
        try:
            decimal_value = Decimal(value_str)
            sign, digits, exponent = decimal_value.as_tuple()
            
            print(f"   Value: {value_str}")
            print(f"     → Decimal: {decimal_value}")
            print(f"     → as_tuple(): sign={sign}, digits={digits}, exponent={exponent}")
            print(f"     → Significant digits count: {len(digits)}")
            print(f"     → Decimal places: {-exponent if exponent < 0 else 0}")
            print()
        except Exception as e:
            print(f"   Value: {value_str} → Error: {e}")
            print()
    
    print("3. Validation testing with max_digits=5:")
    validation_tests = [
        ("123.45", True, "5 digits - should pass"),
        ("12345", True, "5 digits - should pass"),
        ("123456", False, "6 digits - should fail"),
        ("0.12345", True, "5 significant digits - should pass"),
        ("0.123456", False, "6 significant digits - should fail"),
        ("12300", True, "5 digits including trailing zeros - should pass"),
        ("123000", False, "6 digits including trailing zeros - should fail"),
    ]
    
    for value, should_pass, description in validation_tests:
        print(f"   Testing: {value} ({description})")
        try:
            result = DataValidator.validate_decimal(value, "test_field", max_digits=5, decimal_places=10)
            if should_pass:
                print(f"     ✓ PASS: Validated as {result}")
            else:
                print(f"     ❌ UNEXPECTED: Should have failed but got {result}")
        except ValidationError as e:
            if not should_pass:
                print(f"     ✓ EXPECTED FAILURE: {e.message}")
            else:
                print(f"     ❌ UNEXPECTED FAILURE: {e.message}")
        print()
    
    print("4. Decimal places validation (separate from precision):")
    decimal_place_tests = [
        ("123.45", 2, True, "2 decimal places - should pass"),
        ("123.456", 2, False, "3 decimal places - should fail"),
        ("123", 2, True, "0 decimal places - should pass"),
        ("123.4", 2, True, "1 decimal place - should pass"),
    ]
    
    for value, max_decimal_places, should_pass, description in decimal_place_tests:
        print(f"   Testing: {value} with max {max_decimal_places} decimal places ({description})")
        try:
            result = DataValidator.validate_decimal(value, "test_field", max_digits=15, decimal_places=max_decimal_places)
            if should_pass:
                print(f"     ✓ PASS: Validated as {result}")
            else:
                print(f"     ❌ UNEXPECTED: Should have failed but got {result}")
        except ValidationError as e:
            if not should_pass:
                print(f"     ✓ EXPECTED FAILURE: {e.message}")
            else:
                print(f"     ❌ UNEXPECTED FAILURE: {e.message}")
        print()
    
    print("5. Key insights:")
    print("   • len(digits) counts ALL significant digits, including trailing zeros")
    print("   • Leading zeros are NOT included in the digits tuple")
    print("   • Precision (max_digits) and decimal places are independent validations")
    print("   • The digits tuple represents the 'coefficient' of the decimal number")
    print("   • Exponent determines where the decimal point goes")
    print()
    
    print("=== Demo Complete ===")


if __name__ == "__main__":
    demo_decimal_precision()