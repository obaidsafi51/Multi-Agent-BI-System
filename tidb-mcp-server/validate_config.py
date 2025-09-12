#!/usr/bin/env python3
"""
Configuration Validation Script for TiDB MCP Server
This script helps validate your configuration setup in different environments.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def check_environment_type():
    """Check what type of environment we're running in."""
    from tidb_mcp_server.config import _is_containerized_environment
    
    is_containerized = _is_containerized_environment()
    
    print("🔍 Environment Detection")
    print("=" * 50)
    
    if is_containerized:
        print("✅ Detected: CONTAINERIZED environment (Docker/Kubernetes)")
        print("   - Configuration will be loaded from environment variables")
        print("   - .env files will be ignored")
    else:
        print("✅ Detected: LOCAL DEVELOPMENT environment")
        print("   - Configuration will attempt to load from .env files")
        print("   - Falls back to environment variables if no .env found")
    
    print()
    return is_containerized

def check_environment_variables():
    """Check critical environment variables."""
    print("🔧 Environment Variables Check")
    print("=" * 50)
    
    # Critical variables
    critical_vars = {
        'TIDB_HOST': 'TiDB database host',
        'TIDB_USER': 'TiDB database user',
        'TIDB_PASSWORD': 'TiDB database password',
        'TIDB_DATABASE': 'TiDB database name',
        'LLM_API_KEY': 'LLM API key for KIMI/Moonshot'
    }
    
    # Optional but important
    optional_vars = {
        'LLM_PROVIDER': 'LLM provider (defaults to kimi)',
        'LLM_BASE_URL': 'LLM API base URL',
        'LLM_MODEL': 'LLM model name',
        'LOG_LEVEL': 'Logging level',
        'ENABLED_TOOLS': 'Comma-separated list of enabled tools'
    }
    
    print("Critical Variables:")
    all_critical_present = True
    for var, description in critical_vars.items():
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            display_value = "***" if "PASSWORD" in var or "KEY" in var else value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: NOT SET ({description})")
            all_critical_present = False
    
    print("\nOptional Variables:")
    for var, description in optional_vars.items():
        value = os.environ.get(var)
        if value:
            print(f"  ✅ {var}: {value}")
        else:
            print(f"  ⚪ {var}: not set ({description})")
    
    print()
    return all_critical_present

def check_dotenv_files():
    """Check for .env files in expected locations."""
    print("📁 .env File Detection")
    print("=" * 50)
    
    env_paths = [
        ".env",  # Current directory
        os.path.join(os.path.dirname(__file__), "..", ".env"),  # Parent directory
        os.path.join(os.getcwd(), ".env"),  # Working directory
        os.path.expanduser("~/.config/tidb-mcp-server/.env"),  # User config
    ]
    
    found_files = []
    for env_path in env_paths:
        abs_path = os.path.abspath(env_path)
        if os.path.exists(abs_path):
            print(f"  ✅ Found: {abs_path}")
            found_files.append(abs_path)
        else:
            print(f"  ⚪ Not found: {abs_path}")
    
    if not found_files:
        print("  ⚠️  No .env files found in expected locations")
    
    print()
    return found_files

def test_configuration_loading():
    """Test actually loading the configuration."""
    print("⚙️  Configuration Loading Test")
    print("=" * 50)
    
    try:
        from tidb_mcp_server.config import load_config
        
        print("Attempting to load configuration...")
        config = load_config()
        
        print("✅ Configuration loaded successfully!")
        print(f"   - TiDB Host: {config.tidb_host}")
        print(f"   - LLM Provider: {config.llm_provider}")
        print(f"   - MCP Server: {config.mcp_server_name} v{config.mcp_server_version}")
        print(f"   - Enabled Tools: {', '.join(config.enabled_tools)}")
        print(f"   - Cache Enabled: {config.cache_enabled}")
        
        return True, config
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        print("   This indicates missing or invalid configuration values")
        return False, None

def main():
    """Run complete configuration validation."""
    print("🚀 TiDB MCP Server Configuration Validator")
    print("=" * 60)
    print()
    
    # Check environment type
    is_containerized = check_environment_type()
    
    # Check environment variables
    env_vars_ok = check_environment_variables()
    
    # Check .env files (mainly for local development)
    if not is_containerized:
        env_files = check_dotenv_files()
    
    # Test configuration loading
    config_ok, config = test_configuration_loading()
    
    # Summary
    print("📋 Summary")
    print("=" * 50)
    
    if config_ok:
        print("✅ CONFIGURATION IS VALID")
        print("   Your TiDB MCP Server should start without issues")
    else:
        print("❌ CONFIGURATION HAS ISSUES")
        print("   Please fix the above issues before starting the server")
        
        if is_containerized:
            print("\n💡 For Docker deployment:")
            print("   - Ensure all environment variables are set in docker-compose.yml")
            print("   - Check that your .env file in the project root has all required values")
        else:
            print("\n💡 For local development:")
            print("   - Create a .env file in the project root")
            print("   - Add all required environment variables to the .env file")
            print("   - Use the .env.example file as a template")
    
    print()
    return 0 if config_ok else 1

if __name__ == "__main__":
    sys.exit(main())
