#!/usr/bin/env python3
"""
Test WebSocket USE + SELECT functionality
"""
import asyncio
import websockets
import json
import uuid

async def test_websocket_use_select():
    """Test USE + SELECT via WebSocket"""
    print("🧪 Testing USE + SELECT via WebSocket...")
    
    try:
        # Connect to WebSocket
        uri = "ws://localhost:8012"
        print(f"📡 Connecting to {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to Data Agent WebSocket")
            
            # Test USE + SELECT query
            test_message = {
                "action": "execute_sql",
                "data": {
                    "sql_query": "USE `Retail_Business_Agentic_AI`; SELECT COUNT(*) as cashflow_count FROM cashflow WHERE YEAR(date) = 2024;",
                    "query_id": f"ws_test_{uuid.uuid4().hex[:8]}",
                    "execution_config": {
                        "timeout": 30,
                        "use_cache": False
                    }
                }
            }
            
            print("📤 Sending USE + SELECT query via WebSocket...")
            await websocket.send(json.dumps(test_message))
            
            # Receive response
            print("📥 Waiting for response...")
            response_raw = await websocket.recv()
            response = json.loads(response_raw)
            
            print("\n🔍 WebSocket Response:")
            print(f"✅ Success: {response.get('success', False)}")
            print(f"📊 Data: {response.get('data', [])}")
            print(f"📋 Columns: {response.get('columns', [])}")
            print(f"📈 Row Count: {response.get('row_count', 0)}")
            
            if response.get('error'):
                print(f"❌ Error: {response['error']}")
                return False
            
            # Check if we got the expected data
            data = response.get('data', [])
            if len(data) > 0 and 'cashflow_count' in data[0]:
                count = data[0]['cashflow_count']
                print(f"🎯 Cashflow count for 2024: {count}")
                if count == 649:
                    print("🎉 WebSocket USE + SELECT test PASSED!")
                    return True
                else:
                    print(f"⚠️ Unexpected count: {count} (expected 649)")
                    return False
            else:
                print("❌ No data received")
                return False
                
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 WebSocket USE + SELECT Test")
    print("=" * 50)
    
    success = await test_websocket_use_select()
    
    if success:
        print("\n🎉 All WebSocket tests PASSED!")
        return 0
    else:
        print("\n❌ WebSocket tests FAILED!")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        exit(1)
