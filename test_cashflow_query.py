import asyncio
import json
import websockets
import time

async def test_cashflow_query():
    try:
        # Connect to backend WebSocket
        uri = "ws://localhost:3001/ws"
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to backend WebSocket")
            
            # Send authentication
            auth_message = {
                "type": "auth",
                "user_id": "test_user_cashflow",
                "session_id": "test_session_cashflow"
            }
            await websocket.send(json.dumps(auth_message))
            auth_response = await websocket.recv()
            print(f"📧 Auth response: {json.loads(auth_response)}")
            
            # Send cashflow query
            query_message = {
                "type": "query",
                "message": "what is the cashflow for 2025",
                "user_id": "test_user_cashflow",
                "session_id": "test_session_cashflow"
            }
            await websocket.send(json.dumps(query_message))
            print("📤 Sent cashflow query")
            
            # Wait for response
            start_time = time.time()
            while time.time() - start_time < 30:  # 30 second timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    print(f"📥 Response: {data}")
                    
                    if data.get("type") == "query_result":
                        if data.get("success"):
                            print("✅ Query executed successfully!")
                            print(f"📊 Data: {data.get('data', [])}")
                            print(f"📈 Columns: {data.get('columns', [])}")
                            break
                        else:
                            print(f"❌ Query failed: {data.get('error')}")
                            break
                            
                except asyncio.TimeoutError:
                    print("⏳ Waiting for response...")
                    continue
                except Exception as e:
                    print(f"❌ Error receiving response: {e}")
                    break
            else:
                print("⏰ Query timed out")
                
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_cashflow_query())
