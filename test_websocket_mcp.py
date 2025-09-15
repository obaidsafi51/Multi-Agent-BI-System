#!/usr/bin/env python3
"""
Test WebSocket MCP Client Connection
"""

import asyncio
import json
import logging
import os
import sys
sys.path.append('./backend')

from backend.mcp_client import get_backend_mcp_client
from backend.websocket_mcp_client import WebSocketMCPClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_websocket_mcp_direct():
    """Test direct WebSocket MCP client."""
    print("🔗 Testing Direct WebSocket MCP Client")
    
    # Use environment-appropriate URL
    ws_url = "ws://localhost:8000/ws"  # TiDB MCP server WebSocket endpoint
    
    client = WebSocketMCPClient(server_url=ws_url, agent_type="backend_test")
    
    try:
        # Test connection
        connected = await client.connect()
        if connected:
            print("✅ Successfully connected to WebSocket MCP Server")
            
            # Test basic operations
            print("🔍 Testing database discovery...")
            databases = await client.discover_databases()
            print(f"📊 Found databases: {databases}")
            
            if databases:
                # Test table discovery
                first_db = databases[0] if isinstance(databases, list) else databases.get('databases', [{}])[0]
                db_name = first_db.get('name') if isinstance(first_db, dict) else str(first_db)
                
                if db_name:
                    print(f"🔍 Testing table discovery for {db_name}...")
                    tables = await client.discover_tables(db_name)
                    print(f"📋 Found tables: {tables}")
            
            # Test performance stats
            stats = client.get_cache_stats()
            print(f"📈 Cache stats: {stats}")
            
        else:
            print("❌ Failed to connect to WebSocket MCP Server")
            
    except Exception as e:
        print(f"💥 Error testing WebSocket MCP: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

async def test_backend_mcp_client():
    """Test backend MCP client (should use WebSocket if enabled)."""
    print("\n🔗 Testing Backend MCP Client")
    
    client = get_backend_mcp_client()
    print(f"Backend MCP Client - WebSocket mode: {client.use_websocket}")
    print(f"Backend MCP Client - Server URL: {client.server_url}")
    
    try:
        # Test connection
        connected = await client.connect()
        if connected:
            print("✅ Successfully connected to MCP Server")
            
            # Test basic operations
            print("🔍 Testing database discovery...")
            databases = await client.call_tool("list_databases")
            print(f"📊 Found databases: {databases}")
            
            # Get performance stats
            stats = client.get_performance_stats()
            print(f"📈 Performance stats: {json.dumps(stats, indent=2)}")
            
        else:
            print("❌ Failed to connect to MCP Server")
            
    except Exception as e:
        print(f"💥 Error testing Backend MCP: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

async def main():
    """Run all tests."""
    print("🚀 Starting WebSocket MCP Tests")
    print(f"Environment - USE_WEBSOCKET_MCP: {os.getenv('USE_WEBSOCKET_MCP', 'Not set')}")
    print(f"Environment - MCP_SERVER_WS_URL: {os.getenv('MCP_SERVER_WS_URL', 'Not set')}")
    
    # Test direct WebSocket connection
    await test_websocket_mcp_direct()
    
    # Test backend client
    await test_backend_mcp_client()
    
    print("🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
