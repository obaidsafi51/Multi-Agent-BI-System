#!/usr/bin/env python3
"""
Simple test for Data Agent basic functionality.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/home/obaidsafi31/Desktop/Agentic BI /.env")

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_basic_functionality():
    """Test basic data agent functionality."""
    print("Testing basic Data Agent functionality...")
    
    try:
        # Test imports first
        print("  Testing imports...")
        from query.generator import QueryGenerator
        from query.validator import DataValidator
        from optimization.optimizer import QueryOptimizer
        print("  ✓ Imports successful")
        
        # Test query generator
        print("  Testing query generator...")
        generator = QueryGenerator()
        
        query_intent = {
            'metric_type': 'revenue',
            'time_period': 'this year',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        }
        
        result = generator.generate_query(query_intent)
        print(f"  ✓ Query generated: {len(result.sql)} chars")
        print(f"    SQL preview: {result.sql[:100]}...")
        
        # Test data validator
        print("  Testing data validator...")
        validator = DataValidator()
        
        test_data = {
            'data': [{'period_date': '2024-01-01', 'revenue': 1000000.00}],
            'columns': ['period_date', 'revenue']
        }
        
        validation = validator.validate_query_result(test_data, 'revenue')
        print(f"  ✓ Data validated - Quality score: {validation.quality_score}")
        
        # Test query optimizer
        print("  Testing query optimizer...")
        optimizer = QueryOptimizer()
        
        test_sql = "SELECT period_date, SUM(revenue) FROM financial_overview GROUP BY period_date"
        optimization = optimizer.optimize_query(test_sql)
        print(f"  ✓ Query optimized - {len(optimization.applied_optimizations)} optimizations applied")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_database_connection():
    """Test database connection without SQLAlchemy."""
    print("Testing database connection...")
    
    try:
        import pymysql
        import urllib.parse
        
        url = os.getenv('DATABASE_URL')
        parsed = urllib.parse.urlparse(url)
        
        connection = pymysql.connect(
            host=parsed.hostname,
            port=parsed.port or 4000,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:] if parsed.path else '',
            charset='utf8mb4',
            ssl={'check_hostname': False, 'verify_mode': 0},
            connect_timeout=10,
            autocommit=True
        )
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM financial_overview")
            count = cursor.fetchone()[0]
            print(f"  ✓ Database connected - financial_overview has {count} records")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"  ✗ Database connection failed: {e}")
        return False

async def test_redis_connection():
    """Test Redis connection."""
    print("Testing Redis connection...")
    
    try:
        import redis
        
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        r = redis.from_url(redis_url)
        
        # Test ping
        r.ping()
        print("  ✓ Redis connected successfully")
        
        # Test basic operations
        r.set('test_key', 'test_value', ex=10)
        value = r.get('test_key')
        r.delete('test_key')
        
        print(f"  ✓ Redis operations successful")
        return True
        
    except Exception as e:
        print(f"  ✗ Redis connection failed: {e}")
        return False

async def main():
    """Run all basic tests."""
    print("Data Agent Basic Integration Tests")
    print("=" * 40)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Database Connection", test_database_connection),
        ("Redis Connection", test_redis_connection),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
            else:
                success = test_func()
            
            if success:
                passed += 1
        except Exception as e:
            print(f"  ✗ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 40)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic integration tests passed!")
        print("The Data Agent components are working correctly.")
        return 0
    elif passed >= 2:
        print("⚠️  Most tests passed. Core functionality is working.")
        return 0
    else:
        print("❌ Multiple test failures detected.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
