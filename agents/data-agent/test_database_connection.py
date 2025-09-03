#!/usr/bin/env python3
"""
Test database connection to TiDB using PyMySQL directly and via the data agent.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/home/obaidsafi31/Desktop/Agentic BI /.env")

def test_pymysql_direct():
    """Test direct PyMySQL connection."""
    print("Testing direct PyMySQL connection...")
    
    try:
        import pymysql
        
        # Parse database URL
        import urllib.parse
        url = os.getenv('DATABASE_URL')
        parsed = urllib.parse.urlparse(url)
        
        connection = pymysql.connect(
            host=parsed.hostname,
            port=parsed.port,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:],  # Remove leading '/'
            charset='utf8mb4',
            ssl_disabled=False,
            connect_timeout=10
        )
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            
        connection.close()
        
        print(f"✓ Direct PyMySQL connection successful: {result}")
        return True
        
    except Exception as e:
        print(f"✗ Direct PyMySQL connection failed: {e}")
        return False

async def test_data_agent_connection():
    """Test connection via data agent."""
    print("Testing Data Agent connection...")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        from database.connection import get_connection_manager
        
        # Get connection manager
        conn_manager = await get_connection_manager()
        
        # Test basic query
        result = await conn_manager.execute_query("SELECT 1 as test", fetch_all=True)
        
        print(f"✓ Data Agent connection successful: {result}")
        
        # Test health check
        health = await conn_manager.health_check()
        print(f"✓ Health check status: {health['status']}")
        
        # Close connection
        await conn_manager.close()
        
        return True
        
    except Exception as e:
        print(f"✗ Data Agent connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_database_schema():
    """Test database schema by checking available tables."""
    print("Testing database schema...")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        from database.connection import get_connection_manager
        
        conn_manager = await get_connection_manager()
        
        # Check available tables
        result = await conn_manager.execute_query("SHOW TABLES", fetch_all=True)
        
        print(f"Available tables:")
        for row in result['data']:
            table_name = row[list(row.keys())[0]]  # Get the table name from the first column
            print(f"  - {table_name}")
        
        # If we have tables, check one of them
        if result['data']:
            first_table = result['data'][0][list(result['data'][0].keys())[0]]
            desc_result = await conn_manager.execute_query(f"DESCRIBE {first_table}", fetch_all=True)
            
            print(f"\nStructure of {first_table}:")
            for row in desc_result['data']:
                print(f"  {row['Field']}: {row['Type']}")
        
        await conn_manager.close()
        
        return True
        
    except Exception as e:
        print(f"✗ Database schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all database tests."""
    print("Testing Data Agent Database Connection")
    print("=" * 50)
    
    tests = [
        ("Direct PyMySQL", test_pymysql_direct),
        ("Data Agent Connection", test_data_agent_connection),
        ("Database Schema", test_database_schema),
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
            print(f"✗ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"Database Tests Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All database tests passed!")
        return 0
    else:
        print("❌ Some database tests failed.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
