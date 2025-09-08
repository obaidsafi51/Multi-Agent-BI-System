"""
Tests for dynamic data validation system.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime, date

from backend.schema_management.dynamic_validator import (
    DynamicDataValidator, DynamicValidationConfig
)
from backend.schema_management.enhanced_data_validator import (
    EnhancedDataValidator, EnhancedFinancialDataValidator
)
from backend.schema_management.validation_reporter import (
    ValidationReporter, format_validation_result_for_display
)
from backend.schema_management.models import (
    ValidationResult, ValidationError, ValidationWarning, ValidationSeverity,
    TableSchema, ColumnInfo, IndexInfo, ForeignKeyInfo, ConstraintInfo
)
from backend.database.validation import (
    validate_data_quality_with_mcp, MCPIntegratedDataValidator,
    MCPIntegratedFinancialDataValidator
)


class TestDynamicDataValidator:
    """Test cases for DynamicDataValidator."""
    
    @pytest.fixture
    def mock_schema_manager(self):
        """Create a mock schema manager."""
        manager = Mock()
        manager.get_table_schema = AsyncMock()
        return manager
    
    @pytest.fixture
    def sample_table_schema(self):
        """Create a sample table schema for testing."""
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
                name="created_at",
                data_type="datetime",
                is_nullable=False,
                default_value="CURRENT_TIMESTAMP",
                is_primary_key=False,
                is_foreign_key=False,
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
                on_delete="RESTRICT",
                on_update="CASCADE"
            )
        ]
        
        return TableSchema(
            database="test_db",
            table="test_table",
            columns=columns,
            indexes=indexes,
            primary_keys=["id"],
            foreign_keys=foreign_keys,
            constraints=[]
        )
    
    @pytest.fixture
    def validator(self, mock_schema_manager):
        """Create a DynamicDataValidator instance."""
        config = DynamicValidationConfig(
            strict_mode=False,
            validate_types=True,
            validate_constraints=True,
            validate_relationships=True,
            allow_unknown_columns=False,
            fallback_to_static=True
        )
        return DynamicDataValidator(mock_schema_manager, config)
    
    @pytest.mark.asyncio
    async def test_validate_against_schema_success(self, validator, mock_schema_manager, sample_table_schema):
        """Test successful validation against schema."""
        # Setup
        mock_schema_manager.get_table_schema.return_value = sample_table_schema
        
        data = {
            "id": 1,
            "name": "Test Item",
            "amount": Decimal("123.45"),
            "created_at": datetime.now()
        }
        
        # Execute
        result = await validator.validate_against_schema(data, "test_db", "test_table")
        
        # Assert
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.validated_fields) > 0
        assert "id" in result.validated_fields
        assert "name" in result.validated_fields
        assert result.validation_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_validate_against_schema_type_errors(self, validator, mock_schema_manager, sample_table_schema):
        """Test validation with type errors."""
        # Setup
        mock_schema_manager.get_table_schema.return_value = sample_table_schema
        
        data = {
            "id": "not_an_integer",  # Should be int
            "name": "A" * 200,       # Too long for varchar(100)
            "amount": "invalid_decimal",
            "created_at": "invalid_date"
        }
        
        # Execute
        result = await validator.validate_against_schema(data, "test_db", "test_table")
        
        # Assert
        assert not result.is_valid
        assert len(result.errors) > 0
        
        # Check for specific error types
        error_fields = [error.field for error in result.errors]
        assert "id" in error_fields
        assert "name" in error_fields
        assert "amount" in error_fields
        assert "created_at" in error_fields
    
    @pytest.mark.asyncio
    async def test_validate_against_schema_null_constraints(self, validator, mock_schema_manager, sample_table_schema):
        """Test validation with null constraint violations."""
        # Setup
        mock_schema_manager.get_table_schema.return_value = sample_table_schema
        
        data = {
            "id": None,    # Primary key cannot be null
            "name": None,  # Not nullable
            "amount": None,  # Nullable - should be OK
            "created_at": None  # Not nullable
        }
        
        # Execute
        result = await validator.validate_against_schema(data, "test_db", "test_table")
        
        # Assert
        assert not result.is_valid
        assert len(result.errors) >= 2  # id and name should have errors
        
        # Check that amount doesn't have a null error (it's nullable)
        amount_errors = [error for error in result.errors if error.field == "amount"]
        null_amount_errors = [error for error in amount_errors if "NULL" in error.error_code]
        assert len(null_amount_errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_against_schema_unknown_columns(self, validator, mock_schema_manager, sample_table_schema):
        """Test validation with unknown columns."""
        # Setup
        mock_schema_manager.get_table_schema.return_value = sample_table_schema
        
        data = {
            "id": 1,
            "name": "Test",
            "unknown_field": "should_cause_error",
            "another_unknown": 123
        }
        
        # Execute
        result = await validator.validate_against_schema(data, "test_db", "test_table")
        
        # Assert
        assert not result.is_valid
        assert len(result.errors) >= 2  # Two unknown columns
        
        unknown_errors = [error for error in result.errors if error.error_code == "UNKNOWN_COLUMN"]
        assert len(unknown_errors) == 2
    
    @pytest.mark.asyncio
    async def test_validate_against_schema_fallback(self, validator, mock_schema_manager):
        """Test fallback to static validation when schema not found."""
        # Setup
        mock_schema_manager.get_table_schema.return_value = None
        
        data = {
            "period_date": date.today(),
            "period_type": "monthly",
            "revenue": Decimal("10000.00")
        }
        
        # Execute
        result = await validator.validate_against_schema(data, "test_db", "financial_overview")
        
        # Assert
        # Should fallback to static validation and succeed for financial_overview
        assert result.is_valid or len(result.errors) == 0  # Depends on fallback behavior
        assert result.validation_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_validate_data_types_precision_scale(self, validator, sample_table_schema):
        """Test decimal precision and scale validation."""
        # Test data with precision/scale violations
        data = {
            "amount": Decimal("12345678.123")  # Exceeds precision(10) and scale(2)
        }
        
        # Execute
        errors, warnings, fields = await validator.validate_data_types(data, sample_table_schema)
        
        # Assert
        assert len(errors) >= 1
        precision_errors = [error for error in errors if "precision" in error.message.lower()]
        scale_errors = [error for error in errors if "scale" in error.message.lower()]
        assert len(precision_errors) > 0 or len(scale_errors) > 0
    
    @pytest.mark.asyncio
    async def test_validate_constraints_primary_key(self, validator, sample_table_schema):
        """Test primary key constraint validation."""
        # Test data missing primary key
        data = {
            "name": "Test",
            "amount": Decimal("100.00")
            # Missing 'id' primary key
        }
        
        # Execute with strict mode
        validator.config.strict_mode = True
        errors, warnings, fields = await validator.validate_constraints(data, sample_table_schema)
        
        # Assert
        pk_errors = [error for error in errors if error.error_code == "PRIMARY_KEY_MISSING"]
        assert len(pk_errors) > 0
    
    @pytest.mark.asyncio
    async def test_validate_relationships_foreign_keys(self, validator, sample_table_schema):
        """Test foreign key relationship validation."""
        # Test data with foreign key
        data = {
            "category_id": ""  # Empty string foreign key
        }
        
        # Execute
        errors, warnings, fields = await validator.validate_relationships(data, sample_table_schema)
        
        # Assert
        # Should generate warning for empty foreign key
        fk_warnings = [warning for warning in warnings if "foreign key" in warning.message.lower()]
        assert len(fk_warnings) > 0


class TestEnhancedDataValidator:
    """Test cases for EnhancedDataValidator."""
    
    @pytest.fixture
    def mock_schema_manager(self):
        """Create a mock schema manager."""
        manager = Mock()
        manager.get_table_schema = AsyncMock()
        return manager
    
    @pytest.fixture
    def enhanced_validator(self, mock_schema_manager):
        """Create an EnhancedDataValidator instance."""
        return EnhancedDataValidator(mock_schema_manager)
    
    @pytest.mark.asyncio
    async def test_validate_financial_data_success(self, enhanced_validator, mock_schema_manager):
        """Test successful financial data validation."""
        # Setup
        mock_schema_manager.get_table_schema.return_value = None  # Force fallback
        
        data = {
            "period_date": date.today(),
            "period_type": "monthly",
            "revenue": Decimal("10000.00"),
            "gross_profit": Decimal("6000.00"),
            "net_profit": Decimal("3000.00"),
            "operating_expenses": Decimal("2000.00")
        }
        
        # Execute
        result = await enhanced_validator.validate_financial_data(data, "financial_overview")
        
        # Assert
        assert result.is_valid
        assert len(result.validated_fields) > 0
    
    @pytest.mark.asyncio
    async def test_validate_financial_data_with_warnings(self, enhanced_validator, mock_schema_manager):
        """Test financial data validation with warnings."""
        # Setup
        mock_schema_manager.get_table_schema.return_value = None  # Force fallback
        
        data = {
            "department": "IT",
            "period_date": date.today(),
            "budgeted_amount": Decimal("1000.00"),
            "actual_amount": Decimal("2000.00")  # 100% over budget
        }
        
        # Execute
        result = await enhanced_validator.validate_financial_data(data, "budget_tracking")
        
        # Assert
        assert result.is_valid
        # Should have warnings about large variance
        variance_warnings = [w for w in result.warnings if "variance" in w.message.lower()]
        assert len(variance_warnings) > 0
    
    def test_backward_compatibility_methods(self, enhanced_validator):
        """Test backward compatibility wrapper methods."""
        # Test decimal validation
        result = enhanced_validator.validate_decimal(Decimal("123.45"), "test_field")
        assert result == Decimal("123.45")
        
        # Test string validation
        result = enhanced_validator.validate_string("test", "test_field", max_length=10)
        assert result == "test"
        
        # Test date validation
        test_date = date.today()
        result = enhanced_validator.validate_date(test_date, "test_field")
        assert result == test_date


class TestValidationReporter:
    """Test cases for ValidationReporter."""
    
    @pytest.fixture
    def reporter(self):
        """Create a ValidationReporter instance."""
        return ValidationReporter()
    
    @pytest.fixture
    def sample_validation_result(self):
        """Create a sample validation result."""
        errors = [
            ValidationError(
                field="amount",
                message="Invalid decimal value",
                severity=ValidationSeverity.ERROR,
                error_code="INVALID_DECIMAL"
            )
        ]
        
        warnings = [
            ValidationWarning(
                field="variance_percentage",
                message="Large budget variance detected: 75%",
                suggestion="Review budget planning"
            )
        ]
        
        return ValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            validated_fields=["amount", "variance_percentage", "department"],
            validation_time_ms=150
        )
    
    def test_generate_detailed_report(self, reporter, sample_validation_result):
        """Test detailed report generation."""
        context = {"database": "test_db", "table": "budget_tracking"}
        
        report = reporter.generate_detailed_report(sample_validation_result, context)
        
        # Assert report structure
        assert "timestamp" in report
        assert "validation_summary" in report
        assert "context" in report
        assert "errors" in report
        assert "warnings" in report
        assert "performance_metrics" in report
        assert "recommendations" in report
        
        # Assert validation summary
        summary = report["validation_summary"]
        assert summary["is_valid"] == False
        assert summary["total_errors"] == 1
        assert summary["total_warnings"] == 1
        assert summary["validation_time_ms"] == 150
        
        # Assert context
        assert report["context"]["database"] == "test_db"
        assert report["context"]["table"] == "budget_tracking"
        
        # Assert performance metrics
        perf = report["performance_metrics"]
        assert "performance_rating" in perf
        assert "efficiency_score" in perf
    
    def test_generate_summary_report(self, reporter):
        """Test summary report generation for multiple results."""
        # Create multiple validation results
        results = []
        for i in range(5):
            result = ValidationResult(
                is_valid=i % 2 == 0,  # Alternate valid/invalid
                errors=[ValidationError("field", "error", ValidationSeverity.ERROR)] if i % 2 == 1 else [],
                warnings=[],
                validated_fields=["field1", "field2"],
                validation_time_ms=100 + i * 50
            )
            results.append(result)
        
        summary = reporter.generate_summary_report(results)
        
        # Assert summary structure
        assert "summary_metrics" in summary
        assert "performance_analysis" in summary
        assert "error_analysis" in summary
        assert "recommendations" in summary
        
        # Assert metrics
        metrics = summary["summary_metrics"]
        assert metrics["total_validations"] == 5
        assert metrics["successful_validations"] == 3  # 0, 2, 4 are valid
        assert metrics["success_rate"] == 60.0
    
    def test_format_validation_result_for_display(self, sample_validation_result):
        """Test validation result formatting for display."""
        formatted = format_validation_result_for_display(sample_validation_result)
        
        assert "❌ INVALID" in formatted
        assert "Validation Time: 150ms" in formatted
        assert "Validated Fields: 3" in formatted
        assert "❌ Errors (1):" in formatted
        assert "⚠️  Warnings (1):" in formatted
        assert "amount: Invalid decimal value" in formatted


class TestMCPIntegratedValidators:
    """Test cases for MCP integrated validators."""
    
    @pytest.fixture
    def mock_schema_manager(self):
        """Create a mock schema manager."""
        manager = Mock()
        manager.get_table_schema = AsyncMock()
        return manager
    
    @pytest.mark.asyncio
    async def test_validate_data_quality_with_mcp(self, mock_schema_manager):
        """Test MCP integrated data quality validation."""
        # Setup
        data = [
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
        
        # Execute
        validated_data, warnings = await validate_data_quality_with_mcp(
            data, "financial_overview", "test_db", mock_schema_manager
        )
        
        # Assert
        assert len(validated_data) == 2
        assert isinstance(warnings, list)
    
    @pytest.mark.asyncio
    async def test_mcp_integrated_data_validator(self, mock_schema_manager):
        """Test MCPIntegratedDataValidator."""
        validator = MCPIntegratedDataValidator(mock_schema_manager)
        
        # Test with schema validation
        data = {"id": 1, "name": "test"}
        
        # Mock the enhanced validator to return a successful result
        with patch.object(validator, 'enhanced_validator') as mock_enhanced:
            mock_result = ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[],
                validated_fields=["id", "name"],
                validation_time_ms=100
            )
            mock_enhanced.validate_data_with_schema = AsyncMock(return_value=mock_result)
            
            result = await validator.validate_with_schema(data, "test_db", "test_table")
            assert result == data
    
    @pytest.mark.asyncio
    async def test_mcp_integrated_financial_validator(self, mock_schema_manager):
        """Test MCPIntegratedFinancialDataValidator."""
        validator = MCPIntegratedFinancialDataValidator(mock_schema_manager)
        
        data = {
            "period_date": date.today(),
            "period_type": "monthly",
            "revenue": Decimal("10000.00")
        }
        
        # Test fallback to static validation
        result = await validator.validate_financial_overview(data)
        assert isinstance(result, dict)


# Integration tests

@pytest.mark.integration
class TestDynamicValidationIntegration:
    """Integration tests for dynamic validation system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_validation_flow(self):
        """Test complete validation flow from data input to reporting."""
        # This would require actual MCP server connection
        # For now, we'll test with mocked components
        
        # Setup
        mock_schema_manager = Mock()
        mock_schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        validator = EnhancedDataValidator(mock_schema_manager)
        reporter = ValidationReporter()
        
        # Test data
        data = {
            "period_date": date.today(),
            "period_type": "monthly",
            "revenue": Decimal("10000.00"),
            "gross_profit": Decimal("6000.00")
        }
        
        # Execute validation
        result = await validator.validate_financial_data(data, "financial_overview")
        
        # Generate report
        report = reporter.generate_detailed_report(result, {
            "database": "financial_db",
            "table": "financial_overview"
        })
        
        # Assert
        assert result is not None
        assert report is not None
        assert "validation_summary" in report
        assert "recommendations" in report


if __name__ == "__main__":
    pytest.main([__file__])