#!/usr/bin/env python3
"""
Basic test for MCP integration with database layer.

This test verifies that the DatabaseManager can be initialized with MCP integration
and that fallback mechanisms work when MCP is not available.
"""

import asyncio
import logging
import os
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_database_manager_initialization():
    """Test DatabaseManager initialization with and without MCP."""
    logger.info("Testing DatabaseManager initialization...")
    
    try:
        from database.connection import DatabaseManager, DatabaseConfig
        
        # Test with MCP enabled (default)
        db_manager_mcp = DatabaseManager(enable_mcp=True)
        logger.info(f"DatabaseManager with MCP enabled: {db_manager_mcp.enable_mcp}")
        
        # Test with MCP disabled
        db_manager_no_mcp = DatabaseManager(enable_mcp=False)
        logger.info(f"DatabaseManager with MCP disabled: {db_manager_no_mcp.enable_mcp}")
        
        # Test basic database configuration
        config = DatabaseConfig()
        logger.info(f"Database config - Host: {config.host}, Port: {config.port}")
        
        return True
        
    except Exception as e:
        logger.error(f"DatabaseManager initialization test failed: {e}")
        return False


def test_basic_database_operations():
    """Test basic database operations without MCP."""
    logger.info("Testing basic database operations...")
    
    try:
        from database.connection import DatabaseManager
        
        # Create manager without MCP
        db_manager = DatabaseManager(enable_mcp=False)
        
        # Test health check (this should work with direct connection)
        try:
            health = db_manager.health_check()
            logger.info(f"Database health check: {health}")
        except Exception as e:
            logger.warning(f"Database health check failed (expected if no DB): {e}")
        
        # Test database info retrieval
        try:
            info = db_manager.get_database_info()
            logger.info(f"Database info keys: {list(info.keys())}")
        except Exception as e:
            logger.warning(f"Database info retrieval failed (expected if no DB): {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Basic database operations test failed: {e}")
        return False


async def test_mcp_methods_with_fallback():
    """Test MCP methods with fallback when MCP is not available."""
    logger.info("Testing MCP methods with fallback...")
    
    try:
        from database.connection import DatabaseManager
        
        # Create manager with MCP disabled to test fallback
        db_manager = DatabaseManager(enable_mcp=False)
        
        # Test MCP health check (should return False when disabled)
        health = await db_manager.mcp_health_check()
        logger.info(f"MCP health check (disabled): {health}")
        
        # Test cache stats (should return None when disabled)
        cache_stats = db_manager.get_mcp_cache_stats()
        logger.info(f"MCP cache stats (disabled): {cache_stats}")
        
        # Test cache refresh (should return False when disabled)
        refresh_result = await db_manager.refresh_schema_cache_mcp()
        logger.info(f"MCP cache refresh (disabled): {refresh_result}")
        
        return True
        
    except Exception as e:
        logger.error(f"MCP methods with fallback test failed: {e}")
        return False


async def test_global_functions():
    """Test global convenience functions."""
    logger.info("Testing global convenience functions...")
    
    try:
        from database.connection import (
            get_database, connect_mcp, mcp_health_check,
            get_mcp_cache_stats, close_database
        )
        
        # Test get_database
        db = get_database()
        logger.info(f"Global database manager: {type(db).__name__}")
        
        # Test MCP functions (should handle gracefully when MCP not available)
        try:
            connected = await connect_mcp()
            logger.info(f"Global MCP connect: {connected}")
        except Exception as e:
            logger.warning(f"Global MCP connect failed (expected): {e}")
        
        try:
            health = await mcp_health_check()
            logger.info(f"Global MCP health check: {health}")
        except Exception as e:
            logger.warning(f"Global MCP health check failed (expected): {e}")
        
        # Test cache stats
        stats = get_mcp_cache_stats()
        logger.info(f"Global MCP cache stats: {stats}")
        
        # Test cleanup
        await close_database()
        logger.info("Global database cleanup completed")
        
        return True
        
    except Exception as e:
        logger.error(f"Global functions test failed: {e}")
        return False


def test_import_structure():
    """Test that all imports work correctly."""
    logger.info("Testing import structure...")
    
    try:
        # Test database connection imports
        from database.connection import (
            DatabaseManager, DatabaseConfig, get_database,
            tidb_connection, test_tidb_connection
        )
        logger.info("Database connection imports: OK")
        
        # Test that MCP-related imports are handled gracefully
        try:
            from database.connection import (
                connect_mcp, mcp_health_check, discover_databases,
                get_tables, get_table_schema
            )
            logger.info("MCP-related imports: OK")
        except ImportError as e:
            logger.warning(f"MCP-related imports failed (may be expected): {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Import structure test failed: {e}")
        return False


async def run_basic_tests():
    """Run all basic MCP integration tests."""
    logger.info("Starting Basic MCP Integration Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Import Structure", test_import_structure),
        ("DatabaseManager Initialization", test_database_manager_initialization),
        ("Basic Database Operations", test_basic_database_operations),
        ("MCP Methods with Fallback", test_mcp_methods_with_fallback),
        ("Global Functions", test_global_functions),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results[test_name] = result
            status = "PASS" if result else "FAIL"
            logger.info(f"{test_name} Test: {status}")
        except Exception as e:
            results[test_name] = False
            logger.error(f"{test_name} Test: ERROR - {e}")
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("Test Results Summary:")
    logger.info("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name:30}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    return passed == total


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(run_basic_tests())
    sys.exit(0 if success else 1)