"""
End-to-end validation tests for MCP Schema Management system.

This module contains comprehensive end-to-end tests that validate the complete
workflow from schema discovery through data validation using real-world scenarios.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
import json

from backend.schema_management.manager import MCPSchemaManager
from backend.schema_management.client import EnhancedMCPClient
from backend.schema_management.dynamic_validator import DynamicDataValidator, DynamicValidationConfig
from backend.schema_management.config import MCPSchemaConfig
from backend.schema_management.models import (
    ValidationResult, ValidationError, ValidationWarning, ValidationSeverity,
    DatabaseInfo, TableInfo, TableSchema, ColumnInfo, IndexInfo, ForeignKeyInfo,
    DetailedTableSchema, CacheStats
)


@pytest.mark.e2e
class TestEndToEndValidationWorkflows:
    """End-to-end validation workflow tests."""
    
    @pytest.fixture
    def e2e_config(self):
        """Create configuration for end-to-end testing."""
        return MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            connection_timeout=10,
            request_timeout=30,
            max_retries=3,
            retry_delay=1.0,
            cache_ttl=300,
            enable_caching=True,
            fallback_enabled=True
        )
    
    @pytest.fixture
    def financial_schema_setup(self):
        """Create comprehensive financial schema for testing."""
        # Financial Overview Table
        financial_columns = [
            ColumnInfo("id", "int", False, None, True, False, is_auto_increment=True),
            ColumnInfo("company_id", "int", False, None, False, True),
            ColumnInfo("period_date", "date", False, None, False, False),
            ColumnInfo("period_type", "varchar", False, None, False, False, max_length=20),
            ColumnInfo("revenue", "decimal", False, "0.00", False, False, precision=15, scale=2),
            ColumnInfo("cost_of_goods_sold", "decimal", True, None, False, False, precision=15, scale=2),
            ColumnInfo("gross_profit", "decimal", True, None, False, False, precision=15, scale=2),
            ColumnInfo("operating_expenses", "decimal", True, None, False, False, precision=15, scale=2),
            ColumnInfo("ebitda", "decimal", True, None, False, False, precision=15, scale=2),
            ColumnInfo("net_profit", "decimal", True, None, False, False, precision=15, scale=2),
            ColumnInfo("created_at", "timestamp", False, "CURRENT_TIMESTAMP", False, False),
            ColumnInfo("updated_at", "timestamp", False, "CURRENT_TIMESTAMP", False, False)
        ]
        
        financial_foreign_keys = [
            ForeignKeyInfo("fk_company", "company_id", "companies", "id", "CASCADE", "CASCADE")
        ]
        
        financial_schema = TableSchema(
            database="financial_db",
            table="financial_overview",
            columns=financial_columns,
            indexes=[],
            primary_keys=["id"],
            foreign_keys=financial_foreign_keys,
            constraints=[]
        )
        
        # Cash Flow Table
        cash_flow_columns = [
            ColumnInfo("id", "int", False, None, True, False, is_auto_increment=True),
            ColumnInfo("financial_overview_id", "int", False, None, False, True),
            ColumnInfo("operating_cash_flow", "decimal", False, "0.00", False, False, precision=15, scale=2),
            ColumnInfo("investing_cash_flow", "decimal", False, "0.00", False, False, precision=15, scale=2),
            ColumnInfo("financing_cash_flow", "decimal", False, "0.00", False, False, precision=15, scale=2),
            ColumnInfo("net_cash_flow", "decimal", True, None, False, False, precision=15, scale=2),
            ColumnInfo("cash_at_beginning", "decimal", True, None, False, False, precision=15, scale=2),
            ColumnInfo("cash_at_end", "decimal", True, None, False, False, precision=15, scale=2)
        ]
        
        cash_flow_foreign_keys = [
            ForeignKeyInfo("fk_financial_overview", "financial_overview_id", "financial_overview", "id", "CASCADE", "CASCADE")
        ]
        
        cash_flow_schema = TableSchema(
            database="financial_db",
            table="cash_flow",
            columns=cash_flow_columns,
            indexes=[],
            primary_keys=["id"],
            foreign_keys=cash_flow_foreign_keys,
            constraints=[]
        )
        
        return {
            "financial_overview": financial_schema,
            "cash_flow": cash_flow_schema
        }
    
    @pytest.fixture
    def e2e_manager(self, e2e_config, financial_schema_setup):
        """Create end-to-end manager with comprehensive schema setup."""
        with patch('backend.schema_management.manager.EnhancedMCPClient') as mock_client_class:
            mock_client = Mock(spec=EnhancedMCPClient)
            mock_client_class.return_value = mock_client
            
            # Mock successful connection
            mock_client.connect = AsyncMock(return_value=True)
            mock_client.health_check = AsyncMock(return_value=True)
            
            # Mock database discovery
            mock_databases = [
                {"name": "financial_db", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True, "table_count": 10},
                {"name": "analytics_db", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True, "table_count": 5}
            ]
            
            # Mock table discovery
            mock_tables = [
                {"name": "financial_overview", "type": "BASE TABLE", "engine": "InnoDB", "rows": 5000, "size_mb": 25.5},
                {"name": "cash_flow", "type": "BASE TABLE", "engine": "InnoDB", "rows": 5000, "size_mb": 20.2},
                {"name": "budget_tracking", "type": "BASE TABLE", "engine": "InnoDB", "rows": 3000, "size_mb": 15.8}
            ]
            
            async def mock_send_request(method: str, params: Dict[str, Any]):
                if method == "discover_databases_tool":
                    return mock_databases
                elif method == "discover_tables_tool":
                    return mock_tables
                else:
                    return {"error": f"Unknown method: {method}"}
            
            mock_client._send_request = AsyncMock(side_effect=mock_send_request)
            
            # Mock detailed schema responses
            async def mock_get_table_schema_detailed(database: str, table: str):
                if database == "financial_db" and table in financial_schema_setup:
                    schema = financial_schema_setup[table]
                    sample_data = []
                    
                    if table == "financial_overview":
                        sample_data = [
                            {"id": 1, "company_id": 1, "period_date": "2024-01-01", "period_type": "monthly", "revenue": "100000.00"},
                            {"id": 2, "company_id": 1, "period_date": "2024-02-01", "period_type": "monthly", "revenue": "110000.00"}
                        ]
                    elif table == "cash_flow":
                        sample_data = [
                            {"id": 1, "financial_overview_id": 1, "operating_cash_flow": "25000.00", "investing_cash_flow": "-10000.00"},
                            {"id": 2, "financial_overview_id": 2, "operating_cash_flow": "28000.00", "investing_cash_flow": "-12000.00"}
                        ]
                    
                    return DetailedTableSchema(
                        table_schema=schema,
                        sample_data=sample_data,
                        discovery_time_ms=150
                    )
                return None
            
            mock_client.get_table_schema_detailed = AsyncMock(side_effect=mock_get_table_schema_detailed)
            
            manager = MCPSchemaManager(e2e_config)
            manager.client = mock_client
            return manager
    
    @pytest.fixture
    def e2e_validator(self, e2e_manager):
        """Create end-to-end validator."""
        config = DynamicValidationConfig(
            strict_mode=True,
            validate_types=True,
            validate_constraints=True,
            validate_relationships=True,
            allow_unknown_columns=False,
            fallback_to_static=True
        )
        return DynamicDataValidator(e2e_manager, config)
    
    @pytest.mark.asyncio
    async def test_complete_financial_data_workflow(self, e2e_validator):
        """Test complete workflow with realistic financial data."""
        # Step 1: Validate financial overview data
        financial_data = {
            "company_id": 1,
            "period_date": date(2024, 3, 1),
            "period_type": "monthly",
            "revenue": Decimal("150000.00"),
            "cost_of_goods_sold": Decimal("90000.00"),
            "gross_profit": Decimal("60000.00"),
            "operating_expenses": Decimal("35000.00"),
            "ebitda": Decimal("25000.00"),
            "net_profit": Decimal("18000.00")
        }
        
        financial_result = await e2e_validator.validate_against_schema(
            financial_data, "financial_db", "financial_overview"
        )
        
        assert financial_result.is_valid is True
        assert len(financial_result.errors) == 0
        assert len(financial_result.validated_fields) >= 8
        
        # Step 2: Validate related cash flow data
        cash_flow_data = {
            "financial_overview_id": 1,  # References the financial overview
            "operating_cash_flow": Decimal("22000.00"),
            "investing_cash_flow": Decimal("-15000.00"),
            "financing_cash_flow": Decimal("-5000.00"),
            "net_cash_flow": Decimal("2000.00"),
            "cash_at_beginning": Decimal("50000.00"),
            "cash_at_end": Decimal("52000.00")
        }
        
        cash_flow_result = await e2e_validator.validate_against_schema(
            cash_flow_data, "financial_db", "cash_flow"
        )
        
        assert cash_flow_result.is_valid is True
        assert len(cash_flow_result.errors) == 0
        assert len(cash_flow_result.validated_fields) >= 7
        
        # Step 3: Verify validation performance
        assert financial_result.validation_time_ms < 100
        assert cash_flow_result.validation_time_ms < 100
    
    @pytest.mark.asyncio
    async def test_cross_table_relationship_validation(self, e2e_validator):
        """Test validation across related tables."""
        # Test foreign key relationship validation
        cash_flow_data = {
            "financial_overview_id": 999,  # Non-existent foreign key
            "operating_cash_flow": Decimal("22000.00"),
            "investing_cash_flow": Decimal("-15000.00"),
            "financing_cash_flow": Decimal("-5000.00")
        }
        
        result = await e2e_validator.validate_against_schema(
            cash_flow_data, "financial_db", "cash_flow"
        )
        
        # Should validate structure but may warn about foreign key
        assert isinstance(result, ValidationResult)
        assert "financial_overview_id" in result.validated_fields
    
    @pytest.mark.asyncio
    async def test_batch_validation_workflow(self, e2e_validator):
        """Test batch validation of multiple records."""
        # Create batch of financial records
        batch_data = []
        for i in range(12):  # 12 months of data
            month_data = {
                "company_id": 1,
                "period_date": date(2024, i + 1, 1),
                "period_type": "monthly",
                "revenue": Decimal(f"{100000 + i * 5000}.00"),
                "cost_of_goods_sold": Decimal(f"{60000 + i * 3000}.00"),
                "gross_profit": Decimal(f"{40000 + i * 2000}.00"),
                "operating_expenses": Decimal(f"{25000 + i * 1000}.00"),
                "net_profit": Decimal(f"{15000 + i * 1000}.00")
            }
            batch_data.append(month_data)
        
        # Validate batch
        validation_tasks = [
            e2e_validator.validate_against_schema(data, "financial_db", "financial_overview")
            for data in batch_data
        ]
        
        results = await asyncio.gather(*validation_tasks)
        
        # All should be valid
        assert len(results) == 12
        assert all(result.is_valid for result in results)
        
        # Check performance
        total_validation_time = sum(result.validation_time_ms for result in results)
        avg_validation_time = total_validation_time / len(results)
        assert avg_validation_time < 50  # Average under 50ms per validation
    
    @pytest.mark.asyncio
    async def test_complex_error_scenarios(self, e2e_validator):
        """Test complex error scenarios with multiple validation issues."""
        # Data with multiple types of errors
        complex_error_data = {
            "company_id": "not_an_integer",      # Type error
            "period_date": "invalid_date",       # Type error
            "period_type": "A" * 50,             # Length error (max 20)
            "revenue": "not_a_decimal",          # Type error
            "cost_of_goods_sold": None,          # Valid (nullable)
            "gross_profit": Decimal("-1000.00"), # Valid but unusual (negative)
            "operating_expenses": Decimal("99999999999999999.99"),  # Precision error
            "unknown_field": "should_be_ignored" # Unknown field
        }
        
        result = await e2e_validator.validate_against_schema(
            complex_error_data, "financial_db", "financial_overview"
        )
        
        assert result.is_valid is False
        assert len(result.errors) >= 4  # Multiple errors expected
        
        # Check for specific error types
        error_codes = [error.error_code for error in result.errors]
        assert "INVALID_INTEGER" in error_codes
        assert "STRING_TOO_LONG" in error_codes
        assert "INVALID_DECIMAL" in error_codes
        
        # Should still have some validated fields
        assert len(result.validated_fields) > 0
    
    @pytest.mark.asyncio
    async def test_schema_evolution_handling(self, e2e_manager, e2e_validator):
        """Test handling of schema evolution scenarios."""
        # Simulate schema change by updating the mock
        updated_columns = [
            ColumnInfo("id", "int", False, None, True, False, is_auto_increment=True),
            ColumnInfo("company_id", "int", False, None, False, True),
            ColumnInfo("period_date", "date", False, None, False, False),
            ColumnInfo("period_type", "varchar", False, None, False, False, max_length=30),  # Increased length
            ColumnInfo("revenue", "decimal", False, "0.00", False, False, precision=18, scale=2),  # Increased precision
            ColumnInfo("new_field", "varchar", True, None, False, False, max_length=100)  # New field
        ]
        
        updated_schema = TableSchema(
            database="financial_db",
            table="financial_overview",
            columns=updated_columns,
            indexes=[],
            primary_keys=["id"],
            foreign_keys=[],
            constraints=[]
        )
        
        # Update the mock to return new schema
        async def updated_mock_get_schema(database: str, table: str):
            if database == "financial_db" and table == "financial_overview":
                return DetailedTableSchema(
                    table_schema=updated_schema,
                    sample_data=[],
                    discovery_time_ms=150
                )
            return None
        
        e2e_manager.client.get_table_schema_detailed = AsyncMock(side_effect=updated_mock_get_schema)
        
        # Clear cache to force schema refresh
        await e2e_manager.refresh_schema_cache("all")
        
        # Test with data that uses new schema features
        evolved_data = {
            "company_id": 1,
            "period_date": date(2024, 4, 1),
            "period_type": "quarterly_extended_period",  # Longer than old limit
            "revenue": Decimal("999999999999999999.99"),  # Higher precision
            "new_field": "This is a new field value"
        }
        
        result = await e2e_validator.validate_against_schema(
            evolved_data, "financial_db", "financial_overview"
        )
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert "new_field" in result.validated_fields
    
    @pytest.mark.asyncio
    async def test_concurrent_validation_with_caching(self, e2e_validator, e2e_manager):
        """Test concurrent validation with cache performance."""
        # Create different data sets for concurrent validation
        data_sets = []
        for i in range(20):
            data = {
                "company_id": i % 5 + 1,
                "period_date": date(2024, (i % 12) + 1, 1),
                "period_type": "monthly",
                "revenue": Decimal(f"{100000 + i * 1000}.00"),
                "net_profit": Decimal(f"{15000 + i * 100}.00")
            }
            data_sets.append(data)
        
        # Run concurrent validations
        start_time = datetime.now()
        
        validation_tasks = [
            e2e_validator.validate_against_schema(data, "financial_db", "financial_overview")
            for data in data_sets
        ]
        
        results = await asyncio.gather(*validation_tasks)
        
        end_time = datetime.now()
        total_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Verify results
        assert len(results) == 20
        assert all(result.is_valid for result in results)
        
        # Check performance
        avg_time_per_validation = total_time_ms / len(results)
        assert avg_time_per_validation < 25  # Should be fast due to caching
        
        # Verify cache effectiveness
        cache_stats = e2e_manager.get_cache_stats()
        assert cache_stats.hit_rate > 0.5  # At least 50% cache hit rate
    
    @pytest.mark.asyncio
    async def test_validation_with_business_rules(self, e2e_validator):
        """Test validation with business logic rules."""
        # Test data that passes schema validation but might fail business rules
        business_data = {
            "company_id": 1,
            "period_date": date(2024, 5, 1),
            "period_type": "monthly",
            "revenue": Decimal("100000.00"),
            "cost_of_goods_sold": Decimal("120000.00"),  # Higher than revenue (unusual)
            "gross_profit": Decimal("-20000.00"),        # Negative (calculated correctly)
            "operating_expenses": Decimal("50000.00"),
            "net_profit": Decimal("-70000.00")           # Large loss
        }
        
        result = await e2e_validator.validate_against_schema(
            business_data, "financial_db", "financial_overview"
        )
        
        # Should pass schema validation
        assert result.is_valid is True
        assert len(result.errors) == 0
        
        # But might have warnings about unusual values
        # (This would depend on business rule implementation)
        assert len(result.validated_fields) >= 6


@pytest.mark.e2e
class TestEndToEndErrorRecovery:
    """End-to-end error recovery and resilience tests."""
    
    @pytest.fixture
    def resilience_manager(self):
        """Create manager for resilience testing."""
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            connection_timeout=2,
            request_timeout=5,
            max_retries=3,
            retry_delay=0.5,
            cache_ttl=60,
            enable_caching=True,
            fallback_enabled=True
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient') as mock_client_class:
            mock_client = Mock(spec=EnhancedMCPClient)
            mock_client_class.return_value = mock_client
            
            manager = MCPSchemaManager(config)
            manager.client = mock_client
            return manager
    
    @pytest.mark.asyncio
    async def test_recovery_from_temporary_server_failure(self, resilience_manager):
        """Test recovery from temporary server failures."""
        call_count = 0
        
        async def intermittent_failure_mock(method: str, params: Dict[str, Any]):
            nonlocal call_count
            call_count += 1
            
            if call_count <= 2:
                # First two calls fail
                raise Exception("Temporary server error")
            else:
                # Subsequent calls succeed
                return [{"name": "recovered_db", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True}]
        
        resilience_manager.client._send_request = AsyncMock(side_effect=intermittent_failure_mock)
        
        # Should eventually succeed after retries
        databases = await resilience_manager.discover_databases()
        
        # Should fallback gracefully on failures, then succeed
        assert isinstance(databases, list)
        # With fallback enabled, should return empty list on failure
        # But if retries succeed, should return actual data
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_under_load(self, resilience_manager):
        """Test graceful degradation under high load."""
        # Simulate slow responses under load
        async def slow_response_mock(method: str, params: Dict[str, Any]):
            await asyncio.sleep(0.1)  # Simulate slow response
            return [{"name": "slow_db", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True}]
        
        resilience_manager.client._send_request = AsyncMock(side_effect=slow_response_mock)
        
        # Run multiple concurrent operations
        tasks = [resilience_manager.discover_databases() for _ in range(10)]
        
        start_time = datetime.now()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = datetime.now()
        
        total_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Should handle load gracefully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 5  # At least half should succeed
        
        # Should not take too long due to concurrent execution
        assert total_time_ms < 2000  # Under 2 seconds for 10 operations


@pytest.mark.e2e
class TestEndToEndDataIntegrity:
    """End-to-end data integrity and consistency tests."""
    
    @pytest.fixture
    def integrity_validator(self):
        """Create validator for data integrity testing."""
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            cache_ttl=300,
            enable_caching=True,
            fallback_enabled=True
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            manager = MCPSchemaManager(config)
            
            # Create comprehensive schema with constraints
            columns = [
                ColumnInfo("id", "int", False, None, True, False, is_auto_increment=True),
                ColumnInfo("email", "varchar", False, None, False, False, max_length=255),
                ColumnInfo("age", "int", True, None, False, False),
                ColumnInfo("balance", "decimal", False, "0.00", False, False, precision=10, scale=2),
                ColumnInfo("status", "enum", False, "'active'", False, False),
                ColumnInfo("created_at", "timestamp", False, "CURRENT_TIMESTAMP", False, False)
            ]
            
            schema = TableSchema(
                database="integrity_db",
                table="users",
                columns=columns,
                indexes=[],
                primary_keys=["id"],
                foreign_keys=[],
                constraints=[]
            )
            
            manager.get_table_schema = AsyncMock(return_value=schema)
            
            validation_config = DynamicValidationConfig(
                strict_mode=True,
                validate_types=True,
                validate_constraints=True,
                validate_relationships=True
            )
            
            return DynamicDataValidator(manager, validation_config)
    
    @pytest.mark.asyncio
    async def test_data_type_integrity_validation(self, integrity_validator):
        """Test comprehensive data type integrity validation."""
        test_cases = [
            # Valid cases
            {
                "data": {"email": "test@example.com", "age": 25, "balance": Decimal("1000.50")},
                "should_be_valid": True,
                "description": "Valid data types"
            },
            # Type errors
            {
                "data": {"email": "test@example.com", "age": "not_an_integer", "balance": Decimal("1000.50")},
                "should_be_valid": False,
                "description": "Invalid integer type"
            },
            {
                "data": {"email": "test@example.com", "age": 25, "balance": "not_a_decimal"},
                "should_be_valid": False,
                "description": "Invalid decimal type"
            },
            # Boundary cases
            {
                "data": {"email": "a" * 256, "age": 25, "balance": Decimal("1000.50")},  # Email too long
                "should_be_valid": False,
                "description": "String length exceeded"
            },
            {
                "data": {"email": "test@example.com", "age": -1, "balance": Decimal("1000.50")},  # Negative age
                "should_be_valid": True,  # Schema validation only, business rules separate
                "description": "Negative age (schema valid, business invalid)"
            }
        ]
        
        for test_case in test_cases:
            result = await integrity_validator.validate_against_schema(
                test_case["data"], "integrity_db", "users"
            )
            
            if test_case["should_be_valid"]:
                assert result.is_valid, f"Expected valid but got errors for: {test_case['description']}"
            else:
                assert not result.is_valid, f"Expected invalid but got valid for: {test_case['description']}"
    
    @pytest.mark.asyncio
    async def test_constraint_integrity_validation(self, integrity_validator):
        """Test constraint integrity validation."""
        # Test primary key constraints
        test_cases = [
            {
                "data": {"email": "test@example.com", "balance": Decimal("1000.00")},  # Missing ID in strict mode
                "description": "Missing primary key in strict mode"
            },
            {
                "data": {"id": None, "email": "test@example.com", "balance": Decimal("1000.00")},  # NULL primary key
                "description": "NULL primary key"
            }
        ]
        
        for test_case in test_cases:
            result = await integrity_validator.validate_against_schema(
                test_case["data"], "integrity_db", "users"
            )
            
            # Should have constraint-related errors
            constraint_errors = [e for e in result.errors if "PRIMARY_KEY" in e.error_code]
            assert len(constraint_errors) > 0, f"Expected constraint errors for: {test_case['description']}"
    
    @pytest.mark.asyncio
    async def test_data_consistency_across_validations(self, integrity_validator):
        """Test data consistency across multiple validations."""
        # Same data should always produce same validation results
        test_data = {
            "email": "consistency@test.com",
            "age": 30,
            "balance": Decimal("2500.75")
        }
        
        # Run multiple validations
        results = []
        for _ in range(5):
            result = await integrity_validator.validate_against_schema(
                test_data, "integrity_db", "users"
            )
            results.append(result)
        
        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result.is_valid == first_result.is_valid
            assert len(result.errors) == len(first_result.errors)
            assert len(result.warnings) == len(first_result.warnings)
            assert set(result.validated_fields) == set(first_result.validated_fields)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])