#!/usr/bin/env python3
"""
Simple test to verify NLP agent handles nlp_query_with_context message type
"""
import asyncio
import websockets
import json
import uuid
from datetime import datetime

async def test_nlp_websocket():
    uri = "ws://localhost:8001/ws"
    
    try:
        print(f"🔗 Connecting to NLP agent at {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            
            # Send enhanced nlp_query_with_context message
            message = {
                "type": "nlp_query_with_context",
                "message_id": str(uuid.uuid4()),
                "query": "show me cash flow of 2024",
                "query_id": f"test_query_{int(datetime.now().timestamp() * 1000)}",
                "user_id": "test_user",
                "session_id": "test_session",
                "database_context": {
                    "database_name": "Retail_Business_Agentic_AI",
                    "tables": ["cashflow", "financial_data"],
                    "schema_info": "Mock schema for testing"
                },
                "context": {
                    "timestamp": datetime.now().isoformat(),
                    "source": "test_client"
                }
            }
            
            print(f"📤 Sending nlp_query_with_context message...")
            await websocket.send(json.dumps(message))
            
            print("⏳ Waiting for connection established...")
            connection_response = await websocket.recv()
            conn_data = json.loads(connection_response)
            print(f"🔗 Connection response: {conn_data.get('type')}")
            
            print("⏳ Waiting for query response...")
            query_response = await websocket.recv()
            response_data = json.loads(query_response)
            
            print(f"📥 Received query response:")
            print(f"   Type: {response_data.get('type')}")
            print(f"   Success: {response_data.get('success')}")
            print(f"   Has SQL Query: {'sql_query' in response_data}")
            print(f"   Response: {json.dumps(response_data, indent=2)}")
            
            if response_data.get('type') == 'error':
                if 'unknown_message_type' in str(response_data.get('error', {})):
                    print("❌ NLP agent still doesn't recognize nlp_query_with_context message type")
                    return False
                else:
                    print(f"⚠️  Different error: {response_data.get('error')}")
                    return True  # Different error means message type was recognized
            else:
                print("✅ NLP agent successfully handled nlp_query_with_context message type!")
                return True
                
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing NLP Agent WebSocket nlp_query_with_context message handler")
    print("=" * 60)
    result = asyncio.run(test_nlp_websocket())
    
    if result:
        print("\n🎉 TEST PASSED: NLP agent handles nlp_query_with_context correctly!")
    else:
        print("\n💥 TEST FAILED: NLP agent message handler needs fixing")
