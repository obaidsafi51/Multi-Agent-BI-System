#!/usr/bin/env python3
"""
Direct test of MCP server HTTP API to verify it works correctly.
"""

import asyncio
import json
import sys
import httpx

async def test_mcp_direct():
    """Test MCP server directly via HTTP"""
    
    print("Testing MCP server HTTP API...")
    
    # Test data
    test_query = "Show me total revenue for Q1 2024"
    mcp_url = "http://localhost:8000/tools/llm_generate_sql_tool"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"Sending query: {test_query}")
            
            response = await client.post(
                mcp_url,
                json={"natural_language_query": test_query},
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Response keys: {list(result.keys())}")
                
                if "generated_text" in result:
                    print(f"Generated SQL: {result['generated_text']}")
                    
                    # Extract SQL from markdown code block
                    import re
                    sql_match = re.search(r'```sql\s*(.*?)\s*```', result['generated_text'], re.DOTALL | re.IGNORECASE)
                    if sql_match:
                        clean_sql = sql_match.group(1).strip()
                        # Remove comments
                        lines = clean_sql.split('\n')
                        sql_lines = [line for line in lines if line.strip() and not line.strip().startswith('--')]
                        final_sql = '\n'.join(sql_lines).strip()
                        print(f"Extracted SQL: {final_sql}")
                        return final_sql
                    else:
                        print("No SQL code block found")
                        return ""
                else:
                    print("No generated_text in response")
                    return ""
            else:
                print(f"HTTP Error: {response.status_code}")
                print(f"Response: {response.text}")
                return ""
                
    except Exception as e:
        print(f"Error testing MCP: {e}")
        return ""

if __name__ == "__main__":
    result = asyncio.run(test_mcp_direct())
    if result:
        print(f"SUCCESS: Got SQL query: {result}")
        sys.exit(0)
    else:
        print("FAILED: No SQL query generated")
        sys.exit(1)
