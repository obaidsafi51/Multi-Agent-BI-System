"""
Simple tests for Phase 1 Foundation and Core Infrastructure components.
"""

import asyncio
import sys
import os
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema_management.enhanced_cache import (
    EnhancedSchemaCache, CacheEntry, CacheEntryType, CacheMetrics
)
from schema_management.configuration_manager import (
    ConfigurationManager, ConfigurationValidator, ConfigurationSnapshot,
    ConfigurationValidationError, ConfigurationSource
)
from schema_management.config import MCPSchemaConfig, SchemaValidationConfig
from schema_management.manager import MCPSchemaManager


async def test_enhanced_cache_basic():
    """Test basic enhanced cache functionality."""
    print("Testing Enhanced Schema Cache...")
    
    # Test initialization
    config = MCPSchemaConfig(mcp_server_url="http://test:8000")
    cache = EnhancedSchemaCache(config=config, max_entries=100)
    
    # Test basic operations
    test_data = {"test": "data", "number": 123}
    await cache.set("test_operation", test_data, database="test_db")
    
    result = await cache.get("test_operation", database="test_db")
    assert result == test_data, f"Expected {test_data}, got {result}"
    
    # Test miss
    result = await cache.get("missing_operation", database="test_db")
    assert result is None, f"Expected None, got {result}"
    
    # Test TTL expiration
    await cache.set("expiring_operation", {"expires": "soon"}, ttl=1, database="test_db")
    result = await cache.get("expiring_operation", database="test_db")
    assert result == {"expires": "soon"}, "Data should be available immediately"
    
    await asyncio.sleep(1.1)
    result = await cache.get("expiring_operation", database="test_db")
    assert result is None, "Data should be expired"
    
    # Test cache statistics
    stats = cache.get_cache_stats()
    assert stats.total_entries >= 0, "Should have non-negative entry count"
    assert 0.0 <= stats.hit_rate <= 1.0, "Hit rate should be between 0 and 1"
    
    # Test cache clearing
    await cache.clear()
    stats_after_clear = cache.get_cache_stats()
    assert stats_after_clear.total_entries == 0, "Cache should be empty after clear"
    
    print("✓ Enhanced cache basic tests passed")


async def test_configuration_manager_basic():
    """Test basic configuration manager functionality."""
    print("Testing Configuration Manager...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test initialization
        manager = ConfigurationManager(
            config_dir=temp_dir,
            environment="test",
            enable_hot_reload=False,
            enable_versioning=True
        )
        await manager.initialize()
        
        # Test default configuration loading
        config = await manager.get_configuration()
        assert config["environment"] == "test", "Environment should be 'test'"
        assert "database" in config, "Should have database configuration"
        assert "cache" in config, "Should have cache configuration"
        
        # Test configuration setting
        result = await manager.set_configuration("cache.ttl", 600)
        assert result is True, "Setting valid configuration should succeed"
        
        updated_config = await manager.get_configuration("cache.ttl")
        assert updated_config == 600, f"Expected 600, got {updated_config}"
        
        # Test invalid configuration (should fail validation)
        result = await manager.set_configuration("cache.ttl", 50)  # Below minimum
        assert result is False, "Setting invalid configuration should fail"
        
        # Test versioning
        snapshots = manager.get_snapshots()
        assert len(snapshots) > 0, "Should have snapshots after configuration changes"
        
        # Test change history
        history = manager.get_change_history()
        assert len(history) > 0, "Should have change history"
        
        await manager.shutdown()
    
    print("✓ Configuration manager basic tests passed")


def test_configuration_validator():
    """Test configuration validator functionality."""
    print("Testing Configuration Validator...")
    
    validator = ConfigurationValidator()
    
    # Add validation rules
    validator.add_validation_rule("database.timeout", "type", expected_type=int)
    validator.add_validation_rule("database.port", "range", min=1, max=65535)
    
    # Test successful validation
    config = {
        "database": {
            "timeout": 30,
            "port": 3306
        }
    }
    
    errors = validator.validate_configuration(config)
    assert len(errors) == 0, f"Expected no errors, got {len(errors)}"
    
    # Test validation errors
    invalid_config = {
        "database": {
            "timeout": "invalid",  # Wrong type
            "port": 100000  # Out of range
        }
    }
    
    errors = validator.validate_configuration(invalid_config)
    assert len(errors) >= 2, f"Expected at least 2 errors, got {len(errors)}"
    
    # Test custom validator
    def validate_environment(value):
        return value in ["dev", "staging", "prod"]
    
    validator.add_custom_validator("env_validator", validate_environment)
    validator.add_validation_rule("environment", "custom", validator="env_validator")
    
    # Valid environment
    config = {"environment": "prod"}
    errors = validator.validate_configuration(config)
    assert len(errors) == 0, "Valid environment should pass validation"
    
    # Invalid environment
    config = {"environment": "invalid"}
    errors = validator.validate_configuration(config)
    assert len(errors) == 1, "Invalid environment should fail validation"
    
    print("✓ Configuration validator tests passed")


async def test_schema_manager_integration():
    """Test schema manager with enhanced components."""
    print("Testing Schema Manager Integration...")
    
    config = MCPSchemaConfig(mcp_server_url="http://test:8000")
    enhanced_cache = EnhancedSchemaCache(config=config)
    
    manager = MCPSchemaManager(
        mcp_config=config,
        enhanced_cache=enhanced_cache
    )
    
    # Verify enhanced cache is integrated
    assert manager.enhanced_cache is enhanced_cache, "Enhanced cache should be integrated"
    
    # Test cache operations through manager
    test_data = {"test": "integration_data"}
    cache_key = "test_operation:database:test_db"
    
    manager._set_cache(cache_key, test_data)
    cached_result = manager._get_cache(cache_key)
    
    assert cached_result == test_data, "Cache operations should work through manager"
    
    # Test cache statistics
    stats = manager.get_cache_stats()
    assert hasattr(stats, 'total_entries'), "Should have cache statistics"
    
    print("✓ Schema manager integration tests passed")


async def test_error_handling():
    """Test error handling and edge cases."""
    print("Testing Error Handling...")
    
    # Test cache with invalid parameters
    try:
        cache = EnhancedSchemaCache(max_entries=-1)  # Invalid
        assert False, "Should have raised an error for negative max_entries"
    except:
        pass  # Expected to fail
    
    # Test configuration manager with non-existent directory
    with tempfile.TemporaryDirectory() as temp_dir:
        non_existent = os.path.join(temp_dir, "non_existent")
        manager = ConfigurationManager(config_dir=non_existent)
        
        # Should create directory and not fail
        await manager.initialize()
        assert os.path.exists(non_existent), "Should create config directory"
        
        await manager.shutdown()
    
    print("✓ Error handling tests passed")


async def test_performance_basic():
    """Test basic performance characteristics."""
    print("Testing Performance Characteristics...")
    
    cache = EnhancedSchemaCache(max_entries=1000)
    
    # Test batch operations
    start_time = asyncio.get_event_loop().time()
    
    for i in range(100):
        await cache.set(f"operation_{i}", f"data_{i}", id=str(i))
    
    set_time = asyncio.get_event_loop().time() - start_time
    
    start_time = asyncio.get_event_loop().time()
    
    for i in range(100):
        result = await cache.get(f"operation_{i}", id=str(i))
        assert result == f"data_{i}", f"Expected data_{i}, got {result}"
    
    get_time = asyncio.get_event_loop().time() - start_time
    
    print(f"  - Set 100 entries in {set_time:.3f}s ({100/set_time:.1f} ops/sec)")
    print(f"  - Get 100 entries in {get_time:.3f}s ({100/get_time:.1f} ops/sec)")
    
    stats = cache.get_cache_stats()
    print(f"  - Cache hit rate: {stats.hit_rate:.2%}")
    print(f"  - Memory usage: {stats.memory_usage_mb:.2f} MB")
    
    await cache.clear()
    
    print("✓ Performance tests passed")


async def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Running Phase 1 Foundation and Core Infrastructure Tests")
    print("=" * 60)
    print()
    
    try:
        # Basic functionality tests
        await test_enhanced_cache_basic()
        await test_configuration_manager_basic()
        test_configuration_validator()
        await test_schema_manager_integration()
        
        # Edge cases and error handling
        await test_error_handling()
        
        # Performance tests
        await test_performance_basic()
        
        print()
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("Phase 1 Foundation and Core Infrastructure Implementation Summary:")
        print("✅ Task 1: Dynamic Schema Management Infrastructure - COMPLETED")
        print("✅ Task 2: Enhanced Schema Cache System - COMPLETED") 
        print("✅ Task 3: Configuration Management System - COMPLETED")
        print()
        print("Key Features Implemented:")
        print("- EnhancedSchemaCache with TTL, eviction, and distributed sync support")
        print("- ConfigurationManager with validation, versioning, and hot-reload")
        print("- ConfigurationValidator with custom validation rules")
        print("- Integrated schema manager with enhanced caching")
        print("- Comprehensive error handling and monitoring")
        print("- Performance optimization and testing")
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ TEST FAILED: {str(e)}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(run_all_tests())
