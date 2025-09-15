#!/usr/bin/env python3
"""
Test session management and WebSocket connection handling on reload
"""

import requests
import websocket
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor

def test_websocket_session_management():
    """Test WebSocket session management during simulated page reloads"""
    print("🧪 Testing WebSocket Session Management...")
    
    connections = []
    
    def create_connection(user_id, connection_name):
        """Create a WebSocket connection"""
        try:
            ws_url = f"ws://localhost:8080/ws/query/{user_id}"
            print(f"   📡 {connection_name}: Connecting to {ws_url}")
            
            ws = websocket.create_connection(ws_url, timeout=5)
            print(f"   ✅ {connection_name}: Connected successfully")
            
            # Send a test message
            test_msg = {
                "type": "test",
                "message": f"Hello from {connection_name}",
                "timestamp": time.time()
            }
            ws.send(json.dumps(test_msg))
            
            # Try to receive a response (with timeout)
            ws.settimeout(2)
            try:
                response = ws.recv()
                print(f"   📨 {connection_name}: Received: {response[:100]}...")
            except:
                print(f"   ⏰ {connection_name}: No response received (timeout)")
            
            connections.append((connection_name, ws))
            return ws
            
        except Exception as e:
            print(f"   ❌ {connection_name}: Failed to connect: {e}")
            return None
    
    def close_connection(connection_name, ws):
        """Close a WebSocket connection"""
        try:
            ws.close()
            print(f"   🔌 {connection_name}: Disconnected")
        except Exception as e:
            print(f"   ⚠️  {connection_name}: Error closing: {e}")
    
    # Test 1: Simulate normal connection
    print("\n1️⃣ Testing normal connection...")
    user_id_1 = f"user_{int(time.time())}_test1"
    ws1 = create_connection(user_id_1, "Connection-1")
    
    if ws1:
        time.sleep(1)
        
        # Test 2: Simulate page reload (same user ID, new connection)
        print("\n2️⃣ Simulating page reload (same user ID)...")
        ws2 = create_connection(user_id_1, "Connection-2-Reload")
        
        if ws2:
            time.sleep(1)
            
            # Test 3: Check if old connection is still active
            print("\n3️⃣ Testing old connection status...")
            try:
                ws1.ping()
                print("   ⚠️  Connection-1: Still active (potential conflict)")
            except:
                print("   ✅ Connection-1: Properly closed")
            
            # Test 4: Try multiple rapid connections (stress test)
            print("\n4️⃣ Testing rapid connection attempts...")
            user_id_2 = f"user_{int(time.time())}_test2"
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for i in range(3):
                    future = executor.submit(create_connection, user_id_2, f"Rapid-{i+1}")
                    futures.append(future)
                
                time.sleep(2)
                
                # Check results
                active_connections = 0
                for future in futures:
                    try:
                        ws = future.result(timeout=1)
                        if ws and ws.connected:
                            active_connections += 1
                    except:
                        pass
                
                print(f"   📊 Active connections from rapid test: {active_connections}")
    
    # Cleanup all connections
    print("\n5️⃣ Cleaning up connections...")
    for name, ws in connections:
        close_connection(name, ws)
    
    print("\n✅ Session management test completed!")

def test_backend_websocket_handling():
    """Test backend's handling of WebSocket connections"""
    print("\n🔍 Testing Backend WebSocket Handling...")
    
    try:
        # Check if backend is responsive
        response = requests.get("http://localhost:8080/health", timeout=5)
        print(f"   ✅ Backend health check: {response.status_code}")
        
        # Check WebSocket endpoint availability
        user_id = f"test_user_{int(time.time())}"
        ws_url = f"ws://localhost:8080/ws/query/{user_id}"
        
        try:
            ws = websocket.create_connection(ws_url, timeout=5)
            print(f"   ✅ WebSocket endpoint accessible")
            ws.close()
        except Exception as e:
            print(f"   ❌ WebSocket endpoint error: {e}")
            
    except Exception as e:
        print(f"   ❌ Backend check failed: {e}")

if __name__ == "__main__":
    print("🔧 WebSocket Session Management Test Suite")
    print("=" * 50)
    
    test_backend_websocket_handling()
    test_websocket_session_management()
    
    print("\n" + "=" * 50)
    print("🎯 Test completed! Check logs above for any issues.")
