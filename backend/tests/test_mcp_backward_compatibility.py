"""
Comprehensive backward compatibility tests for MCP Schema Management.

This module ensures that the MCP-based schema management system maintains
backward compatibility with existing static schema validation and APIs.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List, Optional

from backend.schema_management.manager import MCPSchemaManager
from backend.schema_management.dynamic_validator import DynamicDataValidator, DynamicValidationConfig
from backend.schema_management.config import MCPSchemaConfig
from backend.schema_management.models import (
    ValidationResult, ValidationError, ValidationSeverity,
    TableSchema, ColumnInfo
)

# Import legacy validation components for compatibility testing
try:
    from backend.database.validation import (
        DataValidator, FinancialDataValidator,
        ValidationError as LegacyValidationError
    )
except ImportError:
    # Create mock classes if legacy components don't exist
    class DataValidator:
        def validate_data(self, data): return data
    
    class FinancialDataValidator:
        def validate_financial_overview(self, data): return data
        def validate_cash_flow(self, data): return data
        def validate_budget_tracking(self, data): return data
        def validate_investment(self, data): return data
    
    class LegacyValidationError(Exception):
        pass


@pytest.mark.compatibility
class TestBackwardCompatibilityAPIs:
    """Test backward compatibility of APIs and interfaces."""
    
    @pytest.fixture
    def compatibility_manager(self):
        """Create manager for compatibility testing."""
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            fallback_enabled=True,
            cache_ttl=300,
            enable_caching=True
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            return MCPSchemaManager(config)
    
    @pytest.fixture
    def compatibility_validator(self, compatibility_manager):
        """Create validator for compatibility testing."""
        config = DynamicValidationConfig(
            fallback_to_static=True,
            strict_mode=False,
            validate_types=True,
            validate_constraints=True
        )
        return DynamicDataValidator(compatibility_manager, config)
    
    @pytest.mark.asyncio
    async def test_manager_api_compatibility(self, compatibility_manager):
        """Test that manager APIs remain compatible."""
        # Mock successful responses
        compatibility_manager.client._send_request = AsyncMock(return_value=[
            {"name": "test_db", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True}
        ])
        
        # Test that all expected methods exist and work
        assert hasattr(compatibility_manager, 'discover_databases')
        assert hasattr(compatibility_manager, 'get_tables')
        assert hasattr(compatibility_manager, 'get_table_schema')
        assert hasattr(compatibility_manager, 'validate_table_exists')
        assert hasattr(compatibility_manager, 'get_column_info')
        assert hasattr(compatibility_manager, 'refresh_schema_cache')
        assert hasattr(compatibility_manager, 'health_check')
        
        # Test method signatures and return types
        databases = await compatibility_manager.discover_databases()
        assert isinstance(databases, list)
        
        tables = await compatibility_manager.get_tables("test_db")
        assert isinstance(tables, list)
        
        exists = await compatibility_manager.validate_table_exists("test_db", "test_table")
        assert isinstance(exists, bool)
        
        health = await compatibility_manager.health_check()
        assert isinstance(health, bool)
    
    @pytest.mark.asyncio
    async def test_validator_api_compatibility(self, compatibility_validator):
        """Test that validator APIs remain compatible."""
        # Mock schema manager to return None (trigger fallback)
        compatibility_validator.schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        # Test that validation method exists and works
        assert hasattr(compatibility_validator, 'validate_against_schema')
        
        test_data = {"field1": "value1", "field2": 123}
        
        result = await compatibility_validator.validate_against_schema(
            test_data, "test_db", "test_table"
        )
        
        # Should return ValidationResult with expected structure
        assert isinstance(result, ValidationResult)
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'validated_fields')
        assert hasattr(result, 'validation_time_ms')
        
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        assert isinstance(result.validated_fields, list)
        assert isinstance(result.validation_time_ms, int)
    
    def test_configuration_compatibility(self):
        """Test that configuration remains compatible."""
        # Test default configuration creation
        config = MCPSchemaConfig()
        
        # Should have all expected attributes
        expected_attrs = [
            'mcp_server_url', 'connection_timeout', 'request_timeout',
            'max_retries', 'retry_delay', 'cache_ttl', 'enable_caching',
            'fallback_enabled'
        ]
        
        for attr in expected_attrs:
            assert hasattr(config, attr), f"Missing configuration attribute: {attr}"
        
        # Test environment-based configuration
        with patch.dict('os.environ', {
            'MCP_SERVER_URL': 'http://test:8000',
            'MCP_CACHE_TTL': '600',
            'MCP_FALLBACK_ENABLED': 'true'
        }):
            env_config = MCPSchemaConfig.from_env()
            assert env_config.mcp_server_url == 'http://test:8000'
            assert env_config.cache_ttl == 600
            assert env_config.fallback_enabled is True
    
    def test_model_compatibility(self):
        """Test that data models remain compatible."""
        # Test ValidationResult structure
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            validated_fields=['field1', 'field2'],
            validation_time_ms=50
        )
        
        # Should be serializable (for API compatibility)
        result_dict = {
            'is_valid': result.is_valid,
            'errors': [{'field': e.field, 'message': e.message} for e in result.errors],
            'warnings': [{'field': w.field, 'message': w.message} for w in result.warnings],
            'validated_fields': result.validated_fields,
            'validation_time_ms': result.validation_time_ms
        }
        
        assert isinstance(result_dict, dict)
        assert 'is_valid' in result_dict
        assert 'errors' in result_dict
        assert 'warnings' in result_dict


@pytest.mark.compatibility
class TestStaticValidationFallback:
    """Test fallback to static validation for backward compatibility."""
    
    @pytest.fixture
    def fallback_validator(self):
        """Create validator with static fallback enabled."""
        config = MCPSchemaConfig(fallback_enabled=True)
        
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            manager = MCPSchemaManager(config)
            
            validation_config = DynamicValidationConfig(
                fallback_to_static=True,
                strict_mode=False
            )
            
            return DynamicDataValidator(manager, validation_config)
    
    @pytest.mark.asyncio
    async def test_financial_overview_fallback(self, fallback_validator):
        """Test fallback to static financial overview validation."""
        # Mock schema manager to return None (trigger fallback)
        fallback_validator.schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        # Mock static financial validator
        with patch.object(fallback_validator.static_financial_validator, 'validate_financial_overview') as mock_validate:
            financial_data = {
                "period_date": date(2024, 1, 1),
                "period_type": "monthly",
                "revenue": Decimal("100000.00"),
                "gross_profit": Decimal("60000.00"),
                "net_profit": Decimal("35000.00")
            }
            
            mock_validate.return_value = financial_data
            
            result = await fallback_validator.validate_against_schema(
                financial_data, "financial_db", "financial_overview"
            )
            
            # Should succeed with static validation
            assert result.is_valid is True
            assert len(result.validated_fields) > 0
            mock_validate.assert_called_once_with(financial_data)
    
    @pytest.mark.asyncio
    async def test_cash_flow_fallback(self, fallback_validator):
        """Test fallback to static cash flow validation."""
        fallback_validator.schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        with patch.object(fallback_validator.static_financial_validator, 'validate_cash_flow') as mock_validate:
            cash_flow_data = {
                "period_date": date(2024, 1, 1),
                "operating_cash_flow": Decimal("25000.00"),
                "investing_cash_flow": Decimal("-10000.00"),
                "financing_cash_flow": Decimal("-5000.00"),
                "net_cash_flow": Decimal("10000.00")
            }
            
            mock_validate.return_value = cash_flow_data
            
            result = await fallback_validator.validate_against_schema(
                cash_flow_data, "financial_db", "cash_flow"
            )
            
            assert result.is_valid is True
            mock_validate.assert_called_once_with(cash_flow_data)
    
    @pytest.mark.asyncio
    async def test_budget_tracking_fallback(self, fallback_validator):
        """Test fallback to static budget tracking validation."""
        fallback_validator.schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        with patch.object(fallback_validator.static_financial_validator, 'validate_budget_tracking') as mock_validate:
            budget_data = {
                "period_date": date(2024, 1, 1),
                "category": "Marketing",
                "budgeted_amount": Decimal("50000.00"),
                "actual_amount": Decimal("45000.00"),
                "variance": Decimal("-5000.00")
            }
            
            mock_validate.return_value = budget_data
            
            result = await fallback_validator.validate_against_schema(
                budget_data, "financial_db", "budget_tracking"
            )
            
            assert result.is_valid is True
            mock_validate.assert_called_once_with(budget_data)
    
    @pytest.mark.asyncio
    async def test_investment_fallback(self, fallback_validator):
        """Test fallback to static investment validation."""
        fallback_validator.schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        with patch.object(fallback_validator.static_financial_validator, 'validate_investment') as mock_validate:
            investment_data = {
                "investment_date": date(2024, 1, 1),
                "investment_type": "Stock",
                "symbol": "AAPL",
                "quantity": 100,
                "price_per_share": Decimal("150.00"),
                "total_value": Decimal("15000.00")
            }
            
            mock_validate.return_value = investment_data
            
            result = await fallback_validator.validate_against_schema(
                investment_data, "financial_db", "investments"
            )
            
            assert result.is_valid is True
            mock_validate.assert_called_once_with(investment_data)
    
    @pytest.mark.asyncio
    async def test_unknown_table_fallback(self, fallback_validator):
        """Test fallback for unknown tables."""
        fallback_validator.schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        unknown_data = {
            "field1": "value1",
            "field2": 123,
            "field3": Decimal("456.78"),
            "field4": date.today()
        }
        
        result = await fallback_validator.validate_against_schema(
            unknown_data, "unknown_db", "unknown_table"
        )
        
        # Should succeed with basic validation
        assert result.is_valid is True
        assert len(result.warnings) >= 1  # Should warn about basic validation
        assert set(result.validated_fields) == set(unknown_data.keys())
    
    @pytest.mark.asyncio
    async def test_static_validation_error_handling(self, fallback_validator):
        """Test error handling in static validation fallback."""
        fallback_validator.schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        # Mock static validator to raise exception
        with patch.object(fallback_validator.static_financial_validator, 'validate_financial_overview') as mock_validate:
            mock_validate.side_effect = LegacyValidationError("Invalid financial data")
            
            invalid_data = {"invalid": "data"}
            
            result = await fallback_validator.validate_against_schema(
                invalid_data, "financial_db", "financial_overview"
            )
            
            assert result.is_valid is False
            assert len(result.errors) == 1
            assert result.errors[0].error_code == "STATIC_VALIDATION_ERROR"


@pytest.mark.compatibility
class TestLegacyDataFormats:
    """Test compatibility with legacy data formats and structures."""
    
    @pytest.fixture
    def format_validator(self):
        """Create validator for format compatibility testing."""
        config = MCPSchemaConfig(fallback_enabled=True)
        
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            manager = MCPSchemaManager(config)
            
            # Mock schema that accepts various data formats
            columns = [
                ColumnInfo("id", "int", False, None, True, False),
                ColumnInfo("amount", "decimal", True, None, False, False, precision=15, scale=2),
                ColumnInfo("date_field", "date", True, None, False, False),
                ColumnInfo("text_field", "varchar", True, None, False, False, max_length=255),
                ColumnInfo("flag_field", "boolean", True, None, False, False)
            ]
            
            schema = TableSchema(
                database="compat_db",
                table="compat_table",
                columns=columns,
                indexes=[],
                primary_keys=["id"],
                foreign_keys=[],
                constraints=[]
            )
            
            manager.get_table_schema = AsyncMock(return_value=schema)
            
            validation_config = DynamicValidationConfig(
                fallback_to_static=True,
                strict_mode=False
            )
            
            return DynamicDataValidator(manager, validation_config)
    
    @pytest.mark.asyncio
    async def test_string_number_compatibility(self, format_validator):
        """Test compatibility with string representations of numbers."""
        # Legacy systems might send numbers as strings
        legacy_data = {
            "id": "123",        # String integer
            "amount": "456.78", # String decimal
            "text_field": "test"
        }
        
        result = await format_validator.validate_against_schema(
            legacy_data, "compat_db", "compat_table"
        )
        
        # Should handle string numbers gracefully
        assert isinstance(result, ValidationResult)
        # Validation behavior depends on implementation
        # At minimum, should not crash
    
    @pytest.mark.asyncio
    async def test_date_format_compatibility(self, format_validator):
        """Test compatibility with various date formats."""
        date_formats = [
            {"date_field": "2024-01-01"},           # ISO format string
            {"date_field": date(2024, 1, 1)},       # Date object
            {"date_field": "01/01/2024"},           # US format
            {"date_field": "2024-01-01T00:00:00"},  # ISO datetime string
        ]
        
        for data in date_formats:
            data.update({"id": 1, "text_field": "test"})
            
            result = await format_validator.validate_against_schema(
                data, "compat_db", "compat_table"
            )
            
            # Should handle various date formats
            assert isinstance(result, ValidationResult)
    
    @pytest.mark.asyncio
    async def test_null_value_compatibility(self, format_validator):
        """Test compatibility with various null representations."""
        null_representations = [
            {"amount": None},           # Python None
            {"amount": ""},             # Empty string
            {"amount": "null"},         # String "null"
            {"amount": "NULL"},         # String "NULL"
        ]
        
        for data in null_representations:
            data.update({"id": 1, "text_field": "test"})
            
            result = await format_validator.validate_against_schema(
                data, "compat_db", "compat_table"
            )
            
            # Should handle various null representations
            assert isinstance(result, ValidationResult)
    
    @pytest.mark.asyncio
    async def test_boolean_compatibility(self, format_validator):
        """Test compatibility with various boolean representations."""
        boolean_representations = [
            {"flag_field": True},       # Python boolean
            {"flag_field": False},      # Python boolean
            {"flag_field": 1},          # Integer 1
            {"flag_field": 0},          # Integer 0
            {"flag_field": "true"},     # String "true"
            {"flag_field": "false"},    # String "false"
            {"flag_field": "1"},        # String "1"
            {"flag_field": "0"},        # String "0"
        ]
        
        for data in boolean_representations:
            data.update({"id": 1, "text_field": "test"})
            
            result = await format_validator.validate_against_schema(
                data, "compat_db", "compat_table"
            )
            
            # Should handle various boolean representations
            assert isinstance(result, ValidationResult)


@pytest.mark.compatibility
class TestMigrationCompatibility:
    """Test compatibility during migration from static to dynamic schema."""
    
    @pytest.fixture
    def migration_validator(self):
        """Create validator for migration testing."""
        config = MCPSchemaConfig(fallback_enabled=True)
        
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            manager = MCPSchemaManager(config)
            
            validation_config = DynamicValidationConfig(
                fallback_to_static=True,
                strict_mode=False
            )
            
            return DynamicDataValidator(manager, validation_config)
    
    @pytest.mark.asyncio
    async def test_gradual_migration_scenario(self, migration_validator):
        """Test gradual migration from static to dynamic validation."""
        # Scenario: Some tables have MCP schema, others fall back to static
        
        # Mock schema manager to return schema for some tables, None for others
        async def selective_schema_mock(database: str, table: str):
            if table == "migrated_table":
                # This table has been migrated to MCP
                columns = [
                    ColumnInfo("id", "int", False, None, True, False),
                    ColumnInfo("name", "varchar", False, None, False, False, max_length=100)
                ]
                return TableSchema(
                    database=database,
                    table=table,
                    columns=columns,
                    indexes=[],
                    primary_keys=["id"],
                    foreign_keys=[],
                    constraints=[]
                )
            else:
                # This table still uses static validation
                return None
        
        migration_validator.schema_manager.get_table_schema = AsyncMock(side_effect=selective_schema_mock)
        
        # Test migrated table (should use MCP validation)
        migrated_data = {"id": 1, "name": "Test User"}
        result1 = await migration_validator.validate_against_schema(
            migrated_data, "test_db", "migrated_table"
        )
        
        assert result1.is_valid is True
        assert len(result1.validated_fields) == 2
        
        # Test non-migrated table (should use static validation fallback)
        with patch.object(migration_validator.static_financial_validator, 'validate_financial_overview') as mock_validate:
            mock_validate.return_value = {"revenue": Decimal("100000.00")}
            
            legacy_data = {"revenue": Decimal("100000.00")}
            result2 = await migration_validator.validate_against_schema(
                legacy_data, "test_db", "financial_overview"
            )
            
            assert result2.is_valid is True
            mock_validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rollback_compatibility(self, migration_validator):
        """Test that system can rollback to static validation if needed."""
        # Simulate MCP server becoming unavailable
        migration_validator.schema_manager.get_table_schema = AsyncMock(
            side_effect=Exception("MCP server unavailable")
        )
        
        # Should fallback to static validation gracefully
        with patch.object(migration_validator.static_financial_validator, 'validate_financial_overview') as mock_validate:
            mock_validate.return_value = {"revenue": Decimal("50000.00")}
            
            rollback_data = {"revenue": Decimal("50000.00")}
            result = await migration_validator.validate_against_schema(
                rollback_data, "financial_db", "financial_overview"
            )
            
            # Should succeed with static validation
            assert result.is_valid is True
            mock_validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_performance_comparison(self, migration_validator):
        """Test that MCP validation performance is comparable to static validation."""
        # Mock fast MCP schema response
        columns = [
            ColumnInfo("id", "int", False, None, True, False),
            ColumnInfo("amount", "decimal", False, None, False, False)
        ]
        schema = TableSchema(
            database="perf_db",
            table="perf_table",
            columns=columns,
            indexes=[],
            primary_keys=["id"],
            foreign_keys=[],
            constraints=[]
        )
        
        migration_validator.schema_manager.get_table_schema = AsyncMock(return_value=schema)
        
        test_data = {"id": 1, "amount": Decimal("100.00")}
        
        # Test MCP validation performance
        start_time = datetime.now()
        for _ in range(10):
            result = await migration_validator.validate_against_schema(
                test_data, "perf_db", "perf_table"
            )
            assert result.is_valid is True
        mcp_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Test static validation performance (with fallback)
        migration_validator.schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        start_time = datetime.now()
        for _ in range(10):
            result = await migration_validator.validate_against_schema(
                test_data, "perf_db", "unknown_table"
            )
        static_time = (datetime.now() - start_time).total_seconds() * 1000
        
        print(f"MCP validation time: {mcp_time:.2f}ms")
        print(f"Static validation time: {static_time:.2f}ms")
        
        # MCP validation should be reasonably fast (allow 5x slower due to async overhead)
        assert mcp_time < static_time * 5, "MCP validation should not be significantly slower than static"


@pytest.mark.compatibility
class TestExistingCodeCompatibility:
    """Test compatibility with existing code that uses validation."""
    
    def test_validation_result_serialization(self):
        """Test that ValidationResult can be serialized for API responses."""
        # Create validation result
        errors = [
            ValidationError("field1", "Error message", ValidationSeverity.ERROR, "ERROR_CODE")
        ]
        
        result = ValidationResult(
            is_valid=False,
            errors=errors,
            warnings=[],
            validated_fields=["field1", "field2"],
            validation_time_ms=25
        )
        
        # Should be serializable to dict (for JSON API responses)
        serialized = {
            "is_valid": result.is_valid,
            "errors": [
                {
                    "field": error.field,
                    "message": error.message,
                    "severity": error.severity.value if hasattr(error.severity, 'value') else str(error.severity),
                    "error_code": error.error_code
                }
                for error in result.errors
            ],
            "warnings": [
                {
                    "field": warning.field,
                    "message": warning.message
                }
                for warning in result.warnings
            ],
            "validated_fields": result.validated_fields,
            "validation_time_ms": result.validation_time_ms
        }
        
        assert isinstance(serialized, dict)
        assert serialized["is_valid"] is False
        assert len(serialized["errors"]) == 1
        assert serialized["errors"][0]["field"] == "field1"
    
    def test_error_handling_compatibility(self):
        """Test that error handling remains compatible."""
        # Test that ValidationError has expected attributes
        error = ValidationError(
            field="test_field",
            message="Test error message",
            severity=ValidationSeverity.ERROR,
            error_code="TEST_ERROR"
        )
        
        # Should have all expected attributes for backward compatibility
        assert hasattr(error, 'field')
        assert hasattr(error, 'message')
        assert hasattr(error, 'severity')
        assert hasattr(error, 'error_code')
        
        assert error.field == "test_field"
        assert error.message == "Test error message"
        assert error.error_code == "TEST_ERROR"
    
    @pytest.mark.asyncio
    async def test_async_compatibility(self):
        """Test that async/await patterns remain compatible."""
        # Test that all validation methods are properly async
        config = MCPSchemaConfig(fallback_enabled=True)
        
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            manager = MCPSchemaManager(config)
            validator = DynamicDataValidator(manager, DynamicValidationConfig())
            
            # All these should be awaitable
            manager.client._send_request = AsyncMock(return_value=[])
            manager.get_table_schema = AsyncMock(return_value=None)
            
            # Should work with async/await
            databases = await manager.discover_databases()
            tables = await manager.get_tables("test_db")
            result = await validator.validate_against_schema({}, "test_db", "test_table")
            
            assert isinstance(databases, list)
            assert isinstance(tables, list)
            assert isinstance(result, ValidationResult)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "compatibility"])