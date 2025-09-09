"""
Comprehensive tests for Phase 1 Foundation and Core Infrastructure components.
"""

import asyncio
import sys
import os
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta

# Try to import yaml, but don't fail if not available
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

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


class TestEnhancedSchemaCache:
    """Test suite for EnhancedSchemaCache."""
    
    async def create_cache(self):
        """Create cache instance for testing."""
        config = MCPSchemaConfig(mcp_server_url="http://test:8000")
        cache = EnhancedSchemaCache(config=config, max_entries=100)
        return cache
    
    async def test_cache_initialization(self):
        """Test cache initialization."""
        config = MCPSchemaConfig(mcp_server_url="http://test:8000")
        cache = EnhancedSchemaCache(
            config=config,
            max_entries=1000,
            default_ttl=600,
            semantic_ttl=3600
        )
        
        assert cache.max_entries == 1000
        assert cache.default_ttl == 600
        assert cache.semantic_ttl == 3600
        assert len(cache._cache) == 0
    
    async def test_basic_cache_operations(self):
        """Test basic cache set/get operations."""
        cache = await self.create_cache()
        
        # Test set and get
        test_data = {"test": "data", "number": 123}
        await cache.set("test_operation", test_data, database="test_db")
        
        result = await cache.get("test_operation", database="test_db")
        assert result == test_data
        
        # Test miss
        result = await cache.get("missing_operation", database="test_db")
        assert result is None
        
        await cache.clear()
    
    async def test_cache_ttl_expiration(self):
        """Test cache TTL expiration."""
        cache = await self.create_cache()
        
        # Set with short TTL
        test_data = {"expires": "soon"}
        await cache.set("expiring_operation", test_data, ttl=1, database="test_db")
        
        # Should be available immediately
        result = await cache.get("expiring_operation", database="test_db")
        assert result == test_data
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        result = await cache.get("expiring_operation", database="test_db")
        assert result is None
        
        await cache.clear()
    
    async def test_cache_entry_types(self):
        """Test different cache entry types."""
        cache = await self.create_cache()
        
        # Test schema entry
        await cache.set("schema", {"tables": []}, database="test_db")
        
        # Test table entry
        await cache.set("table", {"columns": []}, database="test_db", table="test_table")
        
        # Test semantic mapping
        await cache.set("semantic", {"mapping": "data"}, term="revenue")
        
        # Verify type classification
        schema_key = cache._generate_key("schema", database="test_db")
        table_key = cache._generate_key("table", database="test_db", table="test_table")
        semantic_key = cache._generate_key("semantic", term="revenue")
        
        assert cache._get_entry_type(schema_key) == CacheEntryType.SCHEMA
        assert cache._get_entry_type(table_key) == CacheEntryType.TABLE
        assert cache._get_entry_type(semantic_key) == CacheEntryType.SEMANTIC_MAPPING
        
        await cache.clear()
    
    async def test_cache_eviction(self):
        """Test cache eviction when max entries reached."""
        cache = EnhancedSchemaCache(max_entries=5, default_ttl=300)
        
        # Fill cache beyond capacity
        for i in range(10):
            await cache.set("operation", f"data_{i}", id=str(i))
        
        # Should have evicted some entries
        stats = cache.get_cache_stats()
        assert stats.total_entries <= 5
        assert stats.eviction_count > 0
    
    async def test_cache_invalidation(self, cache):
        """Test cache invalidation."""
        # Add test data
        await cache.set("schema", {"test": "data1"}, database="db1")
        await cache.set("schema", {"test": "data2"}, database="db2")
        await cache.set("table", {"test": "data3"}, database="db1", table="table1")
        
        # Invalidate by pattern
        invalidated = await cache.invalidate("schema:*")
        assert invalidated == 2
        
        # Schema entries should be gone
        result1 = await cache.get("schema", database="db1")
        result2 = await cache.get("schema", database="db2")
        assert result1 is None
        assert result2 is None
        
        # Table entry should remain
        result3 = await cache.get("table", database="db1", table="table1")
        assert result3 == {"test": "data3"}
    
    async def test_cache_statistics(self, cache):
        """Test cache statistics collection."""
        # Generate some cache activity
        await cache.set("operation1", "data1", param="value1")
        await cache.set("operation2", "data2", param="value2")
        
        # Some hits
        await cache.get("operation1", param="value1")
        await cache.get("operation1", param="value1")
        
        # Some misses
        await cache.get("missing1", param="value1")
        await cache.get("missing2", param="value2")
        
        stats = cache.get_cache_stats()
        assert stats.total_entries == 2
        assert stats.hit_rate > 0
        assert stats.miss_rate > 0
        
        detailed_metrics = cache.get_detailed_metrics()
        assert detailed_metrics.total_entries == 2
        assert detailed_metrics.hit_rate > 0
        assert len(detailed_metrics.hottest_entries) > 0
    
    async def test_cache_warming(self, cache):
        """Test cache warming functionality."""
        operations = [
            {"operation": "get_tables", "params": {"database": "test_db"}},
            {"operation": "get_schema", "params": {"database": "test_db", "table": "test_table"}}
        ]
        
        warmed_count = await cache.warm_cache(operations)
        assert warmed_count == 2
        
        # Check that entries were created
        result1 = await cache.get("get_tables", database="test_db")
        result2 = await cache.get("get_schema", database="test_db", table="test_table")
        
        assert result1 is not None
        assert result2 is not None
    
    async def test_distributed_sync_setup(self, cache):
        """Test distributed cache synchronization setup."""
        def sync_callback(data):
            return True
        
        result = await cache.setup_distributed_sync(sync_callback)
        assert result is True
        
        # Test sync with agents
        sync_results = await cache.sync_with_agents(["agent1", "agent2"])
        assert sync_results["agent1"] is True
        assert sync_results["agent2"] is True


class TestConfigurationManager:
    """Test suite for ConfigurationManager."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    async def config_manager(self, temp_config_dir):
        """Create configuration manager for testing."""
        manager = ConfigurationManager(
            config_dir=temp_config_dir,
            environment="test",
            enable_hot_reload=False,
            enable_versioning=True
        )
        await manager.initialize()
        yield manager
        await manager.shutdown()
    
    def test_configuration_manager_initialization(self, temp_config_dir):
        """Test configuration manager initialization."""
        manager = ConfigurationManager(
            config_dir=temp_config_dir,
            environment="development",
            enable_hot_reload=True,
            enable_versioning=True
        )
        
        assert manager.environment == "development"
        assert manager.enable_hot_reload is True
        assert manager.enable_versioning is True
        assert manager.config_dir == Path(temp_config_dir)
    
    async def test_default_configuration_loading(self, config_manager):
        """Test loading of default configuration."""
        config = await config_manager.get_configuration()
        
        # Check default values
        assert config["environment"] == "test"
        assert "database" in config
        assert "cache" in config
        assert "mcp" in config
        assert config["database"]["connection"]["timeout"] == 30
    
    async def test_file_configuration_loading(self, temp_config_dir):
        """Test loading configuration from files."""
        # Create config file
        config_file = Path(temp_config_dir) / "config.yaml"
        test_config = {
            "database": {
                "connection": {
                    "timeout": 60,
                    "host": "test-host"
                }
            },
            "custom_setting": "test_value"
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        # Create manager and load config
        manager = ConfigurationManager(
            config_dir=temp_config_dir,
            environment="test",
            enable_hot_reload=False
        )
        await manager.initialize()
        
        config = await manager.get_configuration()
        
        # Should have merged with defaults
        assert config["database"]["connection"]["timeout"] == 60
        assert config["database"]["connection"]["host"] == "test-host"
        assert config["custom_setting"] == "test_value"
        
        await manager.shutdown()
    
    async def test_environment_specific_configuration(self, temp_config_dir):
        """Test environment-specific configuration loading."""
        # Create base config
        base_config = {"base_setting": "base_value", "shared": {"value": "base"}}
        with open(Path(temp_config_dir) / "config.yaml", 'w') as f:
            yaml.dump(base_config, f)
        
        # Create environment-specific config
        env_config = {"env_setting": "env_value", "shared": {"value": "env_override"}}
        with open(Path(temp_config_dir) / "config.test.yaml", 'w') as f:
            yaml.dump(env_config, f)
        
        manager = ConfigurationManager(
            config_dir=temp_config_dir,
            environment="test",
            enable_hot_reload=False
        )
        await manager.initialize()
        
        config = await manager.get_configuration()
        
        assert config["base_setting"] == "base_value"
        assert config["env_setting"] == "env_value"
        assert config["shared"]["value"] == "env_override"  # Environment should override
        
        await manager.shutdown()
    
    async def test_configuration_validation(self, config_manager):
        """Test configuration validation."""
        # Test valid configuration change
        result = await config_manager.set_configuration("cache.ttl", 600)
        assert result is True
        
        # Test invalid configuration change (out of range)
        result = await config_manager.set_configuration("cache.ttl", 50)  # Below minimum
        assert result is False
        
        # Test invalid type
        result = await config_manager.set_configuration("database.connection.timeout", "invalid")
        assert result is False
    
    async def test_configuration_versioning(self, config_manager):
        """Test configuration versioning."""
        # Make a configuration change
        await config_manager.set_configuration("cache.ttl", 600, user_id="test_user")
        
        # Check that snapshot was created
        snapshots = config_manager.get_snapshots()
        assert len(snapshots) > 0
        
        current_version = config_manager._current_version
        
        # Make another change
        await config_manager.set_configuration("cache.max_entries", 5000)
        
        # Should have new version
        assert config_manager._current_version != current_version
        
        # Test rollback
        result = await config_manager.rollback_to_version(current_version)
        assert result is True
        
        # Configuration should be rolled back
        config = await config_manager.get_configuration()
        assert config["cache"]["ttl"] == 600
    
    async def test_configuration_change_tracking(self, config_manager):
        """Test configuration change history tracking."""
        # Make some changes
        await config_manager.set_configuration(
            "cache.ttl", 
            600, 
            user_id="user1", 
            reason="Performance optimization"
        )
        
        await config_manager.set_configuration(
            "database.connection.timeout", 
            45, 
            user_id="user2"
        )
        
        # Check change history
        history = config_manager.get_change_history(limit=10)
        assert len(history) >= 2
        
        # Check change details
        latest_change = history[0]  # Most recent first
        assert latest_change["key_path"] == "database.connection.timeout"
        assert latest_change["new_value"] == 45
        assert latest_change["user_id"] == "user2"
    
    async def test_configuration_backup_restore(self, config_manager, temp_config_dir):
        """Test configuration backup and restore."""
        # Make some configuration changes
        await config_manager.set_configuration("cache.ttl", 600)
        await config_manager.set_configuration("custom.setting", "test_value")
        
        # Create backup
        backup_path = str(Path(temp_config_dir) / "test_backup.json")
        result_path = await config_manager.backup_configuration(backup_path)
        assert result_path == backup_path
        assert os.path.exists(backup_path)
        
        # Make more changes
        await config_manager.set_configuration("cache.ttl", 900)
        await config_manager.set_configuration("custom.setting", "changed_value")
        
        # Restore from backup
        result = await config_manager.restore_configuration(backup_path)
        assert result is True
        
        # Configuration should be restored
        config = await config_manager.get_configuration()
        assert config["cache"]["ttl"] == 600
        assert config["custom"]["setting"] == "test_value"


class TestConfigurationValidator:
    """Test suite for ConfigurationValidator."""
    
    def test_validation_rule_setup(self):
        """Test setting up validation rules."""
        validator = ConfigurationValidator()
        
        # Add type validation
        validator.add_validation_rule("timeout", "type", expected_type=int)
        
        # Add range validation
        validator.add_validation_rule("port", "range", min=1, max=65535)
        
        # Add regex validation
        validator.add_validation_rule("url", "regex", pattern=r"^https?://.*")
        
        assert len(validator.validation_rules) == 3
    
    def test_configuration_validation_success(self):
        """Test successful configuration validation."""
        validator = ConfigurationValidator()
        validator.add_validation_rule("database.timeout", "type", expected_type=int)
        validator.add_validation_rule("database.port", "range", min=1, max=65535)
        
        config = {
            "database": {
                "timeout": 30,
                "port": 3306
            }
        }
        
        errors = validator.validate_configuration(config)
        assert len(errors) == 0
    
    def test_configuration_validation_errors(self):
        """Test configuration validation with errors."""
        validator = ConfigurationValidator()
        validator.add_validation_rule("database.timeout", "type", expected_type=int)
        validator.add_validation_rule("database.port", "range", min=1, max=65535)
        validator.add_validation_rule("required_field", "required", required=True)
        
        config = {
            "database": {
                "timeout": "invalid",  # Wrong type
                "port": 100000  # Out of range
            }
            # Missing required_field
        }
        
        errors = validator.validate_configuration(config)
        assert len(errors) == 3
        
        # Check error details
        error_keys = [error.key_path for error in errors]
        assert "database.timeout" in error_keys
        assert "database.port" in error_keys
        assert "required_field" in error_keys
    
    def test_custom_validator(self):
        """Test custom validation functions."""
        validator = ConfigurationValidator()
        
        # Add custom validator
        def validate_environment(value):
            return value in ["dev", "staging", "prod"]
        
        validator.add_custom_validator("env_validator", validate_environment)
        validator.add_validation_rule("environment", "custom", validator="env_validator")
        
        # Test valid environment
        config = {"environment": "prod"}
        errors = validator.validate_configuration(config)
        assert len(errors) == 0
        
        # Test invalid environment
        config = {"environment": "invalid"}
        errors = validator.validate_configuration(config)
        assert len(errors) == 1
        assert errors[0].key_path == "environment"


class TestIntegratedSchemaManager:
    """Test integration of enhanced components with schema manager."""
    
    async def test_schema_manager_with_enhanced_cache(self):
        """Test schema manager with enhanced cache integration."""
        config = MCPSchemaConfig(mcp_server_url="http://test:8000")
        enhanced_cache = EnhancedSchemaCache(config=config)
        
        manager = MCPSchemaManager(
            mcp_config=config,
            enhanced_cache=enhanced_cache
        )
        
        # Verify enhanced cache is used
        assert manager.enhanced_cache is enhanced_cache
        
        # Test cache operations
        test_data = {"test": "data"}
        cache_key = "test_operation:database:test_db"
        
        manager._set_cache(cache_key, test_data)
        cached_result = manager._get_cache(cache_key)
        
        # Should work with both legacy and enhanced cache
        assert cached_result == test_data


# Test runner functions
def test_enhanced_cache_sync():
    """Synchronous test runner for enhanced cache."""
    async def run_tests():
        test_instance = TestEnhancedSchemaCache()
        
        # Test initialization
        await test_instance.test_cache_initialization()
        print("✓ Enhanced cache initialization test passed")
        
        # Test basic operations
        cache = EnhancedSchemaCache(
            config=MCPSchemaConfig(mcp_server_url="http://test:8000"),
            max_entries=100
        )
        await test_instance.test_basic_cache_operations(cache)
        print("✓ Enhanced cache basic operations test passed")
        
        # Test TTL expiration
        await test_instance.test_cache_ttl_expiration(cache)
        print("✓ Enhanced cache TTL expiration test passed")
        
        # Test entry types
        await test_instance.test_cache_entry_types(cache)
        print("✓ Enhanced cache entry types test passed")
        
        # Test eviction
        await test_instance.test_cache_eviction()
        print("✓ Enhanced cache eviction test passed")
        
        # Test invalidation
        await test_instance.test_cache_invalidation(cache)
        print("✓ Enhanced cache invalidation test passed")
        
        # Test statistics
        await test_instance.test_cache_statistics(cache)
        print("✓ Enhanced cache statistics test passed")
        
        # Test warming
        await test_instance.test_cache_warming(cache)
        print("✓ Enhanced cache warming test passed")
        
        # Test distributed sync
        await test_instance.test_distributed_sync_setup(cache)
        print("✓ Enhanced cache distributed sync test passed")
        
        await cache.clear()
    
    asyncio.run(run_tests())


def test_configuration_manager_sync():
    """Synchronous test runner for configuration manager."""
    async def run_tests():
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_instance = TestConfigurationManager()
            
            # Test initialization
            test_instance.test_configuration_manager_initialization(temp_dir)
            print("✓ Configuration manager initialization test passed")
            
            # Test with actual manager
            manager = ConfigurationManager(
                config_dir=temp_dir,
                environment="test",
                enable_hot_reload=False,
                enable_versioning=True
            )
            await manager.initialize()
            
            # Test default loading
            await test_instance.test_default_configuration_loading(manager)
            print("✓ Configuration manager default loading test passed")
            
            # Test validation
            await test_instance.test_configuration_validation(manager)
            print("✓ Configuration manager validation test passed")
            
            # Test versioning
            await test_instance.test_configuration_versioning(manager)
            print("✓ Configuration manager versioning test passed")
            
            # Test change tracking
            await test_instance.test_configuration_change_tracking(manager)
            print("✓ Configuration manager change tracking test passed")
            
            # Test backup/restore
            await test_instance.test_configuration_backup_restore(manager, temp_dir)
            print("✓ Configuration manager backup/restore test passed")
            
            await manager.shutdown()
    
    asyncio.run(run_tests())


def test_configuration_validator_sync():
    """Synchronous test runner for configuration validator."""
    test_instance = TestConfigurationValidator()
    
    # Test validation rule setup
    test_instance.test_validation_rule_setup()
    print("✓ Configuration validator rule setup test passed")
    
    # Test successful validation
    test_instance.test_configuration_validation_success()
    print("✓ Configuration validator success test passed")
    
    # Test validation errors
    test_instance.test_configuration_validation_errors()
    print("✓ Configuration validator errors test passed")
    
    # Test custom validator
    test_instance.test_custom_validator()
    print("✓ Configuration validator custom test passed")


def test_integrated_manager_sync():
    """Synchronous test runner for integrated schema manager."""
    async def run_tests():
        test_instance = TestIntegratedSchemaManager()
        
        await test_instance.test_schema_manager_with_enhanced_cache()
        print("✓ Integrated schema manager test passed")
    
    asyncio.run(run_tests())


if __name__ == "__main__":
    print("Running Phase 1 Foundation and Core Infrastructure Tests...")
    print()
    
    print("1. Testing Enhanced Schema Cache...")
    test_enhanced_cache_sync()
    print()
    
    print("2. Testing Configuration Manager...")
    test_configuration_manager_sync()
    print()
    
    print("3. Testing Configuration Validator...")
    test_configuration_validator_sync()
    print()
    
    print("4. Testing Integrated Schema Manager...")
    test_integrated_manager_sync()
    print()
    
    print("✓ All Phase 1 Foundation and Core Infrastructure tests passed!")
