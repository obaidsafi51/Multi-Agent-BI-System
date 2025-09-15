#!/usr/bin/env python3
"""
Simple test to verify WebSocket MCP communication is working.
"""

import asyncio
import json
import time
import aiohttp
import websockets


async def test_http_endpoint():
    """Test HTTP MCP endpoint."""
    print("🌐 Testing HTTP MCP endpoint...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/tools/get_server_stats_tool",
                json={},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ HTTP endpoint working")
                    return data
                else:
                    print(f"❌ HTTP endpoint failed: {response.status}")
                    return None
    except Exception as e:
        print(f"❌ HTTP test error: {e}")
        return None


async def test_websocket_endpoint():
    """Test WebSocket MCP endpoint."""
    print("🔌 Testing WebSocket MCP endpoint...")
    try:
        uri = "ws://localhost:8000/ws"
        async with websockets.connect(uri) as websocket:
            # Send connection message
            connection_msg = {
                "type": "connection",
                "agent_id": "test_client_001",
                "agent_type": "test",
                "capabilities": ["batch_requests"],
                "timestamp": time.time()
            }
            
            await websocket.send(json.dumps(connection_msg))
            
            # Wait for connection acknowledgment
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            if response_data.get("type") == "connection_ack":
                print("✅ WebSocket connection established")
                
                # Test a simple request
                request_msg = {
                    "type": "request",
                    "request_id": "test_001",
                    "method": "get_server_stats",
                    "params": {},
                    "timestamp": time.time()
                }
                
                await websocket.send(json.dumps(request_msg))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                if response_data.get("type") == "response":
                    print("✅ WebSocket request/response working")
                    return response_data.get("data")
                else:
                    print(f"❌ Unexpected WebSocket response: {response_data}")
                    return None
            else:
                print(f"❌ WebSocket connection failed: {response_data}")
                return None
                
    except Exception as e:
        print(f"❌ WebSocket test error: {e}")
        return None


async def test_backend_websocket_config():
    """Test if backend is configured for WebSocket."""
    print("🔧 Testing backend WebSocket configuration...")
    try:
        async with aiohttp.ClientSession() as session:
            # Test backend health
            async with session.get("http://localhost:8080/health") as response:
                if response.status == 200:
                    print("✅ Backend is running")
                    
                    # Try to get some performance stats if available
                    try:
                        async with session.get("http://localhost:8080/api/stats") as stats_response:
                            if stats_response.status == 200:
                                stats = await stats_response.json()
                                print("✅ Backend stats available")
                                return stats
                    except:
                        pass
                        
                    return {"backend_status": "healthy"}
                else:
                    print(f"❌ Backend not healthy: {response.status}")
                    return None
    except Exception as e:
        print(f"❌ Backend test error: {e}")
        return None


async def main():
    """Run all tests."""
    print("🧪 WebSocket MCP Configuration Test")
    print("="*50)
    
    # Test HTTP endpoint
    http_result = await test_http_endpoint()
    
    print()
    
    # Test WebSocket endpoint
    ws_result = await test_websocket_endpoint()
    
    print()
    
    # Test backend
    backend_result = await test_backend_websocket_config()
    
    print()
    print("="*50)
    print("📊 Test Results Summary:")
    
    if http_result:
        print("✅ HTTP MCP Server: Working")
        # Show request deduplication stats if available
        dedup_stats = http_result.get("request_deduplication")
        if dedup_stats:
            print(f"   📈 Deduplication: {dedup_stats.get('effectiveness_percent', 0)}% effective")
            print(f"   📊 Cache size: {dedup_stats.get('cache_size', 0)} entries")
    else:
        print("❌ HTTP MCP Server: Failed")
    
    if ws_result:
        print("✅ WebSocket MCP Server: Working")
        # Show any cache stats
        cache_stats = ws_result.get("cache") if ws_result else None
        if cache_stats:
            print(f"   💾 Cache hit rate: {cache_stats.get('hit_rate_percent', 0)}%")
    else:
        print("❌ WebSocket MCP Server: Failed")
    
    if backend_result:
        print("✅ Backend Service: Working")
    else:
        print("❌ Backend Service: Failed")
    
    print()
    
    if http_result and ws_result:
        print("🎉 WebSocket MCP configuration is working!")
        print("   The system can now benefit from:")
        print("   • Persistent connections")
        print("   • Request deduplication") 
        print("   • Client-side caching")
        print("   • Real-time updates")
    else:
        print("⚠️  Some components are not working properly.")
        print("   Check the logs for more details:")
        print("   docker compose logs tidb-mcp-server")
        print("   docker compose logs backend")


if __name__ == "__main__":
    asyncio.run(main())
