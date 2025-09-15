#!/usr/bin/env python3
"""
Test script to verify that the MCP Data Agent and TiDB MCP Server fixes are working.
"""

import asyncio
import json
import aiohttp


async def test_query_execution():
    """Test executing a query with USE statement to verify fixes."""
    
    # Test data agent directly
    print("Testing Data Agent with USE statement query...")
    
    test_query = {
        "sql_query": "USE `Retail_Business_Agentic_AI`;\nSELECT SUM(`net_cashflow`) AS `total_cashflow_2025` FROM `cashflow` WHERE YEAR(`date`) = 2025;",
        "query_context": {
            "metric_type": "cashflow", 
            "time_period": "yearly",
            "aggregation_level": "yearly"
        },
        "query_id": "test_fix_query_001",
        "execution_config": {"use_cache": True}
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8002/execute",
                json=test_query,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                
                print(f"Response Status: {response.status}")
                print(f"Success: {result.get('success', False)}")
                
                if result.get('success'):
                    print(f"✅ Data Agent fix successful!")
                    print(f"   - Rows returned: {result.get('row_count', 0)}")
                    print(f"   - Processing time: {result.get('processing_time_ms', 0)}ms")
                    if result.get('processed_data'):
                        print(f"   - Sample data: {result['processed_data'][:1]}")
                else:
                    print(f"❌ Data Agent still has issues:")
                    print(f"   - Error: {result.get('error', 'Unknown error')}")
                    
    except Exception as e:
        print(f"❌ Failed to test data agent: {e}")
    
    print("\n" + "="*60 + "\n")
    
    # Test TiDB MCP Server directly
    print("Testing TiDB MCP Server with USE statement query...")
    
    test_mcp_query = {
        "query": "USE `Retail_Business_Agentic_AI`;\nSELECT COUNT(*) as table_count FROM `cashflow` LIMIT 5;",
        "timeout": 30,
        "use_cache": True
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/tools/execute_query_tool",
                json=test_mcp_query,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                
                print(f"Response Status: {response.status}")
                print(f"Success: {result.get('success', False)}")
                
                if result.get('success'):
                    print(f"✅ TiDB MCP Server fix successful!")
                    print(f"   - Rows returned: {result.get('row_count', 0)}")
                    print(f"   - Execution time: {result.get('execution_time_ms', 0)}ms")
                    if result.get('rows'):
                        print(f"   - Sample data: {result['rows'][:1]}")
                else:
                    print(f"❌ TiDB MCP Server still has issues:")
                    print(f"   - Error: {result.get('error', 'Unknown error')}")
                    
    except Exception as e:
        print(f"❌ Failed to test TiDB MCP server: {e}")


if __name__ == "__main__":
    asyncio.run(test_query_execution())
