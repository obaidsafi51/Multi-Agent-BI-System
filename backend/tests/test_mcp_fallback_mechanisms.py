"""
Comprehensive tests for MCP fallback mechanisms.

This module tests the fallback behavior when MCP server is unavailable,
returns errors, or when schema information is incomplete.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional

from backend.schema_management.manager import MCPSchemaManager
from backend.schema_management.client import EnhancedMCPClient, MCPConnectionError, MCPRequestError
from backend.schema_management.dynamic_validator import DynamicDataValidator, DynamicValidationConfig
from backend.schema_management.config import MCPSchemaConfig
from backend.schema_management.models import (
    ValidationResult, ValidationError, ValidationSeverity,
    DatabaseInfo, TableInfo, TableSchema
)


class TestMCPFallbackMechanisms:
    """Test cases for MCP fallback mechanisms."""
    
    @pytest.fixture
    def fallback_config(self):
        """Create configuration with fallback enabled."""
        return MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            connection_timeout=1,
            request_timeout=2,
            max_retries=1,
            retry_delay=0.1,
            cache_ttl=300,
            enable_caching=True,
            fallback_enabled=True
        )
    
    @pytest.fixture
    def no_fallback_config(self):
        """Create configuration with fallback disabled."""
        return MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            connection_timeout=1,
            request_timeout=2,
            max_retries=1,
            retry_delay=0.1,
            cache_ttl=300,
            enable_caching=True,
            fallback_enabled=False
        )
    
    @pytest.fixture
    def fallback_manager(self, fallback_config):
        """Create schema manager with fallback enabled."""
        with patch('backend.schema_management.manager.EnhancedMCPClient') as mock_client_class:
            mock_client = Mock(spec=EnhancedMCPClient)
            mock_client_class.return_value = mock_client
            
            manager = MCPSchemaManager(fallback_config)
            manager.client = mock_client
            return manager
    
    @pytest.fixture
    def no_fallback_manager(self, no_fallback_config):
        """Create schema manager with fallback disabled."""
        with patch('backend.schema_management.manager.EnhancedMCPClient') as mock_client_class:
            mock_client = Mock(spec=EnhancedMCPClient)
            mock_client_class.return_value = mock_client
            
            manager = MCPSchemaManager(no_fallback_config)
            manager.client = mock_client
            return manager
    
    @pytest.mark.asyncio
    async def test_connection_failure_fallback(self, fallback_manager):
        """Test fallback when MCP server connection fails."""
        # Mock connection failure
        fallback_manager.client.connect = AsyncMock(side_effect=MCPConnectionError("Connection refused"))
        
        # Should handle gracefully with fallback
        connected = await fallback_manager.connect()
        assert connected is False
        
        # Operations should still work with fallback
        fallback_manager.client._send_request = AsyncMock(side_effect=MCPConnectionError("Not connected"))
        
        databases = await fallback_manager.discover_databases()
        assert databases == []  # Fallback returns empty list
    
    @pytest.mark.asyncio
    async def test_connection_failure_no_fallback(self, no_fallback_manager):
        """Test behavior when connection fails and no fallback."""
        # Mock connection failure
        no_fallback_manager.client.connect = AsyncMock(side_effect=MCPConnectionError("Connection refused"))
        
        # Should raise exception without fallback
        with pytest.raises(MCPConnectionError):
            await no_fallback_manager.connect()
    
    @pytest.mark.asyncio
    async def test_server_error_response_fallback(self, fallback_manager):
        """Test fallback when server returns error responses."""
        # Mock server error
        fallback_manager.client._send_request = AsyncMock(return_value={"error": "Internal server error"})
        
        # Should handle gracefully with fallback
        databases = await fallback_manager.discover_databases()
        assert databases == []
        
        tables = await fallback_manager.get_tables("test_db")
        assert tables == []
        
        schema = await fallback_manager.get_table_schema("test_db", "test_table")
        assert schema is None
    
    @pytest.mark.asyncio
    async def test_server_error_response_no_fallback(self, no_fallback_manager):
        """Test behavior when server returns errors and no fallback."""
        # Mock server error
        no_fallback_manager.client._send_request = AsyncMock(return_value={"error": "Internal server error"})
        
        # Should raise exceptions without fallback
        with pytest.raises(MCPRequestError):
            await no_fallback_manager.discover_databases()
        
        with pytest.raises(MCPRequestError):
            await no_fallback_manager.get_tables("test_db")
    
    @pytest.mark.asyncio
    async def test_timeout_fallback(self, fallback_manager):
        """Test fallback when requests timeout."""
        # Mock timeout
        fallback_manager.client._send_request = AsyncMock(side_effect=asyncio.TimeoutError("Request timeout"))
        
        # Should handle gracefully with fallback
        databases = await fallback_manager.discover_databases()
        assert databases == []
        
        tables = await fallback_manager.get_tables("test_db")
        assert tables == []
    
    @pytest.mark.asyncio
    async def test_timeout_no_fallback(self, no_fallback_manager):
        """Test behavior when requests timeout and no fallback."""
        # Mock timeout
        no_fallback_manager.client._send_request = AsyncMock(side_effect=asyncio.TimeoutError("Request timeout"))
        
        # Should raise exceptions without fallback
        with pytest.raises(Exception):  # Timeout should propagate
            await no_fallback_manager.discover_databases()
    
    @pytest.mark.asyncio
    async def test_malformed_response_fallback(self, fallback_manager):
        """Test fallback when server returns malformed responses."""
        # Mock malformed response
        fallback_manager.client._send_request = AsyncMock(return_value="invalid_json")
        
        # Should handle gracefully with fallback
        databases = await fallback_manager.discover_databases()
        assert databases == []
    
    @pytest.mark.asyncio
    async def test_partial_response_fallback(self, fallback_manager):
        """Test fallback when server returns partial/incomplete responses."""
        # Mock partial response (missing required fields)
        partial_response = [
            {"name": "db1"},  # Missing charset, collation, accessible
            {"charset": "utf8mb4"}  # Missing name, collation, accessible
        ]
        fallback_manager.client._send_request = AsyncMock(return_value=partial_response)
        
        # Should handle gracefully with fallback
        databases = await fallback_manager.discover_databases()
        assert databases == []  # Should fallback due to malformed data
    
    @pytest.mark.asyncio
    async def test_cache_fallback_when_server_unavailable(self, fallback_manager):
        """Test using cached data when server becomes unavailable."""
        # First, populate cache with successful response
        success_response = [
            {"name": "cached_db", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True}
        ]
        fallback_manager.client._send_request = AsyncMock(return_value=success_response)
        
        # First call should populate cache
        databases1 = await fallback_manager.discover_databases()
        assert len(databases1) == 1
        assert databases1[0].name == "cached_db"
        
        # Now simulate server failure
        fallback_manager.client._send_request = AsyncMock(side_effect=MCPConnectionError("Server down"))
        
        # Second call should use cached data
        databases2 = await fallback_manager.discover_databases()
        assert len(databases2) == 1
        assert databases2[0].name == "cached_db"
    
    @pytest.mark.asyncio
    async def test_expired_cache_fallback(self, fallback_manager):
        """Test fallback when cache is expired and server unavailable."""
        # Populate cache
        success_response = [
            {"name": "expired_db", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True}
        ]
        fallback_manager.client._send_request = AsyncMock(return_value=success_response)
        
        databases1 = await fallback_manager.discover_databases()
        assert len(databases1) == 1
        
        # Manually expire cache
        cache_key = fallback_manager._get_cache_key("discover_databases")
        if cache_key in fallback_manager._cache_timestamps:
            fallback_manager._cache_timestamps[cache_key] = datetime.now() - fallback_manager.mcp_config.cache_ttl * 2
        
        # Simulate server failure
        fallback_manager.client._send_request = AsyncMock(side_effect=MCPConnectionError("Server down"))
        
        # Should fallback to empty result since cache is expired
        databases2 = await fallback_manager.discover_databases()
        assert databases2 == []


class TestValidationFallbackMechanisms:
    """Test cases for validation fallback mechanisms."""
    
    @pytest.fixture
    def fallback_validator(self):
        """Create validator with fallback enabled."""
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            fallback_enabled=True
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            manager = MCPSchemaManager(config)
            
            validation_config = DynamicValidationConfig(
                fallback_to_static=True,
                strict_mode=False
            )
            
            return DynamicDataValidator(manager, validation_config)
    
    @pytest.fixture
    def no_fallback_validator(self):
        """Create validator with fallback disabled."""
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            fallback_enabled=False
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            manager = MCPSchemaManager(config)
            
            validation_config = DynamicValidationConfig(
                fallback_to_static=False,
                strict_mode=False
            )
            
            return DynamicDataValidator(manager, validation_config)
    
    @pytest.mark.asyncio
    async def test_schema_not_found_fallback(self, fallback_validator):
        """Test fallback when schema is not found."""
        # Mock schema manager to return None
        fallback_validator.schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        # Test with financial data that should work with static validator
        financial_data = {
            "period_date": date.today(),
            "period_type": "monthly",
            "revenue": Decimal("50000.00"),
            "gross_profit": Decimal("30000.00"),
            "net_profit": Decimal("15000.00")
        }
        
        # Should fallback to static validation
        result = await fallback_validator.validate_against_schema(
            financial_data, "financial_db", "financial_overview"
        )
        
        assert isinstance(result, ValidationResult)
        # Should succeed with static validation fallback
        assert result.validation_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_schema_not_found_no_fallback(self, no_fallback_validator):
        """Test behavior when schema not found and no fallback."""
        # Mock schema manager to return None
        no_fallback_validator.schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        data = {"field": "value"}
        
        # Should return error without fallback
        result = await no_fallback_validator.validate_against_schema(
            data, "unknown_db", "unknown_table"
        )
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "TABLE_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_validation_system_error_fallback(self, fallback_validator):
        """Test fallback when validation system encounters errors."""
        # Mock schema manager to raise exception
        fallback_validator.schema_manager.get_table_schema = AsyncMock(
            side_effect=Exception("Database connection error")
        )
        
        # Test with known financial table
        financial_data = {
            "period_date": date.today(),
            "period_type": "monthly",
            "revenue": Decimal("50000.00")
        }
        
        # Should fallback to static validation
        result = await fallback_validator.validate_against_schema(
            financial_data, "financial_db", "financial_overview"
        )
        
        assert isinstance(result, ValidationResult)
        # Should handle gracefully with fallback
    
    @pytest.mark.asyncio
    async def test_validation_system_error_no_fallback(self, no_fallback_validator):
        """Test behavior when validation system errors and no fallback."""
        # Mock schema manager to raise exception
        no_fallback_validator.schema_manager.get_table_schema = AsyncMock(
            side_effect=Exception("Database connection error")
        )
        
        data = {"field": "value"}
        
        # Should return validation system error
        result = await no_fallback_validator.validate_against_schema(
            data, "test_db", "test_table"
        )
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "VALIDATION_SYSTEM_ERROR"
    
    @pytest.mark.asyncio
    async def test_static_validator_fallback_financial_overview(self, fallback_validator):
        """Test static validator fallback for financial_overview table."""
        # Mock schema not available
        fallback_validator.schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        # Mock static financial validator
        with patch.object(fallback_validator.static_financial_validator, 'validate_financial_overview') as mock_validate:
            financial_data = {
                "period_date": date.today(),
                "period_type": "monthly",
                "revenue": Decimal("50000.00"),
                "gross_profit": Decimal("30000.00")
            }
            
            mock_validate.return_value = financial_data
            
            result = await fallback_validator._fallback_validation(financial_data, "financial_overview")
            
            assert result.is_valid is True
            assert len(result.validated_fields) > 0
            mock_validate.assert_called_once_with(financial_data)
    
    @pytest.mark.asyncio
    async def test_static_validator_fallback_cash_flow(self, fallback_validator):
        """Test static validator fallback for cash_flow table."""
        # Mock schema not available
        fallback_validator.schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        # Mock static financial validator
        with patch.object(fallback_validator.static_financial_validator, 'validate_cash_flow') as mock_validate:
            cash_flow_data = {
                "period_date": date.today(),
                "operating_cash_flow": Decimal("25000.00"),
                "investing_cash_flow": Decimal("-10000.00"),
                "financing_cash_flow": Decimal("-5000.00")
            }
            
            mock_validate.return_value = cash_flow_data
            
            result = await fallback_validator._fallback_validation(cash_flow_data, "cash_flow")
            
            assert result.is_valid is True
            mock_validate.assert_called_once_with(cash_flow_data)
    
    @pytest.mark.asyncio
    async def test_static_validator_fallback_unknown_table(self, fallback_validator):
        """Test static validator fallback for unknown table."""
        # Mock schema not available
        fallback_validator.schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        unknown_data = {
            "field1": "value1",
            "field2": 123,
            "field3": Decimal("456.78")
        }
        
        result = await fallback_validator._fallback_validation(unknown_data, "unknown_table")
        
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "basic validation" in result.warnings[0].message.lower()
        assert set(result.validated_fields) == set(unknown_data.keys())
    
    @pytest.mark.asyncio
    async def test_static_validator_error_handling(self, fallback_validator):
        """Test error handling in static validator fallback."""
        # Mock schema not available
        fallback_validator.schema_manager.get_table_schema = AsyncMock(return_value=None)
        
        # Mock static validator to raise exception
        with patch.object(fallback_validator.static_financial_validator, 'validate_financial_overview') as mock_validate:
            from backend.database.validation import ValidationError as LegacyValidationError
            mock_validate.side_effect = LegacyValidationError("Invalid data")
            
            financial_data = {"invalid": "data"}
            
            result = await fallback_validator._fallback_validation(financial_data, "financial_overview")
            
            assert result.is_valid is False
            assert len(result.errors) == 1
            assert result.errors[0].error_code == "STATIC_VALIDATION_ERROR"


class TestFallbackConfiguration:
    """Test fallback configuration and behavior."""
    
    def test_fallback_enabled_configuration(self):
        """Test fallback enabled configuration."""
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            fallback_enabled=True
        )
        
        assert config.fallback_enabled is True
    
    def test_fallback_disabled_configuration(self):
        """Test fallback disabled configuration."""
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            fallback_enabled=False
        )
        
        assert config.fallback_enabled is False
    
    def test_fallback_environment_configuration(self):
        """Test fallback configuration from environment."""
        with patch.dict('os.environ', {'MCP_FALLBACK_ENABLED': 'false'}):
            config = MCPSchemaConfig.from_env()
            assert config.fallback_enabled is False
        
        with patch.dict('os.environ', {'MCP_FALLBACK_ENABLED': 'true'}):
            config = MCPSchemaConfig.from_env()
            assert config.fallback_enabled is True
    
    def test_validation_fallback_configuration(self):
        """Test validation fallback configuration."""
        # Fallback enabled
        config = DynamicValidationConfig(fallback_to_static=True)
        assert config.fallback_to_static is True
        
        # Fallback disabled
        config = DynamicValidationConfig(fallback_to_static=False)
        assert config.fallback_to_static is False


class TestFallbackRecovery:
    """Test recovery mechanisms after fallback scenarios."""
    
    @pytest.fixture
    def recovery_manager(self):
        """Create manager for recovery testing."""
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            fallback_enabled=True,
            cache_ttl=60
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient') as mock_client_class:
            mock_client = Mock(spec=EnhancedMCPClient)
            mock_client_class.return_value = mock_client
            
            manager = MCPSchemaManager(config)
            manager.client = mock_client
            return manager
    
    @pytest.mark.asyncio
    async def test_recovery_after_server_comes_back_online(self, recovery_manager):
        """Test recovery when server comes back online after being down."""
        # Initially server is down
        recovery_manager.client._send_request = AsyncMock(side_effect=MCPConnectionError("Server down"))
        
        # First call should use fallback
        databases1 = await recovery_manager.discover_databases()
        assert databases1 == []
        
        # Server comes back online
        success_response = [
            {"name": "recovered_db", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True}
        ]
        recovery_manager.client._send_request = AsyncMock(return_value=success_response)
        
        # Clear cache to force server call
        await recovery_manager.refresh_schema_cache("all")
        
        # Next call should work normally
        databases2 = await recovery_manager.discover_databases()
        assert len(databases2) == 1
        assert databases2[0].name == "recovered_db"
    
    @pytest.mark.asyncio
    async def test_health_check_recovery(self, recovery_manager):
        """Test health check recovery mechanism."""
        # Initially unhealthy
        recovery_manager.client.health_check = AsyncMock(return_value=False)
        
        health1 = await recovery_manager.health_check()
        assert health1 is False
        
        # Becomes healthy
        recovery_manager.client.health_check = AsyncMock(return_value=True)
        
        health2 = await recovery_manager.health_check()
        assert health2 is True
    
    @pytest.mark.asyncio
    async def test_gradual_recovery_with_partial_success(self, recovery_manager):
        """Test gradual recovery with some operations succeeding."""
        # Database discovery works but table discovery fails
        db_response = [
            {"name": "partial_db", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True}
        ]
        
        async def partial_success_mock(method, params):
            if method == "discover_databases_tool":
                return db_response
            elif method == "discover_tables_tool":
                raise MCPConnectionError("Table discovery still failing")
            else:
                return {"error": "Method not available"}
        
        recovery_manager.client._send_request = AsyncMock(side_effect=partial_success_mock)
        
        # Database discovery should work
        databases = await recovery_manager.discover_databases()
        assert len(databases) == 1
        assert databases[0].name == "partial_db"
        
        # Table discovery should fallback
        tables = await recovery_manager.get_tables("partial_db")
        assert tables == []  # Fallback returns empty list


if __name__ == "__main__":
    pytest.main([__file__, "-v"])