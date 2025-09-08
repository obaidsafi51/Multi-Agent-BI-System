#!/usr/bin/env python3
"""
Simple health check script for Docker health checks.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, '/app')

async def main():
    """Main health check function."""
    try:
        # Import and check MCP server health
        from schema_management.health_check import check_mcp_server_health
        
        result = await check_mcp_server_health()
        
        if result["status"] == "healthy":
            print("MCP server is healthy")
            sys.exit(0)
        else:
            print(f"MCP server is unhealthy: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except ImportError as e:
        print(f"Import error: {e}")
        # Fallback to basic configuration check
        try:
            from schema_management.config import load_mcp_config
            config = load_mcp_config()
            print(f"Configuration loaded successfully: {config.mcp_server_url}")
            sys.exit(0)
        except Exception as config_error:
            print(f"Configuration error: {config_error}")
            sys.exit(1)
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())