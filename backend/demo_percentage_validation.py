#!/usr/bin/env python3
"""
Demonstration of the flexible percentage validation system.
"""

from database.validation import DataValidator, PercentageType, ValidationError, FinancialDataValidator
from decimal import Decimal


def demo_percentage_validation():
    """Demonstrate the flexible percentage validation system"""
    
    print("=== Flexible Percentage Validation Demo ===\n")
    
    # Test cases for different percentage types
    test_cases = [
        # (value, percentage_type, description, should_pass)
        (50.0, PercentageType.STANDARD, "Standard percentage", True),
        (150.0, PercentageType.STANDARD, "Standard percentage > 100%", False),
        (250.0, PercentageType.ROI, "High ROI (250%)", True),
        (1500.0, PercentageType.ROI, "Very high ROI (1500%) - should warn", True),
        (-75.0, PercentageType.ROI, "Negative ROI (-75%)", True),
        (-150.0, PercentageType.ROI, "Loss exceeding investment (-150%)", True),
        (300.0, PercentageType.GROWTH_RATE, "High growth rate (300%)", True),
        (-50.0, PercentageType.GROWTH_RATE, "Negative growth (-50%)", True),
        (-100.0, PercentageType.GROWTH_RATE, "Complete loss (-100%)", True),
        (-120.0, PercentageType.GROWTH_RATE, "Invalid growth rate (-120%)", False),
        (250.0, PercentageType.VARIANCE, "High budget variance (250%) - should warn", True),
        (-300.0, PercentageType.VARIANCE, "High negative variance (-300%) - should warn", True),
        (75.0, PercentageType.MARGIN, "Valid profit margin (75%)", True),
        (110.0, PercentageType.MARGIN, "Invalid margin > 100%", False),
        (-10.0, PercentageType.MARGIN, "Invalid negative margin", False),
    ]
    
    for value, percentage_type, description, should_pass in test_cases:
        print(f"Testing: {description}")
        print(f"  Value: {value}%, Type: {percentage_type.value}")
        
        try:
            result, warning = DataValidator.validate_percentage_typed(
                value, "test_field", percentage_type
            )
            
            if should_pass:
                print(f"  ✓ PASS: Validated as {result}%")
                if warning:
                    print(f"  ⚠️  WARNING: {warning.message}")
            else:
                print(f"  ❌ UNEXPECTED: Should have failed but got {result}%")
                
        except ValidationError as e:
            if not should_pass:
                print(f"  ✓ EXPECTED FAILURE: {e.message}")
            else:
                print(f"  ❌ UNEXPECTED FAILURE: {e.message}")
        
        print()
    
    print("=== Financial Data Validation Demo ===\n")
    
    # Demo investment with high ROI
    print("Testing investment with high ROI:")
    investment_data = {
        'investment_name': 'High Growth Tech Stock',
        'investment_category': 'Equity',
        'initial_amount': 1000.0,
        'current_value': 3500.0,  # 250% ROI
        'status': 'active',
        'start_date': '2023-01-01'
    }
    
    try:
        validated = FinancialDataValidator.validate_investment(investment_data)
        print(f"  ✓ Investment validated successfully")
        print(f"  ROI: {validated['roi_percentage']}%")
        print(f"  Investment: {validated['investment_name']}")
    except ValidationError as e:
        print(f"  ❌ Validation failed: {e}")
    
    print()
    
    # Demo budget tracking with high variance
    print("Testing budget tracking with high variance:")
    budget_data = {
        'department': 'Marketing',
        'period_date': '2024-01-01',
        'budgeted_amount': 1000.0,
        'actual_amount': 3500.0  # 250% variance
    }
    
    try:
        validated = FinancialDataValidator.validate_budget_tracking(budget_data)
        print(f"  ✓ Budget tracking validated successfully")
        print(f"  Variance: {validated['variance_percentage']}%")
        print(f"  Department: {validated['department']}")
    except ValidationError as e:
        print(f"  ❌ Validation failed: {e}")
    
    print()
    
    print("=== Backward Compatibility Demo ===\n")
    
    # Test backward compatibility
    print("Testing legacy validate_percentage method:")
    legacy_test_cases = [
        (50.0, True),
        (100.0, True),
        (-100.0, True),
        (150.0, False),  # Should fail with legacy method
    ]
    
    for value, should_pass in legacy_test_cases:
        try:
            result = DataValidator.validate_percentage(value, "legacy_field")
            if should_pass:
                print(f"  ✓ Legacy validation passed for {value}%: {result}%")
            else:
                print(f"  ❌ Legacy validation should have failed for {value}%")
        except ValidationError as e:
            if not should_pass:
                print(f"  ✓ Legacy validation correctly failed for {value}%: {e.message}")
            else:
                print(f"  ❌ Legacy validation unexpectedly failed for {value}%: {e.message}")
    
    print()
    
    print("=== Epsilon-Based Calculation Safety Demo ===\n")
    
    # Demo epsilon-based calculations
    print("Testing epsilon-based floating-point safety:")
    
    # Test with zero budget (should not calculate percentage)
    zero_budget_data = {
        'department': 'Zero Budget Test',
        'period_date': '2024-01-01',
        'budgeted_amount': 0.00,
        'actual_amount': 100.0
    }
    
    try:
        validated = FinancialDataValidator.validate_budget_tracking(zero_budget_data)
        print(f"  ✓ Zero budget handled safely")
        print(f"  Variance amount: ${validated['variance_amount']}")
        print(f"  Variance percentage: {validated['variance_percentage']} (None = undefined)")
    except ValidationError as e:
        print(f"  ❌ Zero budget validation failed: {e}")
    
    print()
    
    # Test with very small budget at epsilon threshold
    epsilon_budget_data = {
        'department': 'Epsilon Budget Test',
        'period_date': '2024-01-01',
        'budgeted_amount': 0.01,  # Exactly at epsilon threshold
        'actual_amount': 0.02
    }
    
    try:
        validated = FinancialDataValidator.validate_budget_tracking(epsilon_budget_data)
        print(f"  ✓ Epsilon threshold budget calculated safely")
        print(f"  Variance amount: ${validated['variance_amount']}")
        print(f"  Variance percentage: {validated['variance_percentage']}%")
    except ValidationError as e:
        print(f"  ❌ Epsilon budget validation failed: {e}")
    
    print()
    
    # Test with zero investment (should not calculate ROI)
    zero_investment_data = {
        'investment_name': 'Zero Investment Test',
        'investment_category': 'Test',
        'initial_amount': 0.00,
        'current_value': 100.0,
        'status': 'active'
    }
    
    try:
        validated = FinancialDataValidator.validate_investment(zero_investment_data)
        print(f"  ✓ Zero investment handled safely")
        print(f"  Investment: {validated['investment_name']}")
        print(f"  ROI percentage: {validated['roi_percentage']} (None = undefined)")
    except ValidationError as e:
        print(f"  ❌ Zero investment validation failed: {e}")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    demo_percentage_validation()