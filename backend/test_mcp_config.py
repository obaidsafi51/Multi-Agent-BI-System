#!/usr/bin/env python3
"""
Test script for MCP configuration validation.
"""

import os
import sys
import tempfile
import asyncio

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schema_management.config import MCPSchemaConfig, SchemaValidationConfig
from schema_management.validate_config import validate_environment_variables, validate_configurations


def test_mcp_config_defaults():
    """Test MCP configuration with default values."""
    print("Testing MCP configuration with defaults...")
    
    # Set minimal required environment
    os.environ.update({
        "TIDB_HOST": "test-host",
        "TIDB_USER": "test-user", 
        "TIDB_PASSWORD": "test-password",
        "TIDB_DATABASE": "test-db"
    })
    
    try:
        config = MCPSchemaConfig.from_env()
        print(f"✅ MCP Config created successfully:")
        print(f"   Server URL: {config.mcp_server_url}")
        print(f"   Connection timeout: {config.connection_timeout}s")
        print(f"   Request timeout: {config.request_timeout}s")
        print(f"   Max retries: {config.max_retries}")
        print(f"   Cache TTL: {config.cache_ttl}s")
        print(f"   Caching enabled: {config.enable_caching}")
        print(f"   Fallback enabled: {config.fallback_enabled}")
        return True
    except Exception as e:
        print(f"❌ MCP Config failed: {e}")
        return False


def test_validation_config_defaults():
    """Test schema validation configuration with default values."""
    print("\nTesting schema validation configuration with defaults...")
    
    try:
        config = SchemaValidationConfig.from_env()
        print(f"✅ Validation Config created successfully:")
        print(f"   Strict mode: {config.strict_mode}")
        print(f"   Validate types: {config.validate_types}")
        print(f"   Validate constraints: {config.validate_constraints}")
        print(f"   Validate relationships: {config.validate_relationships}")
        print(f"   Allow unknown columns: {config.allow_unknown_columns}")
        return True
    except Exception as e:
        print(f"❌ Validation Config failed: {e}")
        return False


def test_config_validation():
    """Test configuration validation functions."""
    print("\nTesting configuration validation functions...")
    
    try:
        env_results = validate_environment_variables()
        config_results = validate_configurations()
        
        print(f"✅ Environment validation: {'Valid' if env_results['valid'] else 'Invalid'}")
        print(f"✅ MCP config validation: {'Valid' if config_results['mcp_config']['valid'] else 'Invalid'}")
        print(f"✅ Schema validation config: {'Valid' if config_results['validation_config']['valid'] else 'Invalid'}")
        
        return env_results["valid"] and config_results["mcp_config"]["valid"] and config_results["validation_config"]["valid"]
    except Exception as e:
        print(f"❌ Validation functions failed: {e}")
        return False


def test_invalid_config():
    """Test configuration with invalid values."""
    print("\nTesting configuration with invalid values...")
    
    # Test invalid URL
    original_url = os.environ.get("TIDB_MCP_SERVER_URL")
    os.environ["TIDB_MCP_SERVER_URL"] = "invalid-url"
    
    try:
        config = MCPSchemaConfig.from_env()
        print("❌ Should have failed with invalid URL")
        return False
    except ValueError as e:
        print(f"✅ Correctly caught invalid URL: {e}")
    finally:
        if original_url:
            os.environ["TIDB_MCP_SERVER_URL"] = original_url
        else:
            os.environ.pop("TIDB_MCP_SERVER_URL", None)
    
    # Test invalid timeout
    os.environ["MCP_CONNECTION_TIMEOUT"] = "-1"
    
    try:
        config = MCPSchemaConfig.from_env()
        print("❌ Should have failed with negative timeout")
        return False
    except ValueError as e:
        print(f"✅ Correctly caught negative timeout: {e}")
    finally:
        os.environ.pop("MCP_CONNECTION_TIMEOUT", None)
    
    return True


def main():
    """Run all configuration tests."""
    print("=" * 60)
    print("MCP SCHEMA MANAGEMENT CONFIGURATION TESTS")
    print("=" * 60)
    
    tests = [
        test_mcp_config_defaults,
        test_validation_config_defaults,
        test_config_validation,
        test_invalid_config
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print(f"\n🎯 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All configuration tests passed!")
        return 0
    else:
        print("❌ Some configuration tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())