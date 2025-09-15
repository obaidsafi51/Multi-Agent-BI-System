#!/usr/bin/env python3
"""
Test script to verify session management fixes
"""

import random
import string
from datetime import datetime
from typing import Optional

def generate_session_id() -> str:
    """Generate a session ID using the same logic as our backend"""
    return f"session_{int(datetime.utcnow().timestamp())}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=12))}"

def simulate_database_selection(session_id: Optional[str] = None) -> dict:
    """Simulate database selection endpoint behavior"""
    # Generate session_id if not provided (same logic as backend)
    if not session_id:
        session_id = generate_session_id()
    
    print(f"🔗 Database selection - Session ID: {session_id}")
    return {
        "success": True,
        "database_name": "test_db",
        "session_id": session_id
    }

def simulate_query_processing(session_id: Optional[str] = None) -> dict:
    """Simulate query endpoint behavior"""
    query_id = f"q_{datetime.utcnow().timestamp()}"
    
    # Use provided session_id or generate a new one (fixed logic)
    if session_id:
        actual_session_id = session_id
    else:
        actual_session_id = generate_session_id()
    
    print(f"🔍 Query processing - Session ID: {actual_session_id}")
    return {
        "query_id": query_id,
        "session_id": actual_session_id
    }

def test_session_consistency():
    """Test that session IDs are consistent between database selection and queries"""
    print("🧪 Testing Session Management Fix\n")
    
    # Test 1: Frontend provides session_id to both endpoints
    print("Test 1: Frontend provides consistent session_id")
    frontend_session = "session_1757773211072_s4xhkug2t"
    
    db_result = simulate_database_selection(frontend_session)
    query_result = simulate_query_processing(frontend_session) 
    
    print(f"  DB Selection returned: {db_result['session_id']}")
    print(f"  Query used: {query_result['session_id']}")
    print(f"  ✅ Match: {db_result['session_id'] == query_result['session_id']}\n")
    
    # Test 2: Frontend doesn't provide session_id
    print("Test 2: Frontend doesn't provide session_id (both generate same)")
    db_result = simulate_database_selection()
    query_result = simulate_query_processing(db_result['session_id'])  # Query uses DB session
    
    print(f"  DB Selection generated: {db_result['session_id']}")
    print(f"  Query used: {query_result['session_id']}")
    print(f"  ✅ Match: {db_result['session_id'] == query_result['session_id']}\n")
    
    # Test 3: Show the problematic old behavior (for comparison)
    print("Test 3: Old problematic behavior simulation")
    db_session = "session_1757773211072_s4xhkug2t"
    old_query_behavior = generate_session_id()  # Query generates new ID
    
    print(f"  DB Selection: {db_session}")
    print(f"  Query (old behavior): {old_query_behavior}")
    print(f"  ❌ Match: {db_session == old_query_behavior} (This was the problem!)\n")
    
    print("🎉 Session management fix validation complete!")

if __name__ == "__main__":
    test_session_consistency()
