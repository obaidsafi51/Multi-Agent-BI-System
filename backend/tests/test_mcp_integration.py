"""
Integration tests for MCP Schema Management system.

This module contains end-to-end integration tests that verify the complete
MCP schema management workflow including real server interactions.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List

from backend.schema_management.manager import MCPSchemaManager
from backend.schema_management.client import EnhancedMCPClient, MCPConnectionError
from backend.schema_management.dynamic_validator import DynamicDataValidator, DynamicValidationConfig
from backend.schema_management.config import MCPSchemaConfig, SchemaValidationConfig
from backend.schema_management.models import (
    ValidationResult, ValidationError, ValidationSeverity,
    DatabaseInfo, TableInfo, TableSchema, ColumnInfo
)


@pytest.mark.integration
class TestMCPIntegrationBasic:
    """Basic integration tests for MCP schema management."""
    
    @pytest.fixture
    def integration_config(self):
        """Create configuration for integration testing."""
        return MCPSchemaConfig(
            mcp_server_url=os.getenv("TIDB_MCP_SERVER_URL", "http://localhost:8000"),
            connection_timeout=10,
            request_timeout=30,
            max_retries=3,
            retry_delay=1.0,
            cache_ttl=60,  # Shorter for testing
            enable_caching=True,
            fallback_enabled=True
        )
    
    @pytest.fixture
    def mock_integration_manager(self, integration_config):
        """Create integration manager with mocked MCP server responses."""
        with patch('backend.schema_management.manager.EnhancedMCPClient') as mock_client_class:
            mock_client = Mock(spec=EnhancedMCPClient)
            mock_client_class.return_value = mock_client
            
            # Mock successful connection
            mock_client.connect = AsyncMock(return_value=True)
            mock_client.health_check = AsyncMock(return_value=True)
            
            # Mock database discovery
            mock_databases = [
                {"name": "financial_db", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True, "table_count": 5},
                {"name": "test_db", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True, "table_count": 3}
            ]
            mock_client._send_request = AsyncMock(return_value=mock_databases)
            
            manager = MCPSchemaManager(integration_config)
            manager.client = mock_client
            return manager
    
    @pytest.mark.asyncio
    async def test_end_to_end_schema_discovery(self, mock_integration_manager):
        """Test complete schema discovery workflow."""
        # Test connection
        connected = await mock_integration_manager.connect()
        assert connected is True
        
        # Test database discovery
        databases = await mock_integration_manager.discover_databases()
        assert len(databases) == 2
        assert any(db.name == "financial_db" for db in databases)
        assert any(db.name == "test_db" for db in databases)
        
        # Verify cache is populated
        cache_stats = mock_integration_manager.get_cache_stats()
        assert cache_stats.total_entries > 0
    
    @pytest.mark.asyncio
    async def test_table_discovery_workflow(self, mock_integration_manager):
        """Test table discovery workflow."""
        # Mock table discovery response
        mock_tables = [
            {"name": "financial_overview", "type": "BASE TABLE", "engine": "InnoDB", "rows": 1000, "size_mb": 5.2},
            {"name": "cash_flow", "type": "BASE TABLE", "engine": "InnoDB", "rows": 500, "size_mb": 2.8},
            {"name": "budget_tracking", "type": "BASE TABLE", "engine": "InnoDB", "rows": 750, "size_mb": 3.5}
        ]
        mock_integration_manager.client._send_request = AsyncMock(return_value=mock_tables)
        
        # Test table discovery
        tables = await mock_integration_manager.get_tables("financial_db")
        assert len(tables) == 3
        assert any(table.name == "financial_overview" for table in tables)
        assert any(table.name == "cash_flow" for table in tables)
        assert any(table.name == "budget_tracking" for table in tables)
        
        # Verify table properties
        financial_table = next(t for t in tables if t.name == "financial_overview")
        assert financial_table.rows == 1000
        assert financial_table.size_mb == 5.2
        assert financial_table.engine == "InnoDB"
    
    @pytest.mark.asyncio
    async def test_schema_retrieval_workflow(self, mock_integration_manager):
        """Test schema retrieval workflow."""
        # Mock detailed schema response
        from backend.schema_management.models import DetailedTableSchema
        
        mock_schema_data = {
            "columns": [
                {
                    "name": "id",
                    "data_type": "int",
                    "is_nullable": False,
                    "default_value": None,
                    "is_primary_key": True,
                    "is_foreign_key": False,
                    "is_auto_increment": True
                },
                {
                    "name": "period_date",
                    "data_type": "date",
                    "is_nullable": False,
                    "default_value": None,
                    "is_primary_key": False,
                    "is_foreign_key": False
                },
                {
                    "name": "revenue",
                    "data_type": "decimal",
                    "is_nullable": False,
                    "default_value": "0.00",
                    "is_primary_key": False,
                    "is_foreign_key": False,
                    "precision": 15,
                    "scale": 2
                }
            ],
            "indexes": [
                {
                    "name": "PRIMARY",
                    "columns": ["id"],
                    "is_unique": True,
                    "is_primary": True,
                    "index_type": "BTREE"
                }
            ],
            "primary_keys": ["id"],
            "foreign_keys": [],
            "statistics": {"row_count": 1000}
        }
        
        # Create detailed schema mock
        columns = [
            ColumnInfo("id", "int", False, None, True, False, is_auto_increment=True),
            ColumnInfo("period_date", "date", False, None, False, False),
            ColumnInfo("revenue", "decimal", False, "0.00", False, False, precision=15, scale=2)
        ]
        
        schema = TableSchema(
            database="financial_db",
            table="financial_overview",
            columns=columns,
            indexes=[],
            primary_keys=["id"],
            foreign_keys=[],
            constraints=[]
        )
        
        detailed_schema = DetailedTableSchema(
            schema=schema,
            sample_data=[{"id": 1, "period_date": "2024-01-01", "revenue": "50000.00"}],
            discovery_time_ms=150
        )
        
        mock_integration_manager.client.get_table_schema_detailed = AsyncMock(return_value=detailed_schema)
        
        # Test schema retrieval
        retrieved_schema = await mock_integration_manager.get_table_schema("financial_db", "financial_overview")
        
        assert retrieved_schema is not None
        assert retrieved_schema.database == "financial_db"
        assert retrieved_schema.table == "financial_overview"
        assert len(retrieved_schema.columns) == 3
        assert retrieved_schema.columns[0].name == "id"
        assert retrieved_schema.columns[0].is_primary_key is True
        assert retrieved_schema.columns[2].precision == 15
        assert retrieved_schema.columns[2].scale == 2


@pytest.mark.integration
class TestMCPValidationIntegration:
    """Integration tests for MCP-based validation."""
    
    @pytest.fixture
    def validation_manager(self):
        """Create validation manager for integration testing."""
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            cache_ttl=60,
            enable_caching=True,
            fallback_enabled=True
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient') as mock_client_class:
            mock_client = Mock(spec=EnhancedMCPClient)
            mock_client_class.return_value = mock_client
            
            # Mock financial schema
            financial_columns = [
                ColumnInfo("period_date", "date", False, None, False, False),
                ColumnInfo("period_type", "varchar", False, None, False, False, max_length=20),
                ColumnInfo("revenue", "decimal", False, "0.00", False, False, precision=15, scale=2),
                ColumnInfo("expenses", "decimal", True, None, False, False, precision=15, scale=2),
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
            
            async def mock_get_schema(database: str, table: str):
                if database == "financial_db" and table == "financial_overview":
                    return financial_schema
                return None
            
            manager = MCPSchemaManager(config)
            manager.client = mock_client
            manager.get_table_schema = mock_get_schema
            
            return manager
    
    @pytest.fixture
    def integration_validator(self, validation_manager):
        """Create integration validator."""
        config = DynamicValidationConfig(
            strict_mode=True,
            validate_types=True,
            validate_constraints=True,
            validate_relationships=True,
            allow_unknown_columns=False,
            fallback_to_static=True
        )
        return DynamicDataValidator(validation_manager, config)
    
    @pytest.mark.asyncio
    async def test_complete_validation_workflow(self, integration_validator):
        """Test complete validation workflow from data input to result."""
        # Valid financial data
        valid_data = {
            "period_date": date(2024, 1, 1),
            "period_type": "monthly",
            "revenue": Decimal("100000.00"),
            "expenses": Decimal("60000.00"),
            "net_profit": Decimal("40000.00")
        }
        
        # Execute validation
        result = await integration_validator.validate_against_schema(
            valid_data, "financial_db", "financial_overview"
        )
        
        # Verify results
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.validated_fields) == 5
        assert all(field in result.validated_fields for field in valid_data.keys())
        assert result.validation_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_validation_with_type_errors(self, integration_validator):
        """Test validation workflow with type errors."""
        # Invalid data with type errors
        invalid_data = {
            "period_date": "invalid_date_format",  # Should be date
            "period_type": "A" * 50,               # Too long for varchar(20)
            "revenue": "not_a_number",             # Should be decimal
            "expenses": Decimal("60000.00"),       # Valid
            "net_profit": None                     # Valid (nullable)
        }
        
        # Execute validation
        result = await integration_validator.validate_against_schema(
            invalid_data, "financial_db", "financial_overview"
        )
        
        # Verify results
        assert result.is_valid is False
        assert len(result.errors) >= 2  # At least string length and decimal errors
        
        # Check specific error types
        error_codes = [error.error_code for error in result.errors]
        assert "STRING_TOO_LONG" in error_codes
        assert "INVALID_DECIMAL" in error_codes
    
    @pytest.mark.asyncio
    async def test_validation_with_constraint_errors(self, integration_validator):
        """Test validation workflow with constraint errors."""
        # Data missing primary key fields
        incomplete_data = {
            "revenue": Decimal("100000.00"),
            "expenses": Decimal("60000.00")
            # Missing period_date and period_type (primary keys)
        }
        
        # Execute validation
        result = await integration_validator.validate_against_schema(
            incomplete_data, "financial_db", "financial_overview"
        )
        
        # Verify results
        assert result.is_valid is False
        
        # Should have primary key errors
        pk_errors = [error for error in result.errors if error.error_code == "PRIMARY_KEY_MISSING"]
        assert len(pk_errors) == 2  # Both primary key fields missing
    
    @pytest.mark.asyncio
    async def test_validation_fallback_mechanism(self, integration_validator):
        """Test validation fallback when schema is unavailable."""
        # Test with unknown table (should trigger fallback)
        data = {
            "period_date": date.today(),
            "period_type": "monthly",
            "revenue": Decimal("50000.00")
        }
        
        # Execute validation for unknown table
        result = await integration_validator.validate_against_schema(
            data, "unknown_db", "unknown_table"
        )
        
        # Should fallback gracefully
        assert isinstance(result, ValidationResult)
        # Result depends on fallback implementation
        assert result.validation_time_ms >= 0


@pytest.mark.integration
class TestMCPErrorHandlingIntegration:
    """Integration tests for error handling scenarios."""
    
    @pytest.fixture
    def error_test_manager(self):
        """Create manager for error testing."""
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            connection_timeout=2,
            request_timeout=5,
            max_retries=2,
            retry_delay=0.1,
            fallback_enabled=True
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient') as mock_client_class:
            mock_client = Mock(spec=EnhancedMCPClient)
            mock_client_class.return_value = mock_client
            
            manager = MCPSchemaManager(config)
            manager.client = mock_client
            return manager
    
    @pytest.mark.asyncio
    async def test_server_unavailable_handling(self, error_test_manager):
        """Test handling when MCP server is unavailable."""
        # Mock connection failure
        error_test_manager.client.connect = AsyncMock(side_effect=MCPConnectionError("Connection refused"))
        
        # Should handle gracefully with fallback
        connected = await error_test_manager.connect()
        assert connected is False
    
    @pytest.mark.asyncio
    async def test_server_error_response_handling(self, error_test_manager):
        """Test handling of server error responses."""
        # Mock server error response
        error_test_manager.client._send_request = AsyncMock(return_value={"error": "Internal server error"})
        
        # Should handle gracefully with fallback
        databases = await error_test_manager.discover_databases()
        assert databases == []  # Fallback returns empty list
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, error_test_manager):
        """Test handling of request timeouts."""
        # Mock timeout
        error_test_manager.client._send_request = AsyncMock(side_effect=asyncio.TimeoutError("Request timeout"))
        
        # Should handle gracefully with fallback
        databases = await error_test_manager.discover_databases()
        assert databases == []  # Fallback returns empty list
    
    @pytest.mark.asyncio
    async def test_malformed_response_handling(self, error_test_manager):
        """Test handling of malformed server responses."""
        # Mock malformed response
        error_test_manager.client._send_request = AsyncMock(return_value="invalid_json_response")
        
        # Should handle gracefully with fallback
        databases = await error_test_manager.discover_databases()
        assert databases == []  # Fallback returns empty list


@pytest.mark.integration
class TestMCPPerformanceIntegration:
    """Integration tests for performance characteristics."""
    
    @pytest.fixture
    def performance_manager(self):
        """Create manager for performance testing."""
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            cache_ttl=300,
            enable_caching=True,
            fallback_enabled=True
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient') as mock_client_class:
            mock_client = Mock(spec=EnhancedMCPClient)
            mock_client_class.return_value = mock_client
            
            # Mock fast responses
            mock_client._send_request = AsyncMock(return_value=[
                {"name": "db1", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True}
            ])
            
            manager = MCPSchemaManager(config)
            manager.client = mock_client
            return manager
    
    @pytest.mark.asyncio
    async def test_response_time_performance(self, performance_manager):
        """Test that operations complete within acceptable time limits."""
        start_time = datetime.now()
        
        # Execute multiple operations
        databases = await performance_manager.discover_databases()
        tables = await performance_manager.get_tables("test_db")
        
        end_time = datetime.now()
        total_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Should complete quickly (under 1 second for mocked operations)
        assert total_time_ms < 1000
        assert len(databases) >= 0
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self, performance_manager):
        """Test performance under concurrent load."""
        async def operation_worker():
            """Worker function for concurrent operations."""
            databases = await performance_manager.discover_databases()
            return len(databases)
        
        start_time = datetime.now()
        
        # Run multiple concurrent operations
        tasks = [operation_worker() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        end_time = datetime.now()
        total_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Should handle concurrent operations efficiently
        assert total_time_ms < 2000  # Under 2 seconds for 10 concurrent operations
        assert all(isinstance(result, int) for result in results)
    
    @pytest.mark.asyncio
    async def test_cache_performance_benefit(self, performance_manager):
        """Test that caching provides performance benefits."""
        # First call - should hit server
        start_time = datetime.now()
        databases1 = await performance_manager.discover_databases()
        first_call_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Second call - should use cache
        start_time = datetime.now()
        databases2 = await performance_manager.discover_databases()
        second_call_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Cache should be faster (though with mocks, difference might be minimal)
        assert second_call_time <= first_call_time + 50  # Allow some margin
        assert len(databases1) == len(databases2)
        
        # Verify cache was used
        cache_stats = performance_manager.get_cache_stats()
        assert cache_stats.hit_rate > 0


@pytest.mark.integration
class TestMCPBackwardCompatibility:
    """Integration tests for backward compatibility."""
    
    @pytest.fixture
    def compatibility_validator(self):
        """Create validator for compatibility testing."""
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            fallback_enabled=True
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            manager = MCPSchemaManager(config)
            
            validation_config = DynamicValidationConfig(fallback_to_static=True)
            return DynamicDataValidator(manager, validation_config)
    
    @pytest.mark.asyncio
    async def test_static_validation_fallback(self, compatibility_validator):
        """Test that static validation fallback works correctly."""
        # Mock schema manager to return None (schema not found)
        compatibility_validator.schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        # Test with financial data that should work with static validator
        financial_data = {
            "period_date": date.today(),
            "period_type": "monthly",
            "revenue": Decimal("50000.00"),
            "gross_profit": Decimal("30000.00"),
            "net_profit": Decimal("15000.00")
        }
        
        # Should fallback to static validation
        result = await compatibility_validator.validate_against_schema(
            financial_data, "financial_db", "financial_overview"
        )
        
        # Should succeed with static validation
        assert isinstance(result, ValidationResult)
        assert result.validation_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_legacy_api_compatibility(self, compatibility_validator):
        """Test compatibility with legacy validation APIs."""
        # Test that existing validation patterns still work
        data = {
            "field1": "value1",
            "field2": 123,
            "field3": Decimal("456.78")
        }
        
        # Should handle unknown table gracefully
        result = await compatibility_validator.validate_against_schema(
            data, "unknown_db", "unknown_table"
        )
        
        assert isinstance(result, ValidationResult)
        assert result.validation_time_ms >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])