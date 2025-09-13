"""
Test script for MCP Server-Driven Schema Intelligence.

This script tests the new MCP server-driven schema management capabilities.
"""

import asyncio
import logging
import sys
import os

# Add the parent directory to the Python path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_client import get_backend_mcp_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_mcp_schema_intelligence():
    """Test MCP server schema intelligence capabilities."""
    
    try:
        logger.info("Starting MCP Schema Intelligence Tests...")
        
        # Get MCP client
        mcp_client = get_backend_mcp_client()
        
        # Test 1: Discover business mappings
        logger.info("\n=== Test 1: Business Mappings Discovery ===")
        mappings_result = await mcp_client._send_request(
            "discover_business_mappings_tool",
            {
                "business_terms": ["revenue", "profit", "cash_flow"],
                "confidence_threshold": 0.5
            }
        )
        
        if mappings_result:
            logger.info(f"Business mappings result: {mappings_result}")
        else:
            logger.warning("No response from business mappings discovery")
        
        # Test 2: Analyze query intent
        logger.info("\n=== Test 2: Query Intent Analysis ===")
        intent_result = await mcp_client._send_request(
            "analyze_query_intent_tool",
            {
                "natural_language_query": "Show me monthly revenue for this year",
                "context": {"user_id": "test_user"}
            }
        )
        
        if intent_result:
            logger.info(f"Query intent result: {intent_result}")
        else:
            logger.warning("No response from query intent analysis")
        
        # Test 3: Schema optimizations
        logger.info("\n=== Test 3: Schema Optimizations ===")
        optimization_result = await mcp_client._send_request(
            "suggest_schema_optimizations_tool",
            {
                "database": "Agentic_BI",
                "performance_threshold": 0.5
            }
        )
        
        if optimization_result:
            logger.info(f"Schema optimization result: {optimization_result}")
        else:
            logger.warning("No response from schema optimization analysis")
        
        # Test 4: Learn from successful mapping
        logger.info("\n=== Test 4: Learn from Successful Mapping ===")
        learning_result = await mcp_client._send_request(
            "learn_from_successful_mapping_tool",
            {
                "business_term": "revenue",
                "database_name": "Agentic_BI",
                "table_name": "financial_overview",
                "column_name": "revenue",
                "success_score": 0.9
            }
        )
        
        if learning_result:
            logger.info(f"Learning result: {learning_result}")
        else:
            logger.warning("No response from learning")
        
        # Test 5: Get statistics
        logger.info("\n=== Test 5: Schema Intelligence Statistics ===")
        stats_result = await mcp_client._send_request(
            "get_schema_intelligence_stats_tool",
            {}
        )
        
        if stats_result:
            logger.info(f"Statistics result: {stats_result}")
        else:
            logger.warning("No response from statistics")
        
        logger.info("\n=== MCP Schema Intelligence Tests Completed ===")
        
        # Summary
        results = {
            "business_mappings": bool(mappings_result and mappings_result.get("success")),
            "query_intent": bool(intent_result and intent_result.get("success")),
            "optimizations": bool(optimization_result and optimization_result.get("success")),
            "learning": bool(learning_result and learning_result.get("success")),
            "statistics": bool(stats_result and stats_result.get("success"))
        }
        
        logger.info(f"\nTest Results Summary: {results}")
        
        success_count = sum(results.values())
        total_tests = len(results)
        
        logger.info(f"Tests Passed: {success_count}/{total_tests}")
        
        if success_count == total_tests:
            logger.info("✅ All MCP schema intelligence tests passed!")
            return True
        else:
            logger.warning(f"⚠️ {total_tests - success_count} tests failed")
            return False
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return False


async def test_backend_endpoints():
    """Test backend API endpoints that use MCP server intelligence."""
    
    try:
        import aiohttp
        
        logger.info("\n=== Testing Backend API Endpoints ===")
        
        # Test endpoints (assuming backend is running on localhost:8000)
        base_url = "http://localhost:8000"
        
        endpoints_to_test = [
            "/api/schema/discovery",
            "/api/schema/mappings/revenue",
            "/api/schema/intelligence-stats"
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints_to_test:
                try:
                    logger.info(f"Testing endpoint: {endpoint}")
                    async with session.get(f"{base_url}{endpoint}") as response:
                        if response.status == 200:
                            data = await response.json()
                            logger.info(f"✅ {endpoint} - Success: {data.get('success', False)}")
                        else:
                            logger.warning(f"❌ {endpoint} - Status: {response.status}")
                except Exception as e:
                    logger.warning(f"❌ {endpoint} - Error: {e}")
        
        logger.info("Backend endpoint testing completed")
        
    except ImportError:
        logger.warning("aiohttp not available for backend endpoint testing")
    except Exception as e:
        logger.error(f"Backend endpoint testing failed: {e}")


if __name__ == "__main__":
    async def main():
        """Main test runner."""
        logger.info("🚀 Starting MCP Server-Driven Schema Intelligence Tests")
        
        # Test MCP server capabilities
        mcp_success = await test_mcp_schema_intelligence()
        
        # Test backend integration (optional)
        await test_backend_endpoints()
        
        if mcp_success:
            logger.info("🎉 MCP Schema Intelligence is working correctly!")
            sys.exit(0)
        else:
            logger.error("💥 MCP Schema Intelligence tests failed!")
            sys.exit(1)
    
    # Run the tests
    asyncio.run(main())
