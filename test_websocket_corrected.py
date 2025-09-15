#!/usr/bin/env python3
"""
Test WebSocket communication vs HTTP with the corrected query structure.
"""

import requests
import json

# Test the corrected query structure
def test_corrected_query():
    backend_url = "http://localhost:8080"
    
    # Test with corrected table and column names
    test_query = "Show me the total revenue by month using the revenue table"
    
    print("🧪 Testing Backend WebSocket Communication with Corrected Query")
    print("=" * 70)
    print(f"Query: {test_query}")
    
    try:
        response = requests.post(
            f"{backend_url}/api/query",
            json={
                "query": test_query,
                "session_id": "test_websocket_fix_session"
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Backend processing: SUCCESS")
            
            if "error" in result:
                print(f"❌ Error: {result['error']}")
            else:
                if "data" in result:
                    print(f"   📊 Data rows: {len(result.get('data', []))}")
                    if result.get('data'):
                        print(f"   📋 Sample data: {json.dumps(result['data'][0], indent=4)}")
                if "sql_query" in result:
                    print(f"   🔍 Generated SQL: {result['sql_query']}")
                if "visualization" in result:
                    print(f"   📈 Visualization: {result['visualization'].get('type', 'unknown')}")
                
        else:
            print(f"❌ Backend request failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")

def test_direct_mcp_with_correct_query():
    """Test the MCP server directly with the correct table structure."""
    mcp_url = "http://localhost:8000"
    
    # Use the correct table and column names
    correct_query = """USE `Retail_Business_Agentic_AI`; 
SELECT DATE_FORMAT(`date`, '%Y-%m') AS `month`, SUM(`total_revenue`) AS `total_revenue` 
FROM `revenue` 
GROUP BY DATE_FORMAT(`date`, '%Y-%m') 
ORDER BY `month` 
LIMIT 5;"""
    
    print(f"\n🔍 Testing MCP Server Directly with Correct Query")
    print("=" * 70)
    
    try:
        response = requests.post(
            f"{mcp_url}/tools/execute_query_tool",
            json={"query": correct_query},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if "error" not in result or not result.get("error"):
                row_count = result.get("row_count", 0)
                exec_time = result.get("execution_time_ms", 0)
                print(f"✅ MCP Execution: SUCCESS - {row_count} rows in {exec_time:.1f}ms")
                
                if row_count > 0:
                    rows = result.get("rows", [])
                    print(f"📋 Sample results:")
                    for i, row in enumerate(rows[:3]):  # Show first 3 rows
                        print(f"   {i+1}. {json.dumps(row)}")
            else:
                print(f"❌ MCP Error: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ MCP request failed: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ MCP request failed: {str(e)}")

if __name__ == "__main__":
    test_direct_mcp_with_correct_query()
    test_corrected_query()
