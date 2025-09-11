#!/usr/bin/env python3
"""
Quick configuration test for Universal MCP Server.
"""

import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_config():
    """Test configuration loading."""
    
    print("🔧 Testing Universal MCP Server Configuration")
    print("=" * 50)
    
    # Set minimal test environment
    os.environ.update({
        'TIDB_HOST': 'localhost',
        'TIDB_USER': 'test',
        'TIDB_PASSWORD': 'test',
        'LLM_API_KEY': 'test-key',
        'DATABASE_TOOLS_ENABLED': 'true',
        'LLM_TOOLS_ENABLED': 'true',
        'ENABLED_TOOLS': 'database,llm',
    })
    
    try:
        from tidb_mcp_server.config import load_config
        
        print("✅ Config module imported successfully")
        
        config = load_config()
        print(f"✅ Configuration loaded successfully")
        print(f"   Server name: {config.mcp_server_name}")
        print(f"   Server version: {config.mcp_server_version}")
        print(f"   Database tools enabled: {config.database_tools_enabled}")
        print(f"   LLM tools enabled: {config.llm_tools_enabled}")
        print(f"   Enabled tools: {config.enabled_tools}")
        
        # Test configuration objects
        db_config = config.get_database_config()
        print(f"✅ Database config: {db_config.host}:{db_config.port}")
        
        llm_config = config.get_llm_config()
        print(f"✅ LLM config: {llm_config.provider} - {llm_config.model}")
        
        tools_config = config.get_tools_config()
        print(f"✅ Tools config: {tools_config.enabled_tools}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_imports():
    """Test module imports."""
    
    print("\n📦 Testing Module Imports")
    print("=" * 30)
    
    modules_to_test = [
        ('tidb_mcp_server.config', 'Configuration'),
        ('tidb_mcp_server.cache_manager', 'Cache Manager'),
        ('tidb_mcp_server.database', 'Database'),
        ('tidb_mcp_server.llm_tools', 'LLM Tools'),
        ('tidb_mcp_server.mcp_tools', 'MCP Tools'),
        ('tidb_mcp_server.mcp_server', 'MCP Server'),
    ]
    
    passed = 0
    total = len(modules_to_test)
    
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {description}: Imported successfully")
            passed += 1
        except Exception as e:
            print(f"❌ {description}: Import failed - {e}")
    
    print(f"\n📊 Import Results: {passed}/{total} modules imported successfully")
    return passed == total


def test_tools_initialization():
    """Test tools initialization."""
    
    print("\n🛠️ Testing Tools Initialization")
    print("=" * 35)
    
    try:
        from tidb_mcp_server.cache_manager import CacheManager
        from tidb_mcp_server.config import LLMConfig
        from tidb_mcp_server import llm_tools
        
        # Test cache manager
        cache = CacheManager(default_ttl=60)
        print("✅ Cache manager created")
        
        # Test LLM config
        llm_config = LLMConfig(
            provider="kimi",
            api_key="test-key",
            model="moonshot-v1-8k"
        )
        print("✅ LLM config created")
        
        # Test LLM tools initialization
        llm_tools.initialize_llm_tools(llm_config, cache)
        print("✅ LLM tools initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Tools initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    
    print("🧪 Universal MCP Server - Quick Configuration Test")
    print("=" * 60)
    
    tests = [
        ("Configuration Loading", test_config),
        ("Module Imports", test_imports),
        ("Tools Initialization", test_tools_initialization),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)
    print(f"🎯 Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All configuration tests passed!")
        print("✅ Universal MCP Server is ready to run")
    else:
        print("⚠️ Some tests failed. Check the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
