#!/usr/bin/env python3
"""
Test TiDB connection with proper SSL configuration using PyMySQL directly.
"""

import os
import urllib.parse
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/home/obaidsafi31/Desktop/Agentic BI /.env")

def test_tidb_connection():
    """Test TiDB connection with proper SSL configuration."""
    print("Testing TiDB connection with SSL...")
    
    try:
        # Parse database URL
        url = os.getenv('DATABASE_URL')
        print(f"Database URL: {url}")
        
        parsed = urllib.parse.urlparse(url)
        
        # TiDB Cloud requires SSL
        connection = pymysql.connect(
            host=parsed.hostname,
            port=parsed.port or 4000,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:] if parsed.path else '',
            charset='utf8mb4',
            ssl={'check_hostname': False, 'verify_mode': 0},  # For TiDB Cloud
            connect_timeout=10,
            autocommit=True
        )
        
        print("✓ Connected to TiDB successfully!")
        
        # Test basic query
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 as test, NOW()")
            result = cursor.fetchone()
            print(f"✓ Test query result: {result}")
        
        # Check available tables
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"Available tables ({len(tables)}):")
            for table in tables:
                print(f"  - {table[0]}")
        
        # If we have tables, check one of them
        if tables:
            first_table = tables[0][0]
            with connection.cursor() as cursor:
                cursor.execute(f"DESCRIBE {first_table}")
                columns = cursor.fetchall()
                print(f"\nStructure of {first_table}:")
                for col in columns:
                    print(f"  {col[0]}: {col[1]}")
                
                # Count records
                cursor.execute(f"SELECT COUNT(*) FROM {first_table}")
                count = cursor.fetchone()[0]
                print(f"  Records: {count}")
        
        connection.close()
        print("✓ Connection closed successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ TiDB connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_environment_variables():
    """Test that all required environment variables are set."""
    print("Testing environment variables...")
    
    required_vars = [
        'TIDB_HOST', 'TIDB_PORT', 'TIDB_USER', 'TIDB_PASSWORD', 
        'TIDB_DATABASE', 'DATABASE_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Only show first few characters of sensitive data
            if 'PASSWORD' in var or 'KEY' in var:
                display_value = value[:4] + '*' * (len(value) - 4) if len(value) > 4 else '***'
            else:
                display_value = value
            print(f"  {var}: {display_value}")
    
    if missing_vars:
        print(f"✗ Missing environment variables: {missing_vars}")
        return False
    else:
        print("✓ All required environment variables are set")
        return True

def main():
    """Run database connectivity tests."""
    print("TiDB Database Connectivity Test")
    print("=" * 40)
    
    # Test environment variables first
    if not test_environment_variables():
        return 1
    
    print()
    
    # Test database connection
    if test_tidb_connection():
        print("\n🎉 TiDB database connection successful!")
        return 0
    else:
        print("\n❌ TiDB database connection failed!")
        return 1

if __name__ == "__main__":
    exit(main())
