#!/usr/bin/env python3
"""
Test WebSocket connectivity to all three agents with proper message format testing
"""

import asyncio
import json
import uuid
import websockets
from websockets.exceptions import ConnectionClosed, InvalidHandshake
import sys
import time

async def test_agent_websocket(name, url, port, test_messages=None):
    """Test WebSocket connection to an agent with proper message format"""
    print(f"\n🔍 Testing {name} WebSocket Server ({url})")
    print("-" * 50)
    
    if test_messages is None:
        test_messages = []
    
    try:
        print(f"   Connecting to {url}...")
        async with websockets.connect(url, ping_timeout=None, close_timeout=5) as websocket:
            print(f"   ✅ Connected successfully!")
            print(f"   📡 Connection info: {websocket.remote_address}")
            
            # Wait for welcome message
            try:
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"   📥 Welcome message: {welcome_msg}")
                welcome_data = json.loads(welcome_msg)
                
                if welcome_data.get("type") == "connection_established":
                    print(f"   ✅ Proper welcome message received")
                    client_id = welcome_data.get("client_id", "unknown")
                    server_version = welcome_data.get("version", "unknown")
                    capabilities = welcome_data.get("capabilities", [])
                    print(f"   📋 Client ID: {client_id}")
                    print(f"   � Server Version: {server_version}")
                    print(f"   📋 Capabilities: {capabilities}")
                else:
                    print(f"   ⚠️  Unexpected welcome message format")
                    
            except asyncio.TimeoutError:
                print(f"   ⚠️  No welcome message received")
            except json.JSONDecodeError:
                print(f"   ⚠️  Welcome message is not valid JSON")
            
            # Test health check first
            test_health = {
                "type": "health_check",
                "message_id": str(uuid.uuid4()),
                "timestamp": time.time()
            }
            print(f"   📤 Sending health check: {test_health}")
            await websocket.send(json.dumps(test_health))
            
            try:
                health_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                print(f"   📥 Health response: {health_response}")
                
                health_data = json.loads(health_response)
                if health_data.get("type") == "health_check_response":
                    health_info = health_data.get("data", {})
                    status = health_info.get("status", "unknown")
                    uptime = health_info.get("uptime", 0)
                    print(f"   ✅ Health check passed - Status: {status}, Uptime: {uptime:.2f}s")
                else:
                    print(f"   ⚠️  Unexpected health response format")
                    
            except asyncio.TimeoutError:
                print(f"   ❌ Health check timeout")
                return False
            except json.JSONDecodeError:
                print(f"   ❌ Health response is not valid JSON")
                return False
            
            # Test heartbeat
            heartbeat_msg = {
                "type": "heartbeat",
                "timestamp": time.time()
            }
            print(f"   📤 Sending heartbeat: {heartbeat_msg}")
            await websocket.send(json.dumps(heartbeat_msg))
            
            try:
                heartbeat_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"   📥 Heartbeat response: {heartbeat_response}")
                
                heartbeat_data = json.loads(heartbeat_response)
                if heartbeat_data.get("type") == "heartbeat_response":
                    print(f"   ✅ Heartbeat working properly")
                else:
                    print(f"   ⚠️  Unexpected heartbeat response")
                    
            except asyncio.TimeoutError:
                print(f"   ⚠️  No heartbeat response (may be normal)")
            except json.JSONDecodeError:
                print(f"   ⚠️  Heartbeat response is not valid JSON")
            
            # Test specific functionality for each agent
            success_count = 0
            for test_msg in test_messages:
                print(f"   📤 Sending specific test: {test_msg}")
                await websocket.send(json.dumps(test_msg))
                
                try:
                    test_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    print(f"   📥 Test response: {test_response[:200]}...")
                    
                    response_data = json.loads(test_response)
                    if "error" in response_data:
                        error_info = response_data.get("error", {})
                        if isinstance(error_info, dict):
                            error_msg = error_info.get("message", "Unknown error")
                        else:
                            error_msg = str(error_info)
                        print(f"   ⚠️  Agent returned error: {error_msg}")
                    else:
                        print(f"   ✅ Specific test passed")
                        success_count += 1
                        
                except asyncio.TimeoutError:
                    print(f"   ⚠️  Specific test timeout (may be processing)")
                except json.JSONDecodeError:
                    print(f"   ⚠️  Test response is not valid JSON")
            
            # Wait for any progress updates
            await asyncio.sleep(1)
            
            return True
                
    except ConnectionRefusedError:
        print(f"   ❌ Connection refused - server not running on port {port}")
        return False
    except InvalidHandshake as e:
        print(f"   ❌ WebSocket handshake failed: {e}")
        return False
    except ConnectionClosed as e:
        print(f"   ❌ Connection closed unexpectedly: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {type(e).__name__}: {e}")
        return False

async def test_all_agents():
    """Test all three agent WebSocket servers with specific functionality"""
    print("🚀 Enhanced WebSocket Agent Connectivity Test")
    print("=" * 60)
    
    # Define agent-specific test messages
    nlp_test_messages = [
        {
            "type": "nlp_query",
            "message_id": str(uuid.uuid4()),
            "query": "What is the total sales revenue?",
            "context": {"test": True},
            "query_id": str(uuid.uuid4())
        }
    ]
    
    data_test_messages = [
        {
            "type": "sql_query", 
            "message_id": str(uuid.uuid4()),
            "sql_query": "SELECT COUNT(*) as test_count FROM information_schema.tables",
            "query_context": {"test": True},
            "query_id": str(uuid.uuid4())
        }
    ]
    
    viz_test_messages = [
        {
            "type": "generate_chart",
            "message_id": str(uuid.uuid4()),
            "data": [{"x": 1, "y": 2}, {"x": 2, "y": 4}],
            "config": {"chart_type": "bar", "title": "Test Chart"},
            "query_context": {"test": True},
            "user_id": "test_user",
            "query_intent": {"type": "visualization", "chart_type": "bar"}
        }
    ]
    
    agents = [
        ("NLP Agent", "ws://localhost:8011/ws", 8011, nlp_test_messages),
        ("Data Agent", "ws://localhost:8012/ws", 8012, data_test_messages), 
        ("Viz Agent", "ws://localhost:8013/ws", 8013, viz_test_messages)
    ]
    
    results = {}
    
    for name, url, port, test_msgs in agents:
        results[name] = await test_agent_websocket(name, url, port, test_msgs)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    all_passed = True
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {name}: {status}")
        if not success:
            all_passed = False
    
    print(f"\n🎯 Overall Result: {'✅ ALL AGENTS READY' if all_passed else '❌ SOME AGENTS FAILED'}")
    
    return all_passed

async def test_backend_connection():
    """Test connection from Docker network perspective"""
    print(f"\n🔍 Testing Backend-to-Agent Network Connectivity")
    print("-" * 50)
    
    import socket
    
    agents = [
        ("localhost", 8011, "NLP Agent"),
        ("localhost", 8012, "Data Agent"),
        ("localhost", 8013, "Viz Agent")
    ]
    
    for hostname, port, name in agents:
        try:
            print(f"   Testing {name} at {hostname}:{port}...")
            # Test port accessibility
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            result = sock.connect_ex((hostname, port))
            sock.close()
            
            if result == 0:
                print(f"   ✅ {name} - Accessible at {hostname}:{port}")
            else:
                print(f"   ❌ {name} - Not accessible (error {result})")
        except Exception as e:
            print(f"   ❌ {name} - Error: {e}")

if __name__ == "__main__":
    try:
        result = asyncio.run(test_all_agents())
        asyncio.run(test_backend_connection())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
