#!/usr/bin/env python3
"""
Test script to verify that schema context is properly passed from backend to NLP agent
"""

import asyncio
import aiohttp
import json
import sys

async def test_schema_context_passing():
    """Test that detailed schema context reaches the NLP agent"""
    
    # 1. Use existing session that already has database selected
    print("1. Using existing session with database already selected...")
    session_id = "session_1757843495030_o1xk3y38e"  # Known session from logs
    
    # 2. Send a test query to NLP agent and check what schema it receives
    print("2. Testing query processing with schema context...")
    query_payload = {
        "query": "show me cashflow of 2024",
        "query_id": "test_schema_query_123",
        "user_id": "test_user",
        "session_id": session_id,
        "context": {
            "timestamp": "2025-09-15T10:00:00Z",
            "source": "test_script"
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8001/process",
            json=query_payload
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ NLP processing successful")
                
                # Check if SQL was generated correctly
                sql_query = result.get('sql_query', '')
                if 'date_column' in sql_query:
                    print(f"❌ ISSUE FOUND: SQL still contains 'date_column' placeholder:")
                    print(f"   SQL: {sql_query}")
                    return False
                elif 'date' in sql_query and 'cashflow' in sql_query:
                    print(f"✅ SQL looks correct:")
                    print(f"   SQL: {sql_query}")
                    return True
                else:
                    print(f"⚠️  Unexpected SQL generated:")
                    print(f"   SQL: {sql_query}")
                    return False
            else:
                error = await response.text()
                print(f"❌ NLP processing failed: {error}")
                return False

if __name__ == "__main__":
    result = asyncio.run(test_schema_context_passing())
    if result:
        print("\n🎉 Schema context fix verification PASSED!")
        sys.exit(0)
    else:
        print("\n❌ Schema context fix verification FAILED!")
        sys.exit(1)
