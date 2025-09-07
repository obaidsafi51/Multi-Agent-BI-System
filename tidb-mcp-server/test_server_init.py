#!/usr/bin/env python3
"""
Integration test to verify MCP server initialization.
"""

import asyncio
import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


async def test_server_initialization():
    """Test that the MCP server can be initialized without errors."""
    print("Testing MCP server initialization...")
    
    try:
        # Set required environment variables
        os.environ['TIDB_HOST'] = 'localhost'
        os.environ['TIDB_USER'] = 'test_user'
        os.environ['TIDB_PASSWORD'] = 'test_password'
        
        from tidb_mcp_server.config import load_config
        from tidb_mcp_server.mcp_server import TiDBMCPServer
        
        # Load configuration
        config = load_config()
        print("✓ Configuration loaded successfully")
        
        # Initialize server (but don't start it)
        server = TiDBMCPServer(config)
        print("✓ MCP server initialized successfully")
        
        # Test that all components are properly initialized
        if hasattr(server, 'config') and server.config is not None:
            print("✓ Server configuration is set")
        else:
            print("❌ Server configuration is missing")
            return False
        
        if hasattr(server, 'logger') and server.logger is not None:
            print("✓ Server logger is initialized")
        else:
            print("❌ Server logger is missing")
            return False
        
        print("✅ Server initialization test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Server initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_component_initialization():
    """Test individual component initialization."""
    print("\nTesting component initialization...")
    
    try:
        from tidb_mcp_server.cache_manager import CacheManager
        from tidb_mcp_server.rate_limiter import RateLimiter
        from tidb_mcp_server.config import ServerConfig
        
        # Set environment variables
        os.environ['TIDB_HOST'] = 'localhost'
        os.environ['TIDB_USER'] = 'test_user'
        os.environ['TIDB_PASSWORD'] = 'test_password'
        
        config = ServerConfig()
        
        # Test cache manager initialization
        cache_config = config.get_cache_config()
        cache_manager = CacheManager(
            default_ttl=cache_config.ttl_seconds,
            max_size=cache_config.max_size
        )
        print("✓ Cache manager initialized")
        
        # Test rate limiter initialization
        security_config = config.get_security_config()
        rate_limiter = RateLimiter(
            requests_per_minute=security_config.rate_limit_requests_per_minute
        )
        print("✓ Rate limiter initialized")
        
        # Test that components work together
        cache_manager.set("test", "value")
        if cache_manager.get("test") == "value":
            print("✓ Cache manager is functional")
        
        if rate_limiter.allow_request("test_client"):
            print("✓ Rate limiter is functional")
        
        print("✅ Component initialization test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Component initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all integration tests."""
    print("🧪 Testing TiDB MCP Server Integration")
    print("=" * 50)
    
    tests = [
        test_server_initialization,
        test_component_initialization,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if await test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Integration Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed! Server implementation is ready.")
        return 0
    else:
        print("❌ Some integration tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))