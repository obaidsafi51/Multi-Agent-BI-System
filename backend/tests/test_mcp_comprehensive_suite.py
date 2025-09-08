"""
Comprehensive MCP Schema Management Test Suite.

This module runs all MCP-related tests and provides a comprehensive
test runner for the entire MCP schema management system.
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


class TestMCPComprehensiveSuite:
    """Comprehensive test suite for MCP schema management."""
    
    def test_import_all_mcp_modules(self):
        """Test that all MCP modules can be imported successfully."""
        try:
            from backend.schema_management.manager import MCPSchemaManager
            from backend.schema_management.client import EnhancedMCPClient, BackendMCPClient
            from backend.schema_management.dynamic_validator import DynamicDataValidator
            from backend.schema_management.config import MCPSchemaConfig, SchemaValidationConfig
            from backend.schema_management.models import (
                DatabaseInfo, TableInfo, ColumnInfo, TableSchema,
                ValidationResult, ValidationError, ValidationSeverity
            )
            
            print("✓ All MCP modules imported successfully")
            
        except ImportError as e:
            pytest.fail(f"Failed to import MCP modules: {e}")
    
    def test_configuration_validation(self):
        """Test that MCP configurations are valid."""
        from backend.schema_management.config import MCPSchemaConfig, SchemaValidationConfig
        
        # Test valid configuration
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            connection_timeout=30,
            request_timeout=60,
            max_retries=3,
            cache_ttl=300
        )
        
        assert config.mcp_server_url == "http://localhost:8000"
        assert config.connection_timeout == 30
        assert config.request_timeout == 60
        
        # Test validation configuration
        validation_config = SchemaValidationConfig(
            strict_mode=True,
            validate_types=True,
            validate_constraints=True
        )
        
        assert validation_config.strict_mode is True
        assert validation_config.validate_types is True
        
        print("✓ Configuration validation passed")
    
    def test_model_serialization(self):
        """Test that MCP models can be serialized and deserialized."""
        from backend.schema_management.models import (
            DatabaseInfo, TableInfo, ColumnInfo, serialize_schema_model,
            deserialize_database_info, deserialize_table_info, deserialize_column_info
        )
        from datetime import datetime
        
        # Test DatabaseInfo serialization
        db_info = DatabaseInfo(
            name="test_db",
            charset="utf8mb4",
            collation="utf8mb4_general_ci",
            accessible=True,
            table_count=5
        )
        
        serialized = serialize_schema_model(db_info)
        assert "test_db" in serialized
        
        # Test deserialization
        db_data = {
            "name": "test_db",
            "charset": "utf8mb4",
            "collation": "utf8mb4_general_ci",
            "accessible": True,
            "table_count": 5
        }
        
        deserialized_db = deserialize_database_info(db_data)
        assert deserialized_db.name == "test_db"
        assert deserialized_db.table_count == 5
        
        print("✓ Model serialization tests passed")
    
    @pytest.mark.asyncio
    async def test_basic_mcp_workflow(self):
        """Test basic MCP workflow with mocked components."""
        from unittest.mock import Mock, AsyncMock, patch
        from backend.schema_management.manager import MCPSchemaManager
        from backend.schema_management.config import MCPSchemaConfig
        
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            fallback_enabled=True
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # Mock successful responses
            mock_client.connect = AsyncMock(return_value=True)
            mock_client.health_check = AsyncMock(return_value=True)
            mock_client._send_request = AsyncMock(return_value=[
                {"name": "test_db", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True}
            ])
            
            manager = MCPSchemaManager(config)
            manager.client = mock_client
            
            # Test workflow
            connected = await manager.connect()
            assert connected is True
            
            databases = await manager.discover_databases()
            assert len(databases) == 1
            assert databases[0].name == "test_db"
            
            health = await manager.health_check()
            assert health is True
            
            print("✓ Basic MCP workflow test passed")
    
    @pytest.mark.asyncio
    async def test_validation_workflow(self):
        """Test validation workflow with mocked components."""
        from unittest.mock import Mock, AsyncMock, patch
        from backend.schema_management.dynamic_validator import DynamicDataValidator, DynamicValidationConfig
        from backend.schema_management.manager import MCPSchemaManager
        from backend.schema_management.config import MCPSchemaConfig
        from backend.schema_management.models import TableSchema, ColumnInfo
        from decimal import Decimal
        from datetime import date
        
        # Setup
        config = MCPSchemaConfig(mcp_server_url="http://localhost:8000", fallback_enabled=True)
        
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            manager = MCPSchemaManager(config)
            
            # Mock schema
            columns = [
                ColumnInfo("id", "int", False, None, True, False),
                ColumnInfo("name", "varchar", False, None, False, False, max_length=100),
                ColumnInfo("amount", "decimal", True, None, False, False, precision=10, scale=2)
            ]
            
            schema = TableSchema(
                database="test_db",
                table="test_table",
                columns=columns,
                indexes=[],
                primary_keys=["id"],
                foreign_keys=[],
                constraints=[]
            )
            
            manager.get_table_schema = AsyncMock(return_value=schema)
            
            validation_config = DynamicValidationConfig(fallback_to_static=True)
            validator = DynamicDataValidator(manager, validation_config)
            
            # Test validation
            valid_data = {
                "id": 1,
                "name": "Test Item",
                "amount": Decimal("123.45")
            }
            
            result = await validator.validate_against_schema(valid_data, "test_db", "test_table")
            
            assert result.is_valid is True
            assert len(result.validated_fields) > 0
            
            print("✓ Validation workflow test passed")
    
    def test_error_handling_classes(self):
        """Test that error handling classes work correctly."""
        from backend.schema_management.client import MCPConnectionError, MCPRequestError
        
        # Test MCPConnectionError
        conn_error = MCPConnectionError("Connection failed")
        assert str(conn_error) == "Connection failed"
        assert isinstance(conn_error, Exception)
        
        # Test MCPRequestError
        req_error = MCPRequestError("Request failed")
        assert str(req_error) == "Request failed"
        assert isinstance(req_error, Exception)
        
        print("✓ Error handling classes test passed")
    
    def test_cache_functionality(self):
        """Test basic cache functionality."""
        from unittest.mock import patch
        from backend.schema_management.manager import MCPSchemaManager
        from backend.schema_management.config import MCPSchemaConfig
        from datetime import datetime
        
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            enable_caching=True,
            cache_ttl=300
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            manager = MCPSchemaManager(config)
            
            # Test cache operations
            cache_key = "test_key"
            test_data = {"test": "data"}
            
            # Set cache
            manager._set_cache(cache_key, test_data)
            assert cache_key in manager._schema_cache
            assert manager._schema_cache[cache_key] == test_data
            
            # Get cache
            cached_data = manager._get_cache(cache_key)
            assert cached_data == test_data
            
            # Test cache stats
            stats = manager.get_cache_stats()
            assert stats.total_entries >= 1
            assert stats.hit_rate >= 0
            
            print("✓ Cache functionality test passed")


def run_comprehensive_tests():
    """Run all comprehensive MCP tests."""
    print("Running MCP Schema Management Comprehensive Test Suite")
    print("=" * 60)
    
    # Run the comprehensive suite
    suite = TestMCPComprehensiveSuite()
    
    try:
        # Test imports
        suite.test_import_all_mcp_modules()
        
        # Test configuration
        suite.test_configuration_validation()
        
        # Test models
        suite.test_model_serialization()
        
        # Test error classes
        suite.test_error_handling_classes()
        
        # Test cache
        suite.test_cache_functionality()
        
        # Test async workflows
        asyncio.run(suite.test_basic_mcp_workflow())
        asyncio.run(suite.test_validation_workflow())
        
        print("\n" + "=" * 60)
        print("✅ All comprehensive tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Comprehensive test failed: {e}")
        return False


def run_all_mcp_tests():
    """Run all MCP-related tests using pytest."""
    print("Running All MCP Schema Management Tests")
    print("=" * 60)
    
    # Get the directory containing the test files
    test_dir = Path(__file__).parent
    
    # List of MCP test files
    mcp_test_files = [
        "test_mcp_schema_manager.py",
        "test_mcp_client.py",
        "test_dynamic_data_validator.py",
        "test_mcp_cache_layer.py",
        "test_mcp_integration.py",
        "test_mcp_performance_benchmarks.py",
        "test_mcp_fallback_mechanisms.py"
    ]
    
    # Check which test files exist
    existing_files = []
    for test_file in mcp_test_files:
        file_path = test_dir / test_file
        if file_path.exists():
            existing_files.append(str(file_path))
            print(f"✓ Found: {test_file}")
        else:
            print(f"⚠ Missing: {test_file}")
    
    if not existing_files:
        print("❌ No MCP test files found!")
        return False
    
    print(f"\nRunning {len(existing_files)} test files...")
    
    # Run pytest on the existing files
    pytest_args = [
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "-x",  # Stop on first failure
        "--disable-warnings",  # Disable warnings for cleaner output
    ] + existing_files
    
    try:
        result = pytest.main(pytest_args)
        
        if result == 0:
            print("\n✅ All MCP tests passed!")
            return True
        else:
            print(f"\n❌ Some tests failed (exit code: {result})")
            return False
            
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run MCP Schema Management Tests")
    parser.add_argument(
        "--comprehensive",
        action="store_true",
        help="Run comprehensive test suite only"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all MCP tests using pytest"
    )
    
    args = parser.parse_args()
    
    if args.comprehensive:
        success = run_comprehensive_tests()
    elif args.all:
        success = run_all_mcp_tests()
    else:
        # Run both by default
        print("Running comprehensive tests first...")
        success1 = run_comprehensive_tests()
        
        print("\n" + "=" * 60)
        print("Running all MCP tests...")
        success2 = run_all_mcp_tests()
        
        success = success1 and success2
    
    sys.exit(0 if success else 1)