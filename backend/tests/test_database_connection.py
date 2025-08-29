#!/usr/bin/env python3
"""
Test pure PyMySQL implementation without SQLAlchemy
"""

import sys
import logging
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database.connection import (
    DatabaseManager,
    get_database,
    tidb_connection,
    test_tidb_connection,
    execute_query,
    execute_many
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_database_manager():
    """Test the DatabaseManager class"""
    logger.info("=== Testing DatabaseManager ===")
    
    try:
        db = DatabaseManager()
        
        # Test health check
        health_ok = db.health_check()
        if not health_ok:
            logger.error("Health check failed")
            return False
        logger.info("✅ Health check passed")
        
        # Test simple query
        result = db.execute_query("SELECT 1 as test", fetch_one=True)
        if not result or result.get("test") != 1:
            logger.error(f"Expected test=1, got {result}")
            return False
        logger.info("✅ Simple query test passed")
        
        # Test database info
        info = db.get_database_info()
        logger.info(f"Database version: {info.get('version', 'Unknown')}")
        logger.info(f"TiDB version: {info.get('tidb_version', 'Not TiDB')}")
        logger.info(f"Current database: {info.get('current_database', 'Unknown')}")
        logger.info("✅ Database info test passed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ DatabaseManager test failed: {e}")
        return False


def test_global_functions():
    """Test global convenience functions"""
    logger.info("=== Testing Global Functions ===")
    
    try:
        # Test global database manager
        db = get_database()
        if not isinstance(db, DatabaseManager):
            logger.error("get_database() didn't return DatabaseManager instance")
            return False
        logger.info("✅ get_database() test passed")
        
        # Test global execute_query
        result = execute_query("SELECT 2 as test", fetch_one=True)
        if not result or result.get("test") != 2:
            logger.error(f"Expected test=2, got {result}")
            return False
        logger.info("✅ Global execute_query test passed")
        
        # Test tidb_connection context manager
        with tidb_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 3 as test")
                result = cursor.fetchone()
                if not result or result.get("test") != 3:
                    logger.error(f"Expected test=3, got {result}")
                    return False
        logger.info("✅ tidb_connection context manager test passed")
        
        # Test connection health function
        health_ok = test_tidb_connection()
        if not health_ok:
            logger.error("test_tidb_connection() failed")
            return False
        logger.info("✅ test_tidb_connection() test passed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Global functions test failed: {e}")
        return False


def test_crud_operations():
    """Test CRUD operations"""
    logger.info("=== Testing CRUD Operations ===")
    
    try:
        db = get_database()
        
        # Create test table
        db.execute_query("""
            CREATE TABLE IF NOT EXISTS pure_pymysql_test (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100),
                value DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ Test table created")
        
        # Insert single record
        rows_affected = db.execute_query(
            "INSERT INTO pure_pymysql_test (name, value) VALUES (%s, %s)",
            ("Single Record", 123.45)
        )
        if rows_affected != 1:
            logger.error(f"Expected 1 row affected, got {rows_affected}")
            return False
        logger.info("✅ Single insert test passed")
        
        # Insert multiple records
        test_data = [
            ("Record 1", 100.00),
            ("Record 2", 200.00),
            ("Record 3", 300.00)
        ]
        rows_affected = db.execute_many(
            "INSERT INTO pure_pymysql_test (name, value) VALUES (%s, %s)",
            test_data
        )
        if rows_affected != 3:
            logger.error(f"Expected 3 rows affected, got {rows_affected}")
            return False
        logger.info("✅ Multiple insert test passed")
        
        # Select records
        records = db.execute_query("SELECT * FROM pure_pymysql_test ORDER BY id")
        if len(records) != 4:  # 1 single + 3 multiple
            logger.error(f"Expected 4 records, got {len(records)}")
            return False
        logger.info(f"✅ Select test passed - retrieved {len(records)} records")
        
        # Update record
        rows_affected = db.execute_query(
            "UPDATE pure_pymysql_test SET value = %s WHERE name = %s",
            (999.99, "Record 1")
        )
        if rows_affected != 1:
            logger.error(f"Expected 1 row updated, got {rows_affected}")
            return False
        logger.info("✅ Update test passed")
        
        # Delete record
        rows_affected = db.execute_query(
            "DELETE FROM pure_pymysql_test WHERE name = %s",
            ("Record 3",)
        )
        if rows_affected != 1:
            logger.error(f"Expected 1 row deleted, got {rows_affected}")
            return False
        logger.info("✅ Delete test passed")
        
        # Final count
        count_result = db.execute_query("SELECT COUNT(*) as count FROM pure_pymysql_test", fetch_one=True)
        final_count = count_result["count"]
        if final_count != 3:  # 4 - 1 deleted
            logger.error(f"Expected final count 3, got {final_count}")
            return False
        logger.info(f"✅ Final count test passed - {final_count} records remaining")
        
        # Cleanup
        db.execute_query("DROP TABLE IF EXISTS pure_pymysql_test")
        logger.info("✅ Test table cleaned up")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ CRUD operations test failed: {e}")
        return False


def test_transaction():
    """Test transaction functionality"""
    logger.info("=== Testing Transaction ===")
    
    try:
        db = get_database()
        
        # Create test table
        db.execute_query("""
            CREATE TABLE IF NOT EXISTS transaction_test (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100),
                value INT
            )
        """)
        
        # Test successful transaction
        queries = [
            ("INSERT INTO transaction_test (name, value) VALUES (%s, %s)", ("Item 1", 100)),
            ("INSERT INTO transaction_test (name, value) VALUES (%s, %s)", ("Item 2", 200)),
            ("UPDATE transaction_test SET value = value + %s WHERE name = %s", (50, "Item 1"))
        ]
        
        success = db.execute_transaction(queries)
        if not success:
            logger.error("Transaction should have succeeded")
            return False
        logger.info("✅ Successful transaction test passed")
        
        # Verify transaction results
        records = db.execute_query("SELECT * FROM transaction_test ORDER BY id")
        if len(records) != 2:
            logger.error(f"Expected 2 records after transaction, got {len(records)}")
            return False
        
        if records[0]["value"] != 150:  # 100 + 50
            logger.error(f"Expected Item 1 value to be 150, got {records[0]['value']}")
            return False
        logger.info("✅ Transaction result verification passed")
        
        # Cleanup
        db.execute_query("DROP TABLE IF EXISTS transaction_test")
        logger.info("✅ Transaction test table cleaned up")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Transaction test failed: {e}")
        return False


def main():
    """Run all pure PyMySQL tests"""
    logger.info("🚀 Starting Pure PyMySQL Tests (No SQLAlchemy)")
    logger.info("=" * 60)
    
    # Load environment variables from .env file if it exists
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        logger.info(f"Loading environment from: {env_file}")
        import os
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    else:
        logger.warning("No .env file found, using environment variables")
    
    # Run tests
    tests = [
        ("Database Manager", test_database_manager),
        ("Global Functions", test_global_functions),
        ("CRUD Operations", test_crud_operations),
        ("Transaction", test_transaction),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name:.<30} {status}")
        if not passed:
            all_passed = False
    
    logger.info("="*60)
    if all_passed:
        logger.info("🎉 All tests passed! Pure PyMySQL implementation is working perfectly!")
        return 0
    else:
        logger.error("💥 Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())