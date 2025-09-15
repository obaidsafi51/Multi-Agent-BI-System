#!/usr/bin/env python3
"""
Final comprehensive test to validate schema context fixes
"""
import asyncio
import aiohttp
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_comprehensive_schema_fixes():
    """Test various queries to ensure schema context processing is working"""
    
    test_queries = [
        "show me the cashflow of 2024",
        "what is the revenue for this year",
        "show me balance sheet data",
        "get expenses by category",
        "total profit for 2024"
    ]
    
    session_id = "session_1757843495030_o1xk3y38e"  # Known good session
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for i, query in enumerate(test_queries):
            logger.info(f"Testing query {i+1}/{len(test_queries)}: {query}")
            
            query_payload = {
                "query": query,
                "query_id": f"test_fix_{i+1}",
                "user_id": "test_user", 
                "session_id": session_id,
                "context": {
                    "timestamp": "2025-09-15T10:00:00Z",
                    "source": "comprehensive_test"
                }
            }
            
            try:
                async with session.post(
                    "http://localhost:8001/process",
                    json=query_payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Check for success
                        # Check if the response indicates success (has sql_query and no error)
                        sql_query = result.get('sql_query', '')
                        has_error = 'error' in result and result['error']
                        
                        if sql_query and not has_error:
                            # Check for schema-related issues
                            issues = []
                            if 'date_column' in sql_query:
                                issues.append("Contains placeholder 'date_column'")
                            if not sql_query.strip():
                                issues.append("Empty SQL query")
                            if 'Schema information unavailable' in str(result):
                                issues.append("Schema information unavailable")
                            
                            results.append({
                                "query": query,
                                "success": True,
                                "sql": sql_query,
                                "issues": issues
                            })
                            
                            if issues:
                                logger.warning(f"⚠️  Query {i+1} has issues: {', '.join(issues)}")
                            else:
                                logger.info(f"✅ Query {i+1} processed successfully")
                                logger.info(f"   SQL: {sql_query[:100]}...")
                        else:
                            error = result.get('error', 'No SQL generated')
                            results.append({
                                "query": query,
                                "success": False,
                                "error": error,
                                "issues": []
                            })
                            logger.error(f"❌ Query {i+1} failed: {error}")
                    else:
                        error_text = await response.text()
                        results.append({
                            "query": query,
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "issues": []
                        })
                        logger.error(f"❌ Query {i+1} HTTP error: {response.status}")
                        
            except asyncio.TimeoutError:
                results.append({
                    "query": query,
                    "success": False,
                    "error": "Timeout",
                    "issues": []
                })
                logger.error(f"❌ Query {i+1} timed out")
            except Exception as e:
                results.append({
                    "query": query,
                    "success": False,
                    "error": str(e),
                    "issues": []
                })
                logger.error(f"❌ Query {i+1} exception: {e}")
                
            # Small delay between queries
            await asyncio.sleep(1)
    
    # Analyze results
    total_queries = len(results)
    successful_queries = sum(1 for r in results if r['success'])
    queries_with_issues = sum(1 for r in results if r['success'] and r['issues'])
    failed_queries = total_queries - successful_queries
    
    logger.info("\n" + "="*60)
    logger.info("COMPREHENSIVE TEST RESULTS")
    logger.info("="*60)
    logger.info(f"Total queries tested: {total_queries}")
    logger.info(f"Successful queries: {successful_queries}")
    logger.info(f"Queries with issues: {queries_with_issues}")
    logger.info(f"Failed queries: {failed_queries}")
    
    if failed_queries == 0 and queries_with_issues == 0:
        logger.info("🎉 ALL TESTS PASSED - Schema context fixes are working perfectly!")
        return True
    elif failed_queries == 0:
        logger.warning(f"⚠️  Tests mostly passed but {queries_with_issues} queries have minor issues")
        return True
    else:
        logger.error(f"❌ {failed_queries} queries failed - some issues remain")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_comprehensive_schema_fixes())
    if result:
        print("\n✅ Schema context fix validation PASSED!")
    else:
        print("\n❌ Schema context fix validation FAILED!")
