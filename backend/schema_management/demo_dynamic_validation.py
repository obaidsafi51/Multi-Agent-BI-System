#!/usr/bin/env python3
"""
Demonstration of the dynamic data validation system.
"""

import asyncio
import logging
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from schema_management.dynamic_validator import DynamicDataValidator, DynamicValidationConfig
from schema_management.enhanced_data_validator import EnhancedDataValidator
from schema_management.validation_reporter import ValidationReporter, format_validation_result_for_display
from schema_management.models import (
    TableSchema, ColumnInfo, IndexInfo, ForeignKeyInfo,
    ValidationResult, ValidationError, ValidationSeverity
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_schema():
    """Create a sample table schema for demonstration."""
    columns = [
        ColumnInfo(
            name="id",
            data_type="int",
            is_nullable=False,
            default_value=None,
            is_primary_key=True,
            is_foreign_key=False,
            max_length=None,
            precision=None,
            scale=None
        ),
        ColumnInfo(
            name="name",
            data_type="varchar",
            is_nullable=False,
            default_value=None,
            is_primary_key=False,
            is_foreign_key=False,
            max_length=100,
            precision=None,
            scale=None
        ),
        ColumnInfo(
            name="amount",
            data_type="decimal",
            is_nullable=True,
            default_value=None,
            is_primary_key=False,
            is_foreign_key=False,
            max_length=None,
            precision=10,
            scale=2
        ),
        ColumnInfo(
            name="category_id",
            data_type="int",
            is_nullable=True,
            default_value=None,
            is_primary_key=False,
            is_foreign_key=True,
            max_length=None,
            precision=None,
            scale=None
        )
    ]
    
    indexes = [
        IndexInfo(
            name="PRIMARY",
            columns=["id"],
            is_unique=True,
            is_primary=True,
            index_type="BTREE"
        ),
        IndexInfo(
            name="idx_name",
            columns=["name"],
            is_unique=True,
            is_primary=False,
            index_type="BTREE"
        )
    ]
    
    foreign_keys = [
        ForeignKeyInfo(
            name="fk_category",
            column="category_id",
            referenced_table="categories",
            referenced_column="id",
            on_delete="SET NULL",
            on_update="CASCADE"
        )
    ]
    
    return TableSchema(
        database="demo_db",
        table="products",
        columns=columns,
        indexes=indexes,
        primary_keys=["id"],
        foreign_keys=foreign_keys,
        constraints=[]
    )


async def demo_basic_validation():
    """Demonstrate basic dynamic validation."""
    print("\n" + "="*60)
    print("DEMO: Basic Dynamic Validation")
    print("="*60)
    
    # Create mock schema manager
    mock_manager = Mock()
    sample_schema = create_sample_schema()
    mock_manager.get_table_schema = AsyncMock(return_value=sample_schema)
    
    # Create validator
    config = DynamicValidationConfig(
        strict_mode=True,
        validate_types=True,
        validate_constraints=True,
        validate_relationships=True,
        allow_unknown_columns=False
    )
    validator = DynamicDataValidator(mock_manager, config)
    
    # Test valid data
    print("\n1. Testing VALID data:")
    valid_data = {
        "id": 1,
        "name": "Test Product",
        "amount": Decimal("99.99"),
        "category_id": 5
    }
    
    result = await validator.validate_against_schema(valid_data, "demo_db", "products")
    print(format_validation_result_for_display(result))
    
    # Test invalid data
    print("\n2. Testing INVALID data:")
    invalid_data = {
        "id": "not_an_integer",  # Wrong type
        "name": "A" * 150,       # Too long
        "amount": "invalid",     # Invalid decimal
        "category_id": "",       # Empty foreign key
        "unknown_field": "test"  # Unknown column
    }
    
    result = await validator.validate_against_schema(invalid_data, "demo_db", "products")
    print(format_validation_result_for_display(result))


async def demo_financial_validation():
    """Demonstrate financial data validation with MCP integration."""
    print("\n" + "="*60)
    print("DEMO: Financial Data Validation")
    print("="*60)
    
    # Create mock schema manager (will fallback to static validation)
    mock_manager = Mock()
    mock_manager.get_table_schema = AsyncMock(return_value=None)  # Force fallback
    
    # Create enhanced validator
    enhanced_validator = EnhancedDataValidator(mock_manager)
    
    # Test financial overview data
    print("\n1. Testing Financial Overview data:")
    financial_data = {
        "period_date": date.today(),
        "period_type": "monthly",
        "revenue": Decimal("50000.00"),
        "gross_profit": Decimal("30000.00"),
        "net_profit": Decimal("15000.00"),
        "operating_expenses": Decimal("12000.00")
    }
    
    result = await enhanced_validator.validate_financial_data(financial_data, "financial_overview")
    print(format_validation_result_for_display(result))
    
    # Test budget tracking with large variance
    print("\n2. Testing Budget Tracking with large variance:")
    budget_data = {
        "department": "Marketing",
        "period_date": date.today(),
        "budgeted_amount": Decimal("10000.00"),
        "actual_amount": Decimal("18000.00")  # 80% over budget
    }
    
    result = await enhanced_validator.validate_financial_data(budget_data, "budget_tracking")
    print(format_validation_result_for_display(result))


async def demo_validation_reporting():
    """Demonstrate validation reporting capabilities."""
    print("\n" + "="*60)
    print("DEMO: Validation Reporting")
    print("="*60)
    
    # Create reporter
    reporter = ValidationReporter()
    
    # Create sample validation results
    results = []
    
    # Result 1: Successful validation
    result1 = ValidationResult(
        is_valid=True,
        errors=[],
        warnings=[],
        validated_fields=["id", "name", "amount"],
        validation_time_ms=85
    )
    results.append(result1)
    
    # Result 2: Validation with errors
    result2 = ValidationResult(
        is_valid=False,
        errors=[
            ValidationError(
                field="amount",
                message="Invalid decimal value: abc",
                severity=ValidationSeverity.ERROR,
                error_code="INVALID_DECIMAL"
            ),
            ValidationError(
                field="name",
                message="String length 150 exceeds maximum 100",
                severity=ValidationSeverity.ERROR,
                error_code="STRING_TOO_LONG"
            )
        ],
        warnings=[],
        validated_fields=["id", "name", "amount"],
        validation_time_ms=120
    )
    results.append(result2)
    
    # Result 3: Validation with warnings
    result3 = ValidationResult(
        is_valid=True,
        errors=[],
        warnings=[
            ValidationError(
                field="variance_percentage",
                message="Large budget variance detected: 75%",
                severity=ValidationSeverity.WARNING,
                error_code="UNUSUAL_VARIANCE"
            )
        ],
        validated_fields=["department", "budgeted_amount", "actual_amount"],
        validation_time_ms=95
    )
    results.append(result3)
    
    # Generate detailed report for one result
    print("\n1. Detailed Report for Validation with Errors:")
    detailed_report = reporter.generate_detailed_report(
        result2,
        context={"database": "demo_db", "table": "products", "operation": "insert"}
    )
    
    print(f"Validation Summary:")
    print(f"  - Valid: {detailed_report['validation_summary']['is_valid']}")
    print(f"  - Errors: {detailed_report['validation_summary']['total_errors']}")
    print(f"  - Warnings: {detailed_report['validation_summary']['total_warnings']}")
    print(f"  - Time: {detailed_report['validation_summary']['validation_time_ms']}ms")
    print(f"  - Performance Rating: {detailed_report['performance_metrics']['performance_rating']}")
    print(f"  - Efficiency Score: {detailed_report['performance_metrics']['efficiency_score']:.1f}")
    
    print(f"\nRecommendations:")
    for rec in detailed_report['recommendations']:
        print(f"  - {rec}")
    
    # Generate summary report for all results
    print("\n2. Summary Report for Multiple Validations:")
    summary_report = reporter.generate_summary_report(
        results,
        context={"batch_operation": "bulk_insert", "total_records": 3}
    )
    
    metrics = summary_report['summary_metrics']
    print(f"Summary Metrics:")
    print(f"  - Total Validations: {metrics['total_validations']}")
    print(f"  - Success Rate: {metrics['success_rate']:.1f}%")
    print(f"  - Total Errors: {metrics['total_errors']}")
    print(f"  - Total Warnings: {metrics['total_warnings']}")
    print(f"  - Average Time: {metrics['average_validation_time_ms']:.1f}ms")
    
    perf = summary_report['performance_analysis']
    print(f"\nPerformance Analysis:")
    print(f"  - Fastest: {perf['fastest_validation_ms']}ms")
    print(f"  - Slowest: {perf['slowest_validation_ms']}ms")
    print(f"  - Distribution: {perf['performance_distribution']}")


async def demo_fallback_mechanisms():
    """Demonstrate fallback mechanisms when MCP is unavailable."""
    print("\n" + "="*60)
    print("DEMO: Fallback Mechanisms")
    print("="*60)
    
    # Create mock schema manager that fails
    mock_manager = Mock()
    mock_manager.get_table_schema = AsyncMock(side_effect=Exception("MCP server unavailable"))
    
    # Create validator with fallback enabled
    config = DynamicValidationConfig(fallback_to_static=True)
    validator = DynamicDataValidator(mock_manager, config)
    
    print("\n1. Testing fallback to static validation:")
    financial_data = {
        "period_date": date.today(),
        "period_type": "monthly",
        "revenue": Decimal("25000.00")
    }
    
    result = await validator.validate_against_schema(financial_data, "demo_db", "financial_overview")
    print(format_validation_result_for_display(result))
    
    # Test with fallback disabled
    print("\n2. Testing with fallback disabled:")
    config_no_fallback = DynamicValidationConfig(fallback_to_static=False)
    validator_no_fallback = DynamicDataValidator(mock_manager, config_no_fallback)
    
    result = await validator_no_fallback.validate_against_schema(financial_data, "demo_db", "financial_overview")
    print(format_validation_result_for_display(result))


async def main():
    """Run all demonstrations."""
    print("Dynamic Data Validation System Demonstration")
    print("=" * 60)
    
    try:
        await demo_basic_validation()
        await demo_financial_validation()
        await demo_validation_reporting()
        await demo_fallback_mechanisms()
        
        print("\n" + "="*60)
        print("All demonstrations completed successfully!")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())