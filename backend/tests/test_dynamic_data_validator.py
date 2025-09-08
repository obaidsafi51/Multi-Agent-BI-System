"""
Comprehensive tests for Dynamic Data Validator.

This module tests the dynamic validation system that uses real-time schema
information from the MCP server for data validation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, Any, List

from backend.schema_management.dynamic_validator import (
    DynamicDataValidator, DynamicValidationConfig
)
from backend.schema_management.manager import MCPSchemaManager
from backend.schema_management.models import (
    ValidationResult, ValidationError, ValidationWarning, ValidationSeverity,
    TableSchema, ColumnInfo, IndexInfo, ForeignKeyInfo
)


class TestDynamicValidationConfig:
    """Test cases for DynamicValidationConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = DynamicValidationConfig()
        
        assert config.strict_mode is False
        assert config.validate_types is True
        assert config.validate_constraints is True
        assert config.validate_relationships is True
        assert config.allow_unknown_columns is False
        assert config.fallback_to_static is True
        assert config.max_validation_time_ms == 5000
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = DynamicValidationConfig(
            strict_mode=True,
            validate_types=False,
            validate_constraints=False,
            validate_relationships=False,
            allow_unknown_columns=True,
            fallback_to_static=False,
            max_validation_time_ms=10000
        )
        
        assert config.strict_mode is True
        assert config.validate_types is False
        assert config.validate_constraints is False
        assert config.validate_relationships is False
        assert config.allow_unknown_columns is True
        assert config.fallback_to_static is False
        assert config.max_validation_time_ms == 10000


class TestDynamicDataValidator:
    """Test cases for DynamicDataValidator core functionality."""
    
    @pytest.fixture
    def mock_schema_manager(self):
        """Create a mock schema manager."""
        manager = Mock(spec=MCPSchemaManager)
        manager.get_table_schema = AsyncMock()
        return manager
    
    @pytest.fixture
    def validation_config(self):
        """Create validation configuration for testing."""
        return DynamicValidationConfig(
            strict_mode=False,
            validate_types=True,
            validate_constraints=True,
            validate_relationships=True,
            allow_unknown_columns=False,
            fallback_to_static=True
        )
    
    @pytest.fixture
    def sample_table_schema(self):
        """Create sample table schema for testing."""
        columns = [
            ColumnInfo(
                name="id",
                data_type="int",
                is_nullable=False,
                default_value=None,
                is_primary_key=True,
                is_foreign_key=False,
                is_auto_increment=True
            ),
            ColumnInfo(
                name="name",
                data_type="varchar",
                is_nullable=False,
                default_value=None,
                is_primary_key=False,
                is_foreign_key=False,
                max_length=100
            ),
            ColumnInfo(
                name="email",
                data_type="varchar",
                is_nullable=True,
                default_value=None,
                is_primary_key=False,
                is_foreign_key=False,
                max_length=255
            ),
            ColumnInfo(
                name="amount",
                data_type="decimal",
                is_nullable=True,
                default_value="0.00",
                is_primary_key=False,
                is_foreign_key=False,
                precision=10,
                scale=2
            ),
            ColumnInfo(
                name="category_id",
                data_type="int",
                is_nullable=True,
                default_value=None,
                is_primary_key=False,
                is_foreign_key=True
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
            database="test_db",
            table="test_table",
            columns=columns,
            indexes=[],
            primary_keys=["id"],
            foreign_keys=foreign_keys,
            constraints=[]
        )
    
    @pytest.fixture
    def validator(self, mock_schema_manager, validation_config):
        """Create DynamicDataValidator instance."""
        return DynamicDataValidator(mock_schema_manager, validation_config)
    
    @pytest.mark.asyncio
    async def test_validate_against_schema_success(self, validator, mock_schema_manager, sample_table_schema):
        """Test successful validation against schema."""
        mock_schema_manager.get_table_schema.return_value = sample_table_schema
        
        data = {
            "id": 1,
            "name": "Test User",
            "email": "test@example.com",
            "amount": Decimal("123.45"),
            "category_id": 5
        }
        
        result = await validator.validate_against_schema(data, "test_db", "test_table")
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.validated_fields) > 0
        assert "id" in result.validated_fields
        assert "name" in result.validated_fields
        assert result.validation_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_validate_against_schema_table_not_found(self, validator, mock_schema_manager):
        """Test validation when table is not found."""
        mock_schema_manager.get_table_schema.return_value = None
        
        data = {"id": 1, "name": "Test"}
        
        # With fallback enabled (default)
        result = await validator.validate_against_schema(data, "test_db", "nonexistent_table")
        
        # Should fallback to static validation
        assert isinstance(result, ValidationResult)
        # Result depends on fallback implementation
    
    @pytest.mark.asyncio
    async def test_validate_against_schema_no_fallback(self, validator, mock_schema_manager):
        """Test validation when table not found and no fallback."""
        validator.config.fallback_to_static = False
        mock_schema_manager.get_table_schema.return_value = None
        
        data = {"id": 1, "name": "Test"}
        
        result = await validator.validate_against_schema(data, "test_db", "nonexistent_table")
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "TABLE_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_validate_data_types_integer_validation(self, validator, sample_table_schema):
        """Test integer data type validation."""
        # Valid integer
        data = {"id": 42}
        errors, warnings, fields = await validator.validate_data_types(data, sample_table_schema)
        assert len(errors) == 0
        assert "id" in fields
        
        # Invalid integer
        data = {"id": "not_an_integer"}
        errors, warnings, fields = await validator.validate_data_types(data, sample_table_schema)
        assert len(errors) == 1
        assert errors[0].field == "id"
        assert errors[0].error_code == "INVALID_INTEGER"
    
    @pytest.mark.asyncio
    async def test_validate_data_types_decimal_validation(self, validator, sample_table_schema):
        """Test decimal data type validation."""
        # Valid decimal
        data = {"amount": Decimal("123.45")}
        errors, warnings, fields = await validator.validate_data_types(data, sample_table_schema)
        assert len(errors) == 0
        assert "amount" in fields
        
        # Valid decimal as string
        data = {"amount": "123.45"}
        errors, warnings, fields = await validator.validate_data_types(data, sample_table_schema)
        assert len(errors) == 0
        
        # Invalid decimal
        data = {"amount": "not_a_decimal"}
        errors, warnings, fields = await validator.validate_data_types(data, sample_table_schema)
        assert len(errors) == 1
        assert errors[0].field == "amount"
        assert errors[0].error_code == "INVALID_DECIMAL"
    
    @pytest.mark.asyncio
    async def test_validate_data_types_string_length(self, validator, sample_table_schema):
        """Test string length validation."""
        # Valid string within length
        data = {"name": "Valid Name"}
        errors, warnings, fields = await validator.validate_data_types(data, sample_table_schema)
        assert len(errors) == 0
        assert "name" in fields
        
        # String too long
        data = {"name": "A" * 150}  # Max length is 100
        errors, warnings, fields = await validator.validate_data_types(data, sample_table_schema)
        assert len(errors) == 1
        assert errors[0].field == "name"
        assert errors[0].error_code == "STRING_TOO_LONG"
    
    @pytest.mark.asyncio
    async def test_validate_data_types_null_handling(self, validator, sample_table_schema):
        """Test NULL value handling."""
        # NULL in nullable field - should be OK
        data = {"email": None}
        errors, warnings, fields = await validator.validate_data_types(data, sample_table_schema)
        assert len(errors) == 0
        
        # NULL in non-nullable field - should error
        data = {"name": None}
        errors, warnings, fields = await validator.validate_data_types(data, sample_table_schema)
        assert len(errors) == 1
        assert errors[0].field == "name"
        assert errors[0].error_code == "NULL_NOT_ALLOWED"
    
    @pytest.mark.asyncio
    async def test_validate_constraints_primary_key_missing(self, validator, sample_table_schema):
        """Test primary key constraint validation."""
        # Missing primary key in strict mode
        validator.config.strict_mode = True
        data = {"name": "Test", "email": "test@example.com"}  # Missing 'id'
        
        errors, warnings, fields = await validator.validate_constraints(data, sample_table_schema)
        
        assert len(errors) == 1
        assert errors[0].field == "id"
        assert errors[0].error_code == "PRIMARY_KEY_MISSING"
    
    @pytest.mark.asyncio
    async def test_validate_constraints_primary_key_null(self, validator, sample_table_schema):
        """Test primary key NULL validation."""
        data = {"id": None, "name": "Test"}
        
        errors, warnings, fields = await validator.validate_constraints(data, sample_table_schema)
        
        assert len(errors) == 1
        assert errors[0].field == "id"
        assert errors[0].error_code == "PRIMARY_KEY_NULL"
    
    @pytest.mark.asyncio
    async def test_validate_relationships_foreign_key_empty_string(self, validator, sample_table_schema):
        """Test foreign key relationship validation."""
        data = {"category_id": ""}  # Empty string foreign key
        
        errors, warnings, fields = await validator.validate_relationships(data, sample_table_schema)
        
        assert len(warnings) == 1
        assert warnings[0].field == "category_id"
        assert "foreign key" in warnings[0].message.lower()
    
    @pytest.mark.asyncio
    async def test_validate_relationships_valid_foreign_key(self, validator, sample_table_schema):
        """Test valid foreign key relationship."""
        data = {"category_id": 5}  # Valid foreign key value
        
        errors, warnings, fields = await validator.validate_relationships(data, sample_table_schema)
        
        assert len(errors) == 0
        assert "category_id" in fields
    
    @pytest.mark.asyncio
    async def test_fallback_validation_financial_overview(self, validator, mock_schema_manager):
        """Test fallback validation for financial_overview table."""
        mock_schema_manager.get_table_schema.return_value = None
        
        data = {
            "period_date": date.today(),
            "period_type": "monthly",
            "revenue": Decimal("10000.00"),
            "gross_profit": Decimal("6000.00"),
            "net_profit": Decimal("3000.00")
        }
        
        with patch.object(validator.static_financial_validator, 'validate_financial_overview') as mock_validate:
            mock_validate.return_value = data
            
            result = await validator._fallback_validation(data, "financial_overview")
            
            assert result.is_valid is True
            assert len(result.validated_fields) > 0
            mock_validate.assert_called_once_with(data)
    
    @pytest.mark.asyncio
    async def test_fallback_validation_unknown_table(self, validator, mock_schema_manager):
        """Test fallback validation for unknown table."""
        mock_schema_manager.get_table_schema.return_value = None
        
        data = {"field1": "value1", "field2": "value2"}
        
        result = await validator._fallback_validation(data, "unknown_table")
        
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "basic validation" in result.warnings[0].message.lower()
        assert set(result.validated_fields) == set(data.keys())
    
    @pytest.mark.asyncio
    async def test_validation_system_error_handling(self, validator, mock_schema_manager):
        """Test handling of validation system errors."""
        mock_schema_manager.get_table_schema.side_effect = Exception("Database connection error")
        
        data = {"id": 1, "name": "Test"}
        
        # With fallback enabled
        result = await validator.validate_against_schema(data, "test_db", "test_table")
        
        # Should fallback gracefully
        assert isinstance(result, ValidationResult)
    
    @pytest.mark.asyncio
    async def test_validation_system_error_no_fallback(self, validator, mock_schema_manager):
        """Test validation system error without fallback."""
        validator.config.fallback_to_static = False
        mock_schema_manager.get_table_schema.side_effect = Exception("Database connection error")
        
        data = {"id": 1, "name": "Test"}
        
        result = await validator.validate_against_schema(data, "test_db", "test_table")
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "VALIDATION_SYSTEM_ERROR"
    
    def test_elapsed_time_measurement(self, validator):
        """Test elapsed time measurement utility."""
        start_time = datetime.now()
        # Simulate some processing time
        import time
        time.sleep(0.01)
        
        elapsed_ms = validator._get_elapsed_ms(start_time)
        
        assert elapsed_ms >= 10  # At least 10ms
        assert elapsed_ms < 1000  # Less than 1 second


class TestDynamicDataValidatorIntegration:
    """Integration tests for DynamicDataValidator."""
    
    @pytest.fixture
    def mock_schema_manager(self):
        """Create a more realistic mock schema manager."""
        manager = Mock(spec=MCPSchemaManager)
        
        # Mock financial_overview schema
        financial_columns = [
            ColumnInfo("period_date", "date", False, None, False, False),
            ColumnInfo("period_type", "varchar", False, None, False, False, max_length=20),
            ColumnInfo("revenue", "decimal", False, "0.00", False, False, precision=15, scale=2),
            ColumnInfo("gross_profit", "decimal", True, None, False, False, precision=15, scale=2),
            ColumnInfo("net_profit", "decimal", True, None, False, False, precision=15, scale=2)
        ]
        
        financial_schema = TableSchema(
            database="financial_db",
            table="financial_overview",
            columns=financial_columns,
            indexes=[],
            primary_keys=["period_date", "period_type"],
            foreign_keys=[],
            constraints=[]
        )
        
        async def mock_get_table_schema(database: str, table: str):
            if database == "financial_db" and table == "financial_overview":
                return financial_schema
            return None
        
        manager.get_table_schema = mock_get_table_schema
        return manager
    
    @pytest.fixture
    def integration_validator(self, mock_schema_manager):
        """Create validator for integration testing."""
        config = DynamicValidationConfig(
            strict_mode=True,
            validate_types=True,
            validate_constraints=True,
            validate_relationships=True,
            allow_unknown_columns=False,
            fallback_to_static=True
        )
        return DynamicDataValidator(mock_schema_manager, config)
    
    @pytest.mark.asyncio
    async def test_complete_financial_validation_flow(self, integration_validator):
        """Test complete validation flow for financial data."""
        # Valid financial data
        valid_data = {
            "period_date": date(2024, 1, 1),
            "period_type": "monthly",
            "revenue": Decimal("50000.00"),
            "gross_profit": Decimal("30000.00"),
            "net_profit": Decimal("15000.00")
        }
        
        result = await integration_validator.validate_against_schema(
            valid_data, "financial_db", "financial_overview"
        )
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.validated_fields) == 5
        assert all(field in result.validated_fields for field in valid_data.keys())
    
    @pytest.mark.asyncio
    async def test_financial_validation_with_errors(self, integration_validator):
        """Test financial validation with multiple error types."""
        # Invalid financial data
        invalid_data = {
            "period_date": "invalid_date",  # Invalid date
            "period_type": "A" * 50,        # Too long string
            "revenue": "not_a_number",      # Invalid decimal
            "gross_profit": None,           # NULL in nullable field - OK
            "net_profit": Decimal("15000.00"),
            "unknown_field": "should_error"  # Unknown field
        }
        
        result = await integration_validator.validate_against_schema(
            invalid_data, "financial_db", "financial_overview"
        )
        
        assert result.is_valid is False
        assert len(result.errors) >= 3  # At least date, string length, and decimal errors
        
        # Check for specific error types
        error_codes = [error.error_code for error in result.errors]
        assert "STRING_TOO_LONG" in error_codes
        assert "INVALID_DECIMAL" in error_codes
    
    @pytest.mark.asyncio
    async def test_primary_key_constraint_validation(self, integration_validator):
        """Test primary key constraint validation in strict mode."""
        # Missing primary key fields
        incomplete_data = {
            "revenue": Decimal("50000.00"),
            "gross_profit": Decimal("30000.00")
            # Missing period_date and period_type (primary keys)
        }
        
        result = await integration_validator.validate_against_schema(
            incomplete_data, "financial_db", "financial_overview"
        )
        
        assert result.is_valid is False
        
        # Should have errors for missing primary key fields
        pk_errors = [error for error in result.errors if error.error_code == "PRIMARY_KEY_MISSING"]
        assert len(pk_errors) == 2  # Both primary key fields missing
    
    @pytest.mark.asyncio
    async def test_performance_validation_timing(self, integration_validator):
        """Test that validation completes within reasonable time."""
        data = {
            "period_date": date.today(),
            "period_type": "monthly",
            "revenue": Decimal("50000.00")
        }
        
        start_time = datetime.now()
        result = await integration_validator.validate_against_schema(
            data, "financial_db", "financial_overview"
        )
        end_time = datetime.now()
        
        actual_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Validation should complete quickly
        assert actual_time_ms < 1000  # Less than 1 second
        assert result.validation_time_ms <= actual_time_ms + 50  # Reasonable measurement accuracy


class TestDynamicDataValidatorEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.fixture
    def edge_case_schema(self):
        """Create schema with edge case column definitions."""
        columns = [
            ColumnInfo("tiny_string", "varchar", False, None, False, False, max_length=1),
            ColumnInfo("huge_decimal", "decimal", True, None, False, False, precision=65, scale=30),
            ColumnInfo("zero_scale", "decimal", True, None, False, False, precision=10, scale=0),
            ColumnInfo("nullable_pk", "int", True, None, True, False),  # Unusual: nullable primary key
        ]
        
        return TableSchema(
            database="edge_db",
            table="edge_table",
            columns=columns,
            indexes=[],
            primary_keys=["nullable_pk"],
            foreign_keys=[],
            constraints=[]
        )
    
    @pytest.fixture
    def edge_validator(self, edge_case_schema):
        """Create validator with edge case schema."""
        mock_manager = Mock(spec=MCPSchemaManager)
        mock_manager.get_table_schema = AsyncMock(return_value=edge_case_schema)
        
        config = DynamicValidationConfig(strict_mode=True)
        return DynamicDataValidator(mock_manager, config)
    
    @pytest.mark.asyncio
    async def test_minimum_string_length(self, edge_validator):
        """Test validation with minimum string length."""
        # Valid single character
        data = {"tiny_string": "A"}
        result = await edge_validator.validate_against_schema(data, "edge_db", "edge_table")
        
        type_errors = [e for e in result.errors if e.error_code == "STRING_TOO_LONG"]
        assert len(type_errors) == 0
        
        # Invalid - too long
        data = {"tiny_string": "AB"}
        result = await edge_validator.validate_against_schema(data, "edge_db", "edge_table")
        
        type_errors = [e for e in result.errors if e.error_code == "STRING_TOO_LONG"]
        assert len(type_errors) == 1
    
    @pytest.mark.asyncio
    async def test_high_precision_decimal(self, edge_validator):
        """Test validation with high precision decimal."""
        # Valid high precision decimal
        high_precision_value = "1234567890123456789012345678901234567890.123456789012345678901234567890"
        data = {"huge_decimal": high_precision_value}
        
        result = await edge_validator.validate_against_schema(data, "edge_db", "edge_table")
        
        # Should not error on decimal parsing (though precision might be lost)
        decimal_errors = [e for e in result.errors if e.error_code == "INVALID_DECIMAL"]
        assert len(decimal_errors) == 0
    
    @pytest.mark.asyncio
    async def test_zero_scale_decimal(self, edge_validator):
        """Test validation with zero scale decimal (integer-like)."""
        # Valid integer for zero scale decimal
        data = {"zero_scale": "12345"}
        result = await edge_validator.validate_against_schema(data, "edge_db", "edge_table")
        
        decimal_errors = [e for e in result.errors if e.error_code == "INVALID_DECIMAL"]
        assert len(decimal_errors) == 0
        
        # Decimal with fractional part should still be valid (will be truncated)
        data = {"zero_scale": "12345.67"}
        result = await edge_validator.validate_against_schema(data, "edge_db", "edge_table")
        
        decimal_errors = [e for e in result.errors if e.error_code == "INVALID_DECIMAL"]
        assert len(decimal_errors) == 0
    
    @pytest.mark.asyncio
    async def test_nullable_primary_key(self, edge_validator):
        """Test validation with nullable primary key (edge case)."""
        # NULL primary key - unusual but technically allowed in schema
        data = {"nullable_pk": None}
        result = await edge_validator.validate_against_schema(data, "edge_db", "edge_table")
        
        # Should still error because primary keys shouldn't be NULL
        pk_errors = [e for e in result.errors if e.error_code == "PRIMARY_KEY_NULL"]
        assert len(pk_errors) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])