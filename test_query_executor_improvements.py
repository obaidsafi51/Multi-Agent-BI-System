#!/usr/bin/env python3
"""
Test the improved query executor with USE statement handling.
This test validates that the MCP server can now handle USE statements properly.
"""

import asyncio
import json
import requests
import sys
from typing import Dict, Any

# Test queries that should now work with the improved validator
TEST_QUERIES = [
    # Simple USE statement
    "USE user_finance_db;",
    
    # USE followed by SELECT
    "USE user_finance_db; SELECT * FROM cashflow LIMIT 5;",
    
    # USE followed by SHOW
    "USE user_finance_db; SHOW TABLES;",
    
    # Standard SELECT without USE
    "SELECT * FROM user_finance_db.cashflow LIMIT 3;",
    
    # SHOW tables (schema discovery)
    "SHOW TABLES FROM user_finance_db;",
    
    # DESCRIBE table (schema discovery)
    "DESCRIBE user_finance_db.cashflow;",
]

# Queries that should still be rejected
INVALID_QUERIES = [
    # DML operations
    "INSERT INTO user_finance_db.cashflow VALUES (1, 'test');",
    "UPDATE user_finance_db.cashflow SET amount = 100;",
    "DELETE FROM user_finance_db.cashflow;",
    
    # DDL operations
    "DROP TABLE user_finance_db.cashflow;",
    "CREATE TABLE test (id INT);",
    
    # Multiple unsafe statements
    "USE user_finance_db; DROP TABLE cashflow;",
]

def test_mcp_server_direct():
    """Test the MCP server directly via HTTP."""
    mcp_url = "http://localhost:8000"
    
    print("🧪 Testing MCP Server Query Executor Improvements")
    print("=" * 60)
    
    # Test valid queries
    print("\n✅ Testing VALID queries (should succeed):")
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n{i}. Testing: {query}")
        try:
            # Test query validation endpoint
            response = requests.post(
                f"{mcp_url}/tools/validate_query_tool",
                json={"query": query},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("valid"):
                    print(f"   ✅ Validation: PASSED")
                else:
                    print(f"   ❌ Validation: FAILED - {result.get('message', 'Unknown error')}")
                    continue
            else:
                print(f"   ❌ Validation request failed: {response.status_code}")
                continue
            
            # Test actual query execution
            response = requests.post(
                f"{mcp_url}/tools/execute_query_tool",
                json={"query": query},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if "error" not in result:
                    print(f"   ✅ Execution: SUCCESS - {result.get('row_count', 0)} rows")
                else:
                    print(f"   ⚠️  Execution: ERROR - {result['error']}")
            else:
                print(f"   ❌ Execution request failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {str(e)}")
    
    # Test invalid queries
    print("\n❌ Testing INVALID queries (should be rejected):")
    for i, query in enumerate(INVALID_QUERIES, 1):
        print(f"\n{i}. Testing: {query}")
        try:
            response = requests.post(
                f"{mcp_url}/tools/validate_query_tool",
                json={"query": query},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if not result.get("valid"):
                    print(f"   ✅ Correctly REJECTED: {result.get('message', 'Unknown error')}")
                else:
                    print(f"   ❌ Incorrectly ACCEPTED (should be rejected)")
            else:
                print(f"   ❌ Validation request failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {str(e)}")

def test_backend_integration():
    """Test the backend integration with the improved MCP server."""
    backend_url = "http://localhost:8080"
    
    print("\n\n🔗 Testing Backend Integration")
    print("=" * 60)
    
    # Test cashflow query that previously failed
    test_query = "Show me the total income and expenses by category for the last 6 months"
    
    print(f"\nTesting natural language query: {test_query}")
    
    try:
        response = requests.post(
            f"{backend_url}/process_query",
            json={
                "query": test_query,
                "session_id": "test_session_improvements"
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Backend query processing: SUCCESS")
            
            if "data" in result:
                print(f"   📊 Data rows: {len(result.get('data', []))}")
            if "visualization" in result:
                print(f"   📈 Visualization: {result['visualization'].get('type', 'unknown')}")
            if "sql_query" in result:
                print(f"   🔍 Generated SQL: {result['sql_query'][:100]}...")
                
        else:
            print(f"❌ Backend query failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Backend request failed: {str(e)}")

def main():
    """Run all tests."""
    print("🚀 Starting Query Executor Improvement Tests")
    print(f"Time: {asyncio.get_event_loop().time()}")
    
    # Test MCP server directly
    test_mcp_server_direct()
    
    # Test backend integration
    test_backend_integration()
    
    print("\n" + "=" * 60)
    print("🏁 Test completed!")

if __name__ == "__main__":
    main()
