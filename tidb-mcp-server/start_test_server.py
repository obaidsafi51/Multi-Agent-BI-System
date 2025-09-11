#!/usr/bin/env python3
"""
Simple startup script for Universal MCP Server testing.
"""

import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def setup_test_environment():
    """Setup test environment variables."""
    
    # Set test environment variables
    test_env = {
        # Database Configuration (will fail gracefully without real DB)
        'TIDB_HOST': 'localhost',
        'TIDB_PORT': '4000',
        'TIDB_USER': 'test_user',
        'TIDB_PASSWORD': 'test_password',
        'TIDB_DATABASE': 'test_db',
        'TIDB_SSL_VERIFY_CERT': 'false',
        'TIDB_SSL_VERIFY_IDENTITY': 'false',
        
        # LLM Configuration (mock for testing)
        'LLM_PROVIDER': 'kimi',
        'LLM_API_KEY': 'test-mock-api-key-for-testing',
        'LLM_BASE_URL': 'https://api.moonshot.cn/v1',
        'LLM_MODEL': 'moonshot-v1-8k',
        'LLM_MAX_TOKENS': '1000',
        'LLM_TEMPERATURE': '0.7',
        'LLM_TIMEOUT': '30',
        
        # Tools Configuration
        'ENABLED_TOOLS': 'database,llm',
        'DATABASE_TOOLS_ENABLED': 'true',
        'LLM_TOOLS_ENABLED': 'true',
        
        # MCP Server Configuration
        'MCP_SERVER_NAME': 'universal-mcp-server-test',
        'MCP_SERVER_VERSION': '1.0.0',
        'MCP_MAX_CONNECTIONS': '5',
        'MCP_REQUEST_TIMEOUT': '30',
        
        # Cache Configuration
        'CACHE_ENABLED': 'true',
        'CACHE_TTL_SECONDS': '60',
        'CACHE_MAX_SIZE': '100',
        
        # Security Configuration
        'MAX_QUERY_TIMEOUT': '10',
        'MAX_SAMPLE_ROWS': '10',
        'RATE_LIMIT_RPM': '100',
        
        # Logging Configuration
        'LOG_LEVEL': 'INFO',
        'LOG_FORMAT': 'text',
        
        # HTTP API Configuration
        'USE_HTTP_API': 'true'
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    print("✅ Test environment configured")
    print(f"   Database tools enabled: {os.environ.get('DATABASE_TOOLS_ENABLED')}")
    print(f"   LLM tools enabled: {os.environ.get('LLM_TOOLS_ENABLED')}")
    print(f"   Enabled tools: {os.environ.get('ENABLED_TOOLS')}")


def main():
    """Main function to start the server."""
    
    print("🚀 Starting Universal MCP Server for Testing")
    print("=" * 50)
    
    # Setup test environment
    setup_test_environment()
    
    try:
        # Import and run the server
        from tidb_mcp_server.main import main as server_main
        
        print("\n🌐 Starting HTTP API server on http://localhost:8000")
        print("📖 Available endpoints:")
        print("   GET  /health - Health check")
        print("   GET  /tools - List available tools") 
        print("   POST /tools/* - Execute tools")
        print("   GET  /status - Server status")
        print("\n💡 You can test the server with:")
        print("   python test_http_api.py")
        print("\n⏹️  Press Ctrl+C to stop the server")
        print("=" * 50)
        
        # Start the server
        server_main()
        
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped by user")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed:")
        print("   pip install fastapi uvicorn httpx pydantic pydantic-settings pymysql")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
