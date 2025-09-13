#!/usr/bin/env python3
"""
Simple test script for MCP server tools.
Tests the MCP server endpoints directly via HTTP.
"""

import asyncio
import aiohttp
import json
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_mcp_server_tools():
    """Test MCP server tools via HTTP endpoints."""
    
    # MCP server URL (adjust if needed)
    mcp_server_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Health check
        logger.info("=== Test 1: Health Check ===")
        try:
            async with session.get(f"{mcp_server_url}/health") as response:
                if response.status == 200:
                    logger.info("✅ MCP server is healthy")
                else:
                    logger.warning(f"⚠️ MCP server health check failed: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to MCP server: {e}")
            return False
        
        # Test 2: Discover databases
        logger.info("\n=== Test 2: Discover Databases ===")
        try:
            async with session.post(
                f"{mcp_server_url}/tools/discover_databases_tool",
                json={},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Discovered databases: {len(result) if isinstance(result, list) else 'unknown'}")
                    if isinstance(result, list) and result:
                        for db in result[:3]:  # Show first 3
                            logger.info(f"  - {db.get('name', 'Unknown')} ({'accessible' if db.get('accessible') else 'not accessible'})")
                else:
                    error_text = await response.text()
                    logger.warning(f"⚠️ Database discovery failed: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"❌ Database discovery error: {e}")
        
        # Test 3: Execute a simple query
        logger.info("\n=== Test 3: Execute Query ===")
        try:
            test_query = "SELECT DATABASE() as current_db, VERSION() as version LIMIT 1"
            async with session.post(
                f"{mcp_server_url}/tools/execute_query_tool",
                json={
                    "query": test_query,
                    "timeout": 10,
                    "use_cache": True
                },
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('success'):
                        logger.info(f"✅ Query executed successfully: {result.get('row_count', 0)} rows")
                        if result.get('rows'):
                            logger.info(f"  - Sample result: {result['rows'][0] if result['rows'] else 'No data'}")
                    else:
                        logger.warning(f"⚠️ Query execution failed: {result.get('error', 'Unknown error')}")
                else:
                    error_text = await response.text()
                    logger.warning(f"⚠️ Query execution failed: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"❌ Query execution error: {e}")
        
        # Test 4: Schema Intelligence - Business Mappings
        logger.info("\n=== Test 4: Schema Intelligence - Business Mappings ===")
        try:
            async with session.post(
                f"{mcp_server_url}/tools/discover_business_mappings_tool",
                json={
                    "business_terms": ["revenue", "profit"],
                    "confidence_threshold": 0.5
                },
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Business mappings discovered: {result.get('total_mappings', 0)} mappings")
                    if result.get('mappings'):
                        for mapping in result['mappings'][:2]:  # Show first 2
                            logger.info(f"  - {mapping.get('business_term')} -> {mapping.get('database_name', 'N/A')}.{mapping.get('table_name', 'N/A')}")
                else:
                    error_text = await response.text()
                    logger.warning(f"⚠️ Business mappings discovery failed: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"❌ Business mappings discovery error: {e}")
        
        # Test 5: Schema Intelligence - Query Intent
        logger.info("\n=== Test 5: Schema Intelligence - Query Intent ===")
        try:
            async with session.post(
                f"{mcp_server_url}/tools/analyze_query_intent_tool",
                json={
                    "natural_language_query": "Show me monthly revenue for this year",
                    "context": {"user_id": "test_user"}
                },
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Query intent analyzed: {result.get('intent_type', 'Unknown')} (confidence: {result.get('confidence_score', 0):.2f})")
                    if result.get('suggested_mappings'):
                        logger.info(f"  - Suggested {len(result['suggested_mappings'])} mappings")
                else:
                    error_text = await response.text()
                    logger.warning(f"⚠️ Query intent analysis failed: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"❌ Query intent analysis error: {e}")
        
        # Test 6: Server Statistics
        logger.info("\n=== Test 6: Server Statistics ===")
        try:
            async with session.post(
                f"{mcp_server_url}/tools/get_server_stats_tool",
                json={},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Server stats retrieved: {result.get('server_status', 'Unknown status')}")
                    if result.get('cache'):
                        logger.info(f"  - Cache hits: {result['cache'].get('hits', 0)}")
                else:
                    error_text = await response.text()
                    logger.warning(f"⚠️ Server stats failed: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"❌ Server stats error: {e}")
    
    logger.info("\n🎉 MCP server tool testing completed!")
    return True


async def test_backend_endpoints():
    """Test backend API endpoints that use MCP server."""
    
    backend_url = "http://localhost:8000"  # Adjust port if needed
    
    async with aiohttp.ClientSession() as session:
        
        logger.info("\n=== Testing Backend API Endpoints ===")
        
        # Test backend endpoints
        endpoints = [
            "/api/schema/discovery",
            "/api/schema/mappings/revenue",
            "/api/schema/intelligence-stats"
        ]
        
        for endpoint in endpoints:
            try:
                logger.info(f"Testing endpoint: {endpoint}")
                async with session.get(f"{backend_url}{endpoint}") as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ {endpoint} - Status: {response.status}")
                    else:
                        logger.warning(f"❌ {endpoint} - Status: {response.status}")
            except Exception as e:
                logger.warning(f"❌ {endpoint} - Error: {e}")
        
        logger.info("Backend endpoint testing completed")


async def main():
    """Main test function."""
    
    logger.info("🚀 Starting MCP Server and Schema Intelligence Tests")
    
    # Test MCP server tools directly
    await test_mcp_server_tools()
    
    # Test backend endpoints (if backend is running)
    try:
        await test_backend_endpoints()
    except Exception as e:
        logger.info(f"Backend endpoint testing skipped: {e}")
    
    logger.info("✅ All tests completed!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)
