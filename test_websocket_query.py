#!/usr/bin/env python3
"""
Test WebSocket Query Endpoint

Tests the new /ws/query/{user_id} endpoint with proper query processing.
"""

import asyncio
import json
import websockets
import time


async def test_websocket_query():
    """Test the WebSocket query endpoint"""
    user_id = "test_user_123"
    uri = f"ws://localhost:8080/ws/query/{user_id}"
    
    print(f"Connecting to {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Wait for connection established message
            initial_message = await websocket.recv()
            initial_data = json.loads(initial_message)
            print(f"📨 Initial message: {initial_data}")
            
            # Test 1: Send a heartbeat
            print("\n🔄 Testing heartbeat...")
            heartbeat_msg = {
                "type": "heartbeat",
                "correlation_id": "heartbeat_test_1",
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(heartbeat_msg))
            
            # Wait for heartbeat response
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"💓 Heartbeat response: {response_data}")
            
            # Test 2: Get available databases
            print("\n🗃️ Testing database list...")
            db_list_msg = {
                "type": "get_databases",
                "correlation_id": "db_list_test_1",
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(db_list_msg))
            
            # Wait for database list response
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"🗃️ Database list response: {response_data}")
            
            # Test 3: Select a database (if available)
            if response_data.get("databases"):
                print("\n📋 Testing database selection...")
                db_select_msg = {
                    "type": "database_select",
                    "database_name": "Agentic_BI",
                    "session_id": f"ws_test_session_{int(time.time())}",
                    "correlation_id": "db_select_test_1",
                    "timestamp": time.time()
                }
                await websocket.send(json.dumps(db_select_msg))
                
                # Wait for database selection response
                response = await websocket.recv()
                response_data = json.loads(response)
                print(f"📋 Database selection response: {response_data}")
                
                # Test 4: Send a query
                print("\n🔍 Testing query processing...")
                query_msg = {
                    "type": "query",
                    "query": "show me revenue data",
                    "session_id": db_select_msg["session_id"],
                    "correlation_id": "query_test_1",
                    "timestamp": time.time()
                }
                await websocket.send(json.dumps(query_msg))
                
                # Wait for query processing messages
                print("⏳ Waiting for query processing messages...")
                for i in range(5):  # Wait for up to 5 messages
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        response_data = json.loads(response)
                        print(f"🔍 Query message {i+1}: {response_data.get('type', 'unknown')} - {response_data}")
                        
                        if response_data.get("type") == "query_response":
                            print("✅ Query processing completed!")
                            break
                    except asyncio.TimeoutError:
                        print(f"⏰ Timeout waiting for message {i+1}")
                        break
            else:
                print("⚠️ No databases available for testing query")
            
            print("\n🎉 WebSocket test completed!")
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ Connection closed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket_query())
