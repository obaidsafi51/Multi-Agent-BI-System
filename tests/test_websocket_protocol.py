#!/usr/bin/env python3
"""
Test WebSocket agents with proper message protocol
"""
import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed

async def test_agent_websocket(url, agent_name):
    """Test WebSocket connection to agent with proper protocol"""
    try:
        print(f"Testing {agent_name} WebSocket at {url}...")
        
        async with websockets.connect(url) as websocket:
            print(f"✅ Connected to {agent_name}")
            
            # Send a health check message
            health_message = {
                "type": "health_check",
                "message_id": "test_001",
                "timestamp": "2025-09-13T06:15:00Z",
                "test": True
            }
            
            print(f"Sending health check: {health_message}")
            await websocket.send(json.dumps(health_message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"✅ Response from {agent_name}: {response}")
                return True
            except asyncio.TimeoutError:
                print(f"⚠️  No response from {agent_name} within 5 seconds")
                return True  # Connected but no response
                
    except ConnectionClosed as e:
        print(f"❌ Connection to {agent_name} closed: {e}")
        return False
    except Exception as e:
        print(f"❌ Failed to connect to {agent_name}: {e}")
        return False

async def test_all_websockets():
    """Test all WebSocket agents"""
    print("🔍 Testing WebSocket Agent Connectivity with Proper Protocol")
    print("=" * 60)
    
    agents = [
        ("ws://localhost:8011", "NLP Agent"),
        ("ws://localhost:8012", "Data Agent"),
        ("ws://localhost:8013", "Viz Agent")
    ]
    
    results = []
    for url, name in agents:
        result = await test_agent_websocket(url, name)
        results.append((name, result))
        print()
    
    print("📊 WebSocket Connectivity Summary:")
    print("-" * 30)
    for name, connected in results:
        status = "✅ Connected" if connected else "❌ Failed"
        print(f"{name}: {status}")

if __name__ == "__main__":
    asyncio.run(test_all_websockets())
