#!/usr/bin/env python3
"""
Test the session management fix with real HTTP requests to the backend
"""

import asyncio
import aiohttp
import json

async def test_session_flow():
    """Test the complete session flow with the backend"""
    
    base_url = "http://localhost:8080"
    
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing Session Management with Real Backend\n")
        
        # Step 1: Select a database
        print("Step 1: Selecting database...")
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
        
        # Step 2: Send a query WITH the session_id
        print(f"\nStep 2: Sending query with session_id: {session_id}")
        query_payload = {
            "query": "Show me total revenue for the last 6 months",
            "session_id": session_id  # Include the session_id from database selection
        }
        
        async with session.post(f"{base_url}/api/query", json=query_payload) as response:
            if response.status == 200:
                query_result = await response.json()
                print("✅ Query sent successfully")
                # Check if there was a database context error
                if query_result.get("error") and "database context" in str(query_result["error"]).lower():
                    print("❌ Still getting database context error")
                else:
                    print("✅ No database context error - session management working!")
            else:
                print(f"❌ Query failed: {response.status}")
        
        # Step 3: Send a query WITHOUT session_id (should fail with database context error)
        print(f"\nStep 3: Sending query WITHOUT session_id (expected to fail)")
        query_payload_no_session = {
            "query": "Show me net profit for the current period"
            # No session_id - this should fail
        }
        
        async with session.post(f"{base_url}/api/query", json=query_payload_no_session) as response:
            if response.status == 200:
                query_result = await response.json()
                if query_result.get("error") and "database context" in str(query_result["error"]).lower():
                    print("✅ Correctly failed with database context error (as expected)")
                else:
                    print("❌ Query succeeded when it should have failed")

if __name__ == "__main__":
    asyncio.run(test_session_flow())
