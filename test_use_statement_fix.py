#!/usr/bin/env python3
"""
Test script to verify that the MCP server now accepts USE statements.
"""

import asyncio
import sys
import os
import requests
import json
from datetime import datetime

# Add backend to path
sys.path.append('./backend')

async def test_use_statements():
    """Test various USE statement scenarios with the MCP server"""
    print("🧪 Testing USE statement support in MCP server...")
    print("=" * 60)
    
    # Test 1: Direct HTTP API call to MCP server
    print("\n1️⃣ Testing direct MCP server HTTP API...")
    try:
        mcp_server_url = "http://localhost:8000"
        
        # Test standalone USE statement
        use_query = "USE Agentic_BI"
        payload = {"query": use_query, "timeout": 30}
        
        response = requests.post(f"{mcp_server_url}/tools/execute_query_tool", 
                               json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Standalone USE statement: {result}")
        else:
            print(f"❌ Standalone USE statement failed: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"❌ Direct MCP server test failed: {e}")
    
    # Test 2: USE + SELECT combination
    print("\n2️⃣ Testing USE + SELECT combination...")
    try:
        combined_query = "USE Agentic_BI; SELECT 1 as test_value;"
        payload = {"query": combined_query, "timeout": 30}
        
        response = requests.post(f"{mcp_server_url}/tools/execute_query_tool", 
                               json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ USE + SELECT combination: {result}")
        else:
            print(f"❌ USE + SELECT combination failed: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"❌ USE + SELECT test failed: {e}")
    
    # Test 3: Backend API test
    print("\n3️⃣ Testing through backend API...")
    try:
        backend_url = "http://localhost:8000"
        query_payload = {
            "query": "Show me the cash flow for revenue",
            "session_id": f"test_session_{int(datetime.now().timestamp())}"
        }
        
        # First select a database
        print("   📋 Selecting database...")
        db_select_payload = {
            "database_name": "Agentic_BI",
            "session_id": query_payload["session_id"]
        }
        
        db_response = requests.post(f"{backend_url}/api/database/select", 
                                  json=db_select_payload, timeout=10)
        
        if db_response.status_code == 200:
            print("   ✅ Database selected successfully")
            
            # Now test the query
            print("   🔍 Testing query processing...")
            query_response = requests.post(f"{backend_url}/api/query", 
                                         json=query_payload, timeout=30)
            
            if query_response.status_code == 200:
                result = query_response.json()
                if result.get("error"):
                    print(f"   ❌ Query failed: {result['error']}")
                else:
                    print(f"   ✅ Query succeeded: {len(result.get('result', {}).get('data', []))} rows")
            else:
                print(f"   ❌ Query request failed: {query_response.status_code}")
        else:
            print(f"   ❌ Database selection failed: {db_response.status_code}")
    
    except Exception as e:
        print(f"❌ Backend API test failed: {e}")
    
    # Test 4: MCP client test
    print("\n4️⃣ Testing through MCP client...")
    try:
        from mcp_client import get_backend_mcp_client
        
        client = get_backend_mcp_client()
        
        # Test connection
        if await client.connect():
            print("   ✅ MCP client connected")
            
            # Test USE statement
            use_result = await client.execute_query("USE Agentic_BI")
            print(f"   🔧 USE statement result: {use_result}")
            
            # Test combined query
            combined_result = await client.execute_query("USE Agentic_BI; SELECT 1 as test")
            print(f"   🔧 Combined query result: {combined_result}")
            
            await client.disconnect()
        else:
            print("   ❌ Failed to connect to MCP client")
    
    except Exception as e:
        print(f"❌ MCP client test failed: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 USE statement tests completed!")


if __name__ == "__main__":
    asyncio.run(test_use_statements())
