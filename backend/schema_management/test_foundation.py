"""
Basic test to verify MCP schema management foundation.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema_management.config import MCPSchemaConfig, SchemaValidationConfig
from schema_management.client import BackendMCPClient, EnhancedMCPClient
from schema_management.manager import MCPSchemaManager
from schema_management.models import DatabaseInfo, ValidationResult


def test_mcp_schema_config():
    """Test MCP schema configuration."""
    config = MCPSchemaConfig(
        mcp_server_url="http://test:8000",
        connection_timeout=30,
        cache_ttl=300
    )
    
    assert config.mcp_server_url == "http://test:8000"
    assert config.connection_timeout == 30
    assert config.cache_ttl == 300
    assert config.enable_caching is True


def test_schema_validation_config():
    """Test schema validation configuration."""
    config = SchemaValidationConfig(
        strict_mode=True,
        validate_types=True,
        validate_constraints=False
    )
    
    assert config.strict_mode is True
    assert config.validate_types is True
    assert config.validate_constraints is False


async def test_backend_mcp_client_initialization():
    """Test BackendMCPClient initialization."""
    config = MCPSchemaConfig(mcp_server_url="http://test:8000")
    client = BackendMCPClient(config)
    
    assert client.config.mcp_server_url == "http://test:8000"
    assert client.session is None
    assert client.is_connected is False


async def test_enhanced_mcp_client_initialization():
    """Test EnhancedMCPClient initialization."""
    config = MCPSchemaConfig(mcp_server_url="http://test:8000")
    client = EnhancedMCPClient(config)
    
    assert client.config.mcp_server_url == "http://test:8000"
    assert isinstance(client, BackendMCPClient)


async def test_mcp_schema_manager_initialization():
    """Test MCPSchemaManager initialization."""
    mcp_config = MCPSchemaConfig(mcp_server_url="http://test:8000")
    validation_config = SchemaValidationConfig(strict_mode=True)
    
    manager = MCPSchemaManager(mcp_config, validation_config)
    
    assert manager.mcp_config.mcp_server_url == "http://test:8000"
    assert manager.validation_config.strict_mode is True
    assert isinstance(manager.client, EnhancedMCPClient)


async def test_mcp_schema_manager_cache_operations():
    """Test cache operations in MCPSchemaManager."""
    manager = MCPSchemaManager()
    
    # Test cache key generation
    cache_key = manager._get_cache_key("test_op", database="test_db", table="test_table")
    assert cache_key == "test_op:database:test_db:table:test_table"
    
    # Test cache set/get
    test_data = {"test": "data"}
    manager._set_cache(cache_key, test_data)
    
    cached_data = manager._get_cache(cache_key)
    assert cached_data == test_data
    
    # Test cache stats
    stats = manager.get_cache_stats()
    assert stats.total_entries >= 0
    assert 0.0 <= stats.hit_rate <= 1.0


if __name__ == "__main__":
    # Run basic tests
    print("Testing MCP Schema Management Foundation...")
    
    # Test configurations
    test_mcp_schema_config()
    test_schema_validation_config()
    print("✓ Configuration tests passed")
    
    # Test async components
    async def run_async_tests():
        await test_backend_mcp_client_initialization()
        await test_enhanced_mcp_client_initialization()
        await test_mcp_schema_manager_initialization()
        await test_mcp_schema_manager_cache_operations()
        print("✓ Async component tests passed")
    
    asyncio.run(run_async_tests())
    
    print("✓ All foundation tests passed!")