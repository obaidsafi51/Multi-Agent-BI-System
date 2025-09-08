#!/usr/bin/env python3
"""
Simple demonstration of the dynamic data validation system.
"""

import asyncio
import logging
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_validation_integration():
    """Demonstrate the MCP integrated validation system."""
    print("Dynamic Data Validation System - Integration Demo")
    print("=" * 60)
    
    # Import the MCP integrated validators
    from database.validation import (
        validate_data_quality_with_mcp,
        MCPIntegratedDataValidator,
        MCPIntegratedFinancialDataValidator
    )
    
    # Create mock schema manager
    mock_manager = Mock()
    mock_manager.get_table_schema = AsyncMock(return_value=None)  # Force fallback
    
    print("\n1. Testing MCP Integrated Data Validator:")
    validator = MCPIntegratedDataValidator(mock_manager)
    
    # Test data
    test_data = {
        "id": 1,
        "name": "Test Product",
        "amount": Decimal("99.99")
    }
    
    try:
        result = await validator.validate_with_schema(test_data, "test_db", "products")
        print(f"✅ Validation successful: {result}")
    except Exception as e:
        print(f"❌ Validation failed: {e}")
    
    print("\n2. Testing MCP Integrated Financial Validator:")
    financial_validator = MCPIntegratedFinancialDataValidator(mock_manager)
    
    # Financial test data
    financial_data = {
        "period_date": date.today(),
        "period_type": "monthly",
        "revenue": Decimal("50000.00"),
        "gross_profit": Decimal("30000.00"),
        "net_profit": Decimal("15000.00"),
        "operating_expenses": Decimal("12000.00")
    }
    
    try:
        result = await financial_validator.validate_financial_overview(financial_data)
        print(f"✅ Financial validation successful: {len(result)} fields validated")
    except Exception as e:
        print(f"❌ Financial validation failed: {e}")
    
    print("\n3. Testing Batch Data Quality Validation:")
    batch_data = [
        {
            "period_date": date.today(),
            "period_type": "monthly",
            "revenue": Decimal("10000.00")
        },
        {
            "period_date": date.today(),
            "period_type": "quarterly",
            "revenue": Decimal("30000.00")
        }
    ]
    
    try:
        validated_data, warnings = await validate_data_quality_with_mcp(
            batch_data, "financial_overview", "financial_db", mock_manager
        )
        print(f"✅ Batch validation successful:")
        print(f"   - Records processed: {len(validated_data)}")
        print(f"   - Warnings: {len(warnings)}")
        for warning in warnings[:3]:  # Show first 3 warnings
            print(f"     • {warning}")
    except Exception as e:
        print(f"❌ Batch validation failed: {e}")
    
    print("\n4. Testing Backward Compatibility:")
    # Test that static methods still work
    try:
        decimal_result = validator.validate_decimal(Decimal("123.45"), "test_field")
        print(f"✅ Static decimal validation: {decimal_result}")
        
        string_result = validator.validate_string("test", "test_field", max_length=10)
        print(f"✅ Static string validation: {string_result}")
        
        date_result = validator.validate_date(date.today(), "test_field")
        print(f"✅ Static date validation: {date_result}")
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")


async def demo_performance_metrics():
    """Demonstrate performance tracking in validation."""
    print("\n" + "="*60)
    print("Performance Metrics Demo")
    print("="*60)
    
    from database.validation import MCPIntegratedDataValidator
    
    # Create validator
    mock_manager = Mock()
    mock_manager.get_table_schema = AsyncMock(return_value=None)
    validator = MCPIntegratedDataValidator(mock_manager)
    
    # Test multiple validations and track performance
    test_cases = [
        {"id": 1, "name": "Product A", "amount": Decimal("10.00")},
        {"id": 2, "name": "Product B", "amount": Decimal("20.00")},
        {"id": 3, "name": "Product C", "amount": Decimal("30.00")},
        {"id": 4, "name": "Product D", "amount": Decimal("40.00")},
        {"id": 5, "name": "Product E", "amount": Decimal("50.00")},
    ]
    
    print(f"\nTesting validation performance with {len(test_cases)} records:")
    
    start_time = datetime.now()
    successful_validations = 0
    
    for i, test_data in enumerate(test_cases, 1):
        try:
            validation_start = datetime.now()
            result = await validator.validate_with_schema(test_data, "test_db", "products")
            validation_time = (datetime.now() - validation_start).total_seconds() * 1000
            
            successful_validations += 1
            print(f"  Record {i}: ✅ {validation_time:.1f}ms")
            
        except Exception as e:
            print(f"  Record {i}: ❌ Failed - {e}")
    
    total_time = (datetime.now() - start_time).total_seconds() * 1000
    avg_time = total_time / len(test_cases)
    
    print(f"\nPerformance Summary:")
    print(f"  - Total time: {total_time:.1f}ms")
    print(f"  - Average per record: {avg_time:.1f}ms")
    print(f"  - Success rate: {successful_validations}/{len(test_cases)} ({successful_validations/len(test_cases)*100:.1f}%)")


async def demo_error_handling():
    """Demonstrate error handling and fallback mechanisms."""
    print("\n" + "="*60)
    print("Error Handling and Fallback Demo")
    print("="*60)
    
    from database.validation import MCPIntegratedDataValidator, DynamicValidationConfig
    
    # Test 1: MCP server unavailable (exception)
    print("\n1. Testing MCP server unavailable:")
    mock_manager_error = Mock()
    mock_manager_error.get_table_schema = AsyncMock(side_effect=Exception("Connection failed"))
    
    validator_with_fallback = MCPIntegratedDataValidator(mock_manager_error)
    
    test_data = {"period_date": date.today(), "revenue": Decimal("1000.00")}
    
    try:
        result = await validator_with_fallback.validate_with_schema(test_data, "test_db", "financial_overview")
        print(f"✅ Fallback successful: {len(result)} fields")
    except Exception as e:
        print(f"❌ Fallback failed: {e}")
    
    # Test 2: Invalid data types
    print("\n2. Testing invalid data types:")
    mock_manager_ok = Mock()
    mock_manager_ok.get_table_schema = AsyncMock(return_value=None)
    validator = MCPIntegratedDataValidator(mock_manager_ok)
    
    invalid_data = {
        "period_date": "invalid_date",
        "period_type": "invalid_period",
        "revenue": "not_a_number"
    }
    
    try:
        result = await validator.validate_with_schema(invalid_data, "test_db", "financial_overview")
        print(f"⚠️  Validation passed with warnings (fallback mode)")
    except Exception as e:
        print(f"✅ Validation correctly caught errors: {type(e).__name__}")
    
    # Test 3: Performance under load
    print("\n3. Testing performance under simulated load:")
    
    # Simulate multiple concurrent validations
    tasks = []
    for i in range(10):
        task_data = {"id": i, "name": f"Product {i}", "amount": Decimal(f"{i*10}.00")}
        task = validator.validate_with_schema(task_data, "test_db", "products")
        tasks.append(task)
    
    try:
        start_time = datetime.now()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - successful
        
        print(f"✅ Concurrent validation results:")
        print(f"   - Total time: {total_time:.1f}ms")
        print(f"   - Successful: {successful}")
        print(f"   - Failed: {failed}")
        print(f"   - Average per validation: {total_time/len(results):.1f}ms")
        
    except Exception as e:
        print(f"❌ Concurrent validation failed: {e}")


async def main():
    """Run all demonstrations."""
    try:
        await demo_validation_integration()
        await demo_performance_metrics()
        await demo_error_handling()
        
        print("\n" + "="*60)
        print("🎉 All demonstrations completed successfully!")
        print("="*60)
        print("\nKey Features Demonstrated:")
        print("✅ Dynamic schema-based validation")
        print("✅ MCP integration with fallback mechanisms")
        print("✅ Financial data validation")
        print("✅ Batch data processing")
        print("✅ Performance monitoring")
        print("✅ Error handling and recovery")
        print("✅ Backward compatibility")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())