#!/usr/bin/env python3
"""
Simple test script to verify the MCP server implementation.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all modules can be imported successfully."""
    print("Testing imports...")
    
    try:
        from tidb_mcp_server.config import ServerConfig, load_config
        print("✓ Config module imported successfully")
        
        from tidb_mcp_server.exceptions import TiDBMCPServerError, DatabaseConnectionError
        print("✓ Exceptions module imported successfully")
        
        from tidb_mcp_server.cache_manager import CacheManager, CacheKeyGenerator
        print("✓ Cache manager module imported successfully")
        
        from tidb_mcp_server.rate_limiter import RateLimiter, AdaptiveRateLimiter
        print("✓ Rate limiter module imported successfully")
        
        from tidb_mcp_server.models import DatabaseInfo, TableInfo, QueryResult
        print("✓ Models module imported successfully")
        
        from tidb_mcp_server.mcp_server import TiDBMCPServer
        print("✓ MCP server module imported successfully")
        
        from tidb_mcp_server import mcp_tools
        print("✓ MCP tools module imported successfully")
        
        print("\n✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_cache_manager():
    """Test basic cache manager functionality."""
    print("\nTesting cache manager...")
    
    try:
        from tidb_mcp_server.cache_manager import CacheManager
        
        cache = CacheManager(default_ttl=60, max_size=100)
        
        # Test basic operations
        cache.set("test_key", "test_value")
        value = cache.get("test_key")
        
        if value == "test_value":
            print("✓ Cache set/get works correctly")
        else:
            print(f"❌ Cache get returned unexpected value: {value}")
            return False
        
        # Test stats
        stats = cache.get_stats()
        if isinstance(stats, dict) and 'hits' in stats:
            print("✓ Cache stats work correctly")
        else:
            print("❌ Cache stats format is incorrect")
            return False
        
        print("✅ Cache manager tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Cache manager test error: {e}")
        return False


def test_rate_limiter():
    """Test basic rate limiter functionality."""
    print("\nTesting rate limiter...")
    
    try:
        from tidb_mcp_server.rate_limiter import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=60)
        
        # Test allowing requests
        allowed = limiter.allow_request("test_client")
        if allowed:
            print("✓ Rate limiter allows requests correctly")
        else:
            print("❌ Rate limiter incorrectly blocked first request")
            return False
        
        # Test stats
        stats = limiter.get_stats()
        if isinstance(stats, dict) and 'total_requests' in stats:
            print("✓ Rate limiter stats work correctly")
        else:
            print("❌ Rate limiter stats format is incorrect")
            return False
        
        print("✅ Rate limiter tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Rate limiter test error: {e}")
        return False


def test_config_loading():
    """Test configuration loading with environment variables."""
    print("\nTesting configuration...")
    
    try:
        # Set minimal required environment variables
        os.environ['TIDB_HOST'] = 'localhost'
        os.environ['TIDB_USER'] = 'test_user'
        os.environ['TIDB_PASSWORD'] = 'test_password'
        
        from tidb_mcp_server.config import ServerConfig
        
        config = ServerConfig()
        
        if config.tidb_host == 'localhost':
            print("✓ Configuration loading works correctly")
        else:
            print(f"❌ Configuration loaded unexpected host: {config.tidb_host}")
            return False
        
        # Test configuration objects
        db_config = config.get_database_config()
        mcp_config = config.get_mcp_server_config()
        cache_config = config.get_cache_config()
        security_config = config.get_security_config()
        
        if all([db_config, mcp_config, cache_config, security_config]):
            print("✓ Configuration objects created successfully")
        else:
            print("❌ Failed to create configuration objects")
            return False
        
        print("✅ Configuration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test error: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Testing TiDB MCP Server Implementation")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_cache_manager,
        test_rate_limiter,
        test_config_loading,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Implementation looks good.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())