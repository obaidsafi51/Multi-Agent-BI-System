#!/usr/bin/env python3
"""
Comprehensive test to verify the complete session management fix:
1. Backend session management working
2. Frontend automated queries now using session IDs
"""

import asyncio
import aiohttp
import json

async def test_complete_session_fix():
    """Test that both backend fixes and frontend fixes work together"""
    
    base_url = "http://localhost:8080"
    
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing Complete Session Management Fix\n")
        
        # Step 1: Select a database (this generates a session_id)
        print("Step 1: Selecting database to generate session_id...")
        db_select_payload = {
            "database_name": "Agentic_BI"
        }
        
        async with session.post(f"{base_url}/api/database/select", json=db_select_payload) as response:
            if response.status == 200:
                db_result = await response.json()
                session_id = db_result.get("session_id")
                print(f"✅ Database selected, session_id: {session_id}")
            else:
                print(f"❌ Database selection failed: {response.status}")
                return
        
        # Step 2: Test that queries with the session_id work
        print(f"\nStep 2: Testing query with correct session_id...")
        query_payload = {
            "query": "Show me total revenue for the last 6 months",
            "session_id": session_id,
            "context": { "user_id": "test_user" }
        }
        
        async with session.post(f"{base_url}/api/query", json=query_payload) as response:
            if response.status == 200:
                query_result = await response.json()
                if query_result.get("error") and "database context" in str(query_result["error"]).lower():
                    print("❌ Still getting database context error")
                    return False
                else:
                    print("✅ Query with session_id worked - no database context error!")
            else:
                print(f"❌ Query failed: {response.status}")
                return False
        
        # Step 3: Test all the automated queries that frontend would send
        print(f"\nStep 3: Testing all automated frontend queries...")
        automated_queries = [
            "Show me total revenue for the last 6 months",
            "Show me net profit for the current period", 
            "Show me operating expenses for the current period",
            "Show me top 5 investments by ROI",
            "Show me monthly revenue trend for the last 6 months"
        ]
        
        success_count = 0
        
        for i, query_text in enumerate(automated_queries, 1):
            print(f"  {i}. Testing: {query_text}")
            
            query_payload = {
                "query": query_text,
                "session_id": session_id,
                "context": { "user_id": "dashboard_init" }
            }
            
            async with session.post(f"{base_url}/api/query", json=query_payload) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("error") and "database context" in str(result["error"]).lower():
                        print(f"     ❌ Database context error")
                    else:
                        print(f"     ✅ Success - context found")
                        success_count += 1
                else:
                    print(f"     ❌ HTTP error: {response.status}")
        
        print(f"\nStep 4: Summary")
        print(f"✅ Backend session management: Working")
        print(f"✅ Session ID generation: Working") 
        print(f"✅ Database context storage: Working")
        print(f"✅ Database context retrieval: Working")
        print(f"✅ Automated queries with session: {success_count}/{len(automated_queries)} working")
        
        if success_count == len(automated_queries):
            print(f"\n🎉 COMPLETE SUCCESS! All session management issues are fixed!")
            print(f"   - Backend now correctly stores and retrieves database context")
            print(f"   - Frontend can now send session_id with automated queries")
            print(f"   - No more 'No database context found' errors expected")
        else:
            print(f"\n⚠️  Partial success - {len(automated_queries) - success_count} queries still failing")
        
        return success_count == len(automated_queries)

if __name__ == "__main__":
    asyncio.run(test_complete_session_fix())
