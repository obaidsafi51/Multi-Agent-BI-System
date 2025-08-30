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

from tests.utils.env_loader import load_environment_variables

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
    
    db = DatabaseManager()
    
    # Test health check
    health_ok = db.health_check()
    assert health_ok, "Health check failed"
    logger.info("✅ Health check passed")
    
    # Test simple query
    result = db.execute_query("SELECT 1 as test", fetch_one=True)
    assert result and result.get("test") == 1, f"Expected test=1, got {result}"
    logger.info("✅ Simple query test passed")
    
    # Test database info
    info = db.get_database_info()
    logger.info(f"Database version: {info.get('version', 'Unknown')}")
    logger.info(f"TiDB version: {info.get('tidb_version', 'Not TiDB')}")
    logger.info(f"Current database: {info.get('current_database', 'Unknown')}")
    logger.info("✅ Database info test passed")


def test_global_functions():
    """Test global convenience functions"""
    logger.info("=== Testing Global Functions ===")
    
    # Test global database manager
    db = get_database()
    assert isinstance(db, DatabaseManager), "get_database() didn't return DatabaseManager instance"
    logger.info("✅ get_database() test passed")
    
    # Test global execute_query
    result = execute_query("SELECT 2 as test", fetch_one=True)
    assert result and result.get("test") == 2, f"Expected test=2, got {result}"
    logger.info("✅ Global execute_query test passed")
    
    # Test tidb_connection context manager
    with tidb_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 3 as test")
            result = cursor.fetchone()
            assert result and result.get("test") == 3, f"Expected test=3, got {result}"
    logger.info("✅ tidb_connection context manager test passed")
    
    # Test connection health function
    health_ok = test_tidb_connection()
    assert health_ok, "test_tidb_connection() failed"
    logger.info("✅ test_tidb_connection() test passed")


def test_crud_operations():
    """Test CRUD operations"""
    logger.info("=== Testing CRUD Operations ===")
    
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
    assert rows_affected == 1, f"Expected 1 row affected, got {rows_affected}"
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
    assert rows_affected == 3, f"Expected 3 rows affected, got {rows_affected}"
    logger.info("✅ Multiple insert test passed")
    
    # Select records
    records = db.execute_query("SELECT * FROM pure_pymysql_test ORDER BY id")
    assert len(records) == 4, f"Expected 4 records, got {len(records)}"  # 1 single + 3 multiple
    logger.info(f"✅ Select test passed - retrieved {len(records)} records")
    
    # Update record
    rows_affected = db.execute_query(
        "UPDATE pure_pymysql_test SET value = %s WHERE name = %s",
        (999.99, "Record 1")
    )
    assert rows_affected == 1, f"Expected 1 row updated, got {rows_affected}"
    logger.info("✅ Update test passed")
    
    # Delete record
    rows_affected = db.execute_query(
        "DELETE FROM pure_pymysql_test WHERE name = %s",
        ("Record 3",)
    )
    assert rows_affected == 1, f"Expected 1 row deleted, got {rows_affected}"
    logger.info("✅ Delete test passed")
    
    # Final count
    count_result = db.execute_query("SELECT COUNT(*) as count FROM pure_pymysql_test", fetch_one=True)
    final_count = count_result["count"]
    assert final_count == 3, f"Expected final count 3, got {final_count}"  # 4 - 1 deleted
    logger.info(f"✅ Final count test passed - {final_count} records remaining")
    
    # Cleanup
    db.execute_query("DROP TABLE IF EXISTS pure_pymysql_test")
    logger.info("✅ Test table cleaned up")


def test_transaction():
    """Test transaction functionality"""
    logger.info("=== Testing Transaction ===")
    
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
    assert success, "Transaction should have succeeded"
    logger.info("✅ Successful transaction test passed")
    
    # Verify transaction results
    records = db.execute_query("SELECT * FROM transaction_test ORDER BY id")
    assert len(records) == 2, f"Expected 2 records after transaction, got {len(records)}"
    
    assert records[0]["value"] == 150, f"Expected Item 1 value to be 150, got {records[0]['value']}"  # 100 + 50
    logger.info("✅ Transaction result verification passed")
    
    # Cleanup
    db.execute_query("DROP TABLE IF EXISTS transaction_test")
    logger.info("✅ Transaction test table cleaned up")


# Pytest-compatible test function
def test_tidb_connection():
    """Pytest-compatible test that runs all database tests"""
    load_environment_variables()
    
    # Run all tests - they now use assertions instead of returning values
    test_database_manager()
    test_global_functions() 
    test_crud_operations()
    test_transaction()


def main():
    """Run all pure PyMySQL tests"""
    logger.info("🚀 Starting Pure PyMySQL Tests (No SQLAlchemy)")
    logger.info("=" * 60)
    
    # Load environment variables using shared utility
    load_environment_variables()
    
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
            test_func()  # Functions now use assertions instead of returning values
            results.append((test_name, True))
        except Exception as e:
            logger.error(f"Test {test_name} failed: {e}")
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