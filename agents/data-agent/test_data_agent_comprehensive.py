#!/usr/bin/env python3
"""
Comprehensive test for Data Agent functionality with real database connection.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/home/obaidsafi31/Desktop/Agentic BI /.env")

async def test_data_agent_initialization():
    """Test Data Agent initialization with real database."""
    print("Testing Data Agent initialization...")
    
    try:
        # Add src to Python path for imports
        src_path = os.path.join(os.path.dirname(__file__), 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        # Import with proper module path
        import agent
        
        # Initialize data agent
        data_agent = await agent.get_data_agent()
        
        print("✓ Data Agent initialized successfully")
        return data_agent
        
    except Exception as e:
        print(f"✗ Data Agent initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_data_agent_health_check(data_agent):
    """Test Data Agent health check."""
    print("Testing Data Agent health check...")
    
    try:
        health_status = await data_agent.health_check()
        
        print(f"✓ Health check completed")
        print(f"  Status: {health_status['status']}")
        print(f"  Components: {list(health_status['components'].keys())}")
        
        # Check each component
        for component, status in health_status['components'].items():
            comp_status = status.get('status', 'unknown')
            print(f"    {component}: {comp_status}")
        
        return health_status['status'] in ['healthy', 'degraded']
        
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_database_summary(data_agent):
    """Test getting database table summaries."""
    print("Testing database table summaries...")
    
    try:
        # Test summary for financial_overview table
        summary = await data_agent.get_data_summary('financial_overview')
        
        print(f"✓ Table summary retrieved")
        print(f"  Table: {summary['table_name']}")
        
        if summary['summary']:
            print(f"  Total records: {summary['summary'].get('total_records', 'N/A')}")
            print(f"  Date range: {summary['summary'].get('earliest_date', 'N/A')} to {summary['summary'].get('latest_date', 'N/A')}")
            print(f"  Unique periods: {summary['summary'].get('unique_periods', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"✗ Database summary failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_query_processing(data_agent):
    """Test Data Agent query processing."""
    print("Testing Data Agent query processing...")
    
    try:
        # Test a simple revenue query
        query_intent = {
            'metric_type': 'revenue',
            'time_period': 'this year',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        }
        
        print(f"  Processing query: {query_intent['metric_type']} for {query_intent['time_period']}")
        
        result = await data_agent.process_query(query_intent)
        
        print(f"✓ Query processed successfully")
        print(f"  Success: {result['success']}")
        print(f"  Row count: {result.get('row_count', 0)}")
        print(f"  Processing time: {result['metadata']['processing_time_ms']}ms")
        print(f"  Data quality score: {result['metadata']['data_quality']['quality_score']}")
        print(f"  Cache hit: {result['metadata']['cache_hit']}")
        
        if result['data']:
            print(f"  Sample data: {result['data'][:2]}")  # Show first 2 rows
        
        return result['success']
        
    except Exception as e:
        print(f"✗ Query processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_metrics_collection(data_agent):
    """Test Data Agent metrics collection."""
    print("Testing Data Agent metrics...")
    
    try:
        metrics = await data_agent.get_metrics()
        
        print(f"✓ Metrics collected")
        print(f"  Queries processed: {metrics.get('queries_processed', 0)}")
        print(f"  Cache hits: {metrics.get('cache_hits', 0)}")
        print(f"  Cache misses: {metrics.get('cache_misses', 0)}")
        print(f"  Average query time: {metrics.get('avg_query_time', 0):.2f}s")
        print(f"  Errors: {metrics.get('errors', 0)}")
        
        if 'cache' in metrics:
            print(f"  Cache hit rate: {metrics['cache'].get('hit_rate', 0):.1f}%")
        
        return True
        
    except Exception as e:
        print(f"✗ Metrics collection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_multiple_queries(data_agent):
    """Test multiple different query types."""
    print("Testing multiple query types...")
    
    test_queries = [
        {
            'metric_type': 'budget',
            'time_period': 'Q1 2024',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        },
        {
            'metric_type': 'cash_flow',
            'time_period': 'this month',
            'aggregation_level': 'daily',
            'filters': {},
            'comparison_periods': []
        }
    ]
    
    successful_queries = 0
    
    for i, query_intent in enumerate(test_queries):
        try:
            print(f"  Query {i+1}: {query_intent['metric_type']}")
            
            result = await data_agent.process_query(query_intent)
            
            if result['success']:
                successful_queries += 1
                print(f"    ✓ Success - {result.get('row_count', 0)} rows")
            else:
                print(f"    ✗ Failed - {result.get('error', {}).get('message', 'Unknown error')}")
        
        except Exception as e:
            print(f"    ✗ Exception - {e}")
    
    print(f"✓ Multiple queries test: {successful_queries}/{len(test_queries)} successful")
    return successful_queries > 0

async def cleanup_data_agent():
    """Cleanup data agent resources."""
    print("Cleaning up Data Agent...")
    
    try:
        # Add src to Python path for imports
        import sys
        import os
        src_path = os.path.join(os.path.dirname(__file__), 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        import agent
        await agent.close_data_agent()
        print("✓ Data Agent cleanup completed")
        
    except Exception as e:
        print(f"✗ Cleanup failed: {e}")

async def main():
    """Run comprehensive Data Agent tests."""
    print("Data Agent Comprehensive Testing")
    print("=" * 50)
    
    data_agent = None
    test_results = []
    
    try:
        # Test 1: Initialization
        data_agent = await test_data_agent_initialization()
        test_results.append(("Initialization", data_agent is not None))
        
        if not data_agent:
            print("❌ Cannot continue without initialized Data Agent")
            return 1
        
        print()
        
        # Test 2: Health Check
        health_ok = await test_data_agent_health_check(data_agent)
        test_results.append(("Health Check", health_ok))
        print()
        
        # Test 3: Database Summary
        summary_ok = await test_database_summary(data_agent)
        test_results.append(("Database Summary", summary_ok))
        print()
        
        # Test 4: Query Processing
        query_ok = await test_query_processing(data_agent)
        test_results.append(("Query Processing", query_ok))
        print()
        
        # Test 5: Metrics Collection
        metrics_ok = await test_metrics_collection(data_agent)
        test_results.append(("Metrics Collection", metrics_ok))
        print()
        
        # Test 6: Multiple Queries
        multi_query_ok = await test_multiple_queries(data_agent)
        test_results.append(("Multiple Queries", multi_query_ok))
        print()
        
    finally:
        # Always cleanup
        if data_agent:
            await cleanup_data_agent()
    
    # Summary
    print("=" * 50)
    print("Test Results Summary:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Data Agent tests passed! The data agent is working correctly.")
        return 0
    elif passed >= total * 0.7:  # 70% pass rate
        print("⚠️  Most tests passed. Data agent is functional with some issues.")
        return 0
    else:
        print("❌ Multiple test failures. Data agent needs investigation.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
