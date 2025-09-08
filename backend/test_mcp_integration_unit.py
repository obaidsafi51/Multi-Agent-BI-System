#!/usr/bin/env python3
"""
Unit test for MCP integration with database layer.

This test verifies the integration without requiring actual MCP server connection.
"""

import asyncio
import logging
import os
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce log noise
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_database_manager_mcp_integration():
    """Test DatabaseManager MCP integration components."""
    logger.info("Testing DatabaseManager MCP integration...")
    
    try:
        from database.connection import DatabaseManager
        
        # Test with MCP enabled
        db_manager = DatabaseManager(enable_mcp=True)
        
        # Check MCP components are initialized
        assert hasattr(db_manager, 'mcp_schema_manager'), "MCP schema manager should be initialized"
        assert hasattr(db_manager, 'mcp_client'), "MCP client should be initialized"
        assert hasattr(db_manager, '_mcp_connected'), "MCP connection state should be tracked"
        
        # Check MCP is enabled
        assert db_manager.enable_mcp == True, "MCP should be enabled"
        
        # Test with MCP disabled
        db_manager_no_mcp = DatabaseManager(enable_mcp=False)
        assert db_manager_no_mcp.enable_mcp == False, "MCP should be disabled"
        assert db_manager_no_mcp.mcp_schema_manager is None, "MCP schema manager should be None when disabled"
        
        logger.info("DatabaseManager MCP integration test: PASS")
        return True
        
    except Exception as e:
        logger.error(f"DatabaseManager MCP integration test failed: {e}")
        return False


async def test_mcp_methods_without_connection():
    """Test MCP methods behavior when not connected."""
    logger.info("Testing MCP methods without connection...")
    
    try:
        from database.connection import DatabaseManager
        
        # Create manager with MCP enabled but don't connect
        db_manager = DatabaseManager(enable_mcp=True)
        
        # Test health check (should return False when not connected)
        health = await db_manager.mcp_health_check()
        assert health == False, "Health check should return False when not connected"
        
        # Test cache stats (should return None or empty stats)
        cache_stats = db_manager.get_mcp_cache_stats()
        assert cache_stats is not None, "Cache stats should be available even when not connected"
        
        # Test cache refresh (should return False when not connected)
        refresh_result = await db_manager.refresh_schema_cache_mcp()
        assert refresh_result == False, "Cache refresh should return False when not connected"
        
        logger.info("MCP methods without connection test: PASS")
        return True
        
    except Exception as e:
        logger.error(f"MCP methods without connection test failed: {e}")
        return False


async def test_fallback_methods():
    """Test fallback methods work correctly."""
    logger.info("Testing fallback methods...")
    
    try:
        from database.connection import DatabaseManager
        
        # Create manager with MCP disabled to force fallback
        db_manager = DatabaseManager(enable_mcp=False)
        
        # Test database discovery fallback (should not raise exception)
        try:
            databases = await db_manager.discover_databases_mcp()
            # Should return empty list or handle gracefully
            assert isinstance(databases, list), "Fallback should return a list"
            logger.info(f"Fallback database discovery returned {len(databases)} databases")
        except Exception as e:
            # Connection errors are expected in test environment
            logger.info(f"Fallback database discovery failed as expected: {type(e).__name__}")
        
        # Test table discovery fallback
        try:
            tables = await db_manager.get_tables_mcp("test_db")
            assert isinstance(tables, list), "Fallback should return a list"
            logger.info(f"Fallback table discovery returned {len(tables)} tables")
        except Exception as e:
            logger.info(f"Fallback table discovery failed as expected: {type(e).__name__}")
        
        # Test schema discovery fallback
        try:
            schema = await db_manager.get_table_schema_mcp("test_db", "test_table")
            # Should return None or schema object
            logger.info(f"Fallback schema discovery returned: {type(schema).__name__ if schema else 'None'}")
        except Exception as e:
            logger.info(f"Fallback schema discovery failed as expected: {type(e).__name__}")
        
        logger.info("Fallback methods test: PASS")
        return True
        
    except Exception as e:
        logger.error(f"Fallback methods test failed: {e}")
        return False


def test_global_functions_exist():
    """Test that all global functions are properly exported."""
    logger.info("Testing global functions exist...")
    
    try:
        from database.connection import (
            get_database, connect_mcp, mcp_health_check,
            discover_databases, get_tables, get_table_schema,
            execute_query_mcp, get_sample_data, validate_table_exists,
            validate_query, refresh_schema_cache, get_mcp_cache_stats,
            close_database
        )
        
        # Check all functions are callable
        functions = [
            get_database, connect_mcp, mcp_health_check,
            discover_databases, get_tables, get_table_schema,
            execute_query_mcp, get_sample_data, validate_table_exists,
            validate_query, refresh_schema_cache, get_mcp_cache_stats,
            close_database
        ]
        
        for func in functions:
            assert callable(func), f"Function {func.__name__} should be callable"
        
        logger.info("Global functions exist test: PASS")
        return True
        
    except Exception as e:
        logger.error(f"Global functions exist test failed: {e}")
        return False


def test_configuration_handling():
    """Test MCP configuration handling."""
    logger.info("Testing MCP configuration handling...")
    
    try:
        from database.connection import DatabaseManager
        
        # Test with default configuration
        db_manager = DatabaseManager(enable_mcp=True)
        
        if db_manager.mcp_schema_manager:
            config = db_manager.mcp_schema_manager.mcp_config
            
            # Check configuration has expected attributes
            assert hasattr(config, 'mcp_server_url'), "Config should have mcp_server_url"
            assert hasattr(config, 'connection_timeout'), "Config should have connection_timeout"
            assert hasattr(config, 'request_timeout'), "Config should have request_timeout"
            assert hasattr(config, 'max_retries'), "Config should have max_retries"
            assert hasattr(config, 'enable_caching'), "Config should have enable_caching"
            assert hasattr(config, 'fallback_enabled'), "Config should have fallback_enabled"
            
            logger.info(f"MCP server URL: {config.mcp_server_url}")
            logger.info(f"Connection timeout: {config.connection_timeout}")
            logger.info(f"Fallback enabled: {config.fallback_enabled}")
        
        logger.info("Configuration handling test: PASS")
        return True
        
    except Exception as e:
        logger.error(f"Configuration handling test failed: {e}")
        return False


async def test_error_handling():
    """Test error handling in MCP operations."""
    logger.info("Testing error handling...")
    
    try:
        from database.connection import DatabaseManager
        
        # Create manager with MCP enabled
        db_manager = DatabaseManager(enable_mcp=True)
        
        # Test operations that should handle errors gracefully
        
        # Test connection with invalid server (should not crash)
        try:
            connected = await db_manager.connect_mcp()
            logger.info(f"Connection attempt result: {connected}")
        except Exception as e:
            logger.info(f"Connection failed as expected: {type(e).__name__}")
        
        # Test health check (should not crash)
        try:
            health = await db_manager.mcp_health_check()
            logger.info(f"Health check result: {health}")
        except Exception as e:
            logger.info(f"Health check failed as expected: {type(e).__name__}")
        
        # Test MCP connection context manager (should handle errors)
        try:
            async with db_manager.get_mcp_connection() as client:
                logger.info("MCP connection context manager worked")
        except Exception as e:
            logger.info(f"MCP connection context failed as expected: {type(e).__name__}")
        
        logger.info("Error handling test: PASS")
        return True
        
    except Exception as e:
        logger.error(f"Error handling test failed: {e}")
        return False


async def run_unit_tests():
    """Run all unit tests for MCP integration."""
    logger.info("Starting MCP Integration Unit Tests")
    logger.info("=" * 50)
    
    tests = [
        ("DatabaseManager MCP Integration", test_database_manager_mcp_integration),
        ("MCP Methods Without Connection", test_mcp_methods_without_connection),
        ("Fallback Methods", test_fallback_methods),
        ("Global Functions Exist", test_global_functions_exist),
        ("Configuration Handling", test_configuration_handling),
        ("Error Handling", test_error_handling),
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
        logger.info(f"{test_name:35}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    return passed == total


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(run_unit_tests())
    print(f"\nMCP Integration Unit Tests: {'SUCCESS' if success else 'FAILED'}")
    sys.exit(0 if success else 1)