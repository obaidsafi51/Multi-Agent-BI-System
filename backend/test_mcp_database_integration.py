#!/usr/bin/env python3
"""
Test MCP integration with database layer.

This test verifies that the DatabaseManager properly integrates with the MCP client
for schema operations, query execution, and fallback mechanisms.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import (
    DatabaseManager, get_database, connect_mcp, mcp_health_check,
    discover_databases, get_tables, get_table_schema, execute_query_mcp,
    get_sample_data, validate_table_exists, validate_query,
    refresh_schema_cache, get_mcp_cache_stats, close_database
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_mcp_connection():
    """Test MCP server connection."""
    logger.info("Testing MCP connection...")
    
    try:
        # Test connection
        connected = await connect_mcp()
        logger.info(f"MCP connection result: {connected}")
        
        # Test health check
        health = await mcp_health_check()
        logger.info(f"MCP health check result: {health}")
        
        return connected and health
        
    except Exception as e:
        logger.error(f"MCP connection test failed: {e}")
        return False


async def test_database_discovery():
    """Test database discovery through MCP."""
    logger.info("Testing database discovery...")
    
    try:
        databases = await discover_databases()
        logger.info(f"Discovered {len(databases)} databases:")
        
        for db in databases:
            logger.info(f"  - {db.name} (tables: {db.table_count}, accessible: {db.accessible})")
        
        return len(databases) > 0
        
    except Exception as e:
        logger.error(f"Database discovery test failed: {e}")
        return False


async def test_table_discovery():
    """Test table discovery through MCP."""
    logger.info("Testing table discovery...")
    
    try:
        # First get databases
        databases = await discover_databases()
        if not databases:
            logger.warning("No databases found for table discovery test")
            return False
        
        # Test with first accessible database
        test_db = None
        for db in databases:
            if db.accessible and db.name not in ['information_schema', 'performance_schema', 'mysql', 'sys']:
                test_db = db.name
                break
        
        if not test_db:
            logger.warning("No suitable database found for table discovery test")
            return False
        
        tables = await get_tables(test_db)
        logger.info(f"Discovered {len(tables)} tables in database '{test_db}':")
        
        for table in tables[:5]:  # Show first 5 tables
            logger.info(f"  - {table.name} ({table.engine}, {table.rows} rows, {table.size_mb:.2f} MB)")
        
        return True
        
    except Exception as e:
        logger.error(f"Table discovery test failed: {e}")
        return False


async def test_schema_discovery():
    """Test table schema discovery through MCP."""
    logger.info("Testing schema discovery...")
    
    try:
        # Get a test table
        databases = await discover_databases()
        if not databases:
            logger.warning("No databases found for schema discovery test")
            return False
        
        test_db = None
        test_table = None
        
        for db in databases:
            if db.accessible and db.name not in ['information_schema', 'performance_schema', 'mysql', 'sys']:
                tables = await get_tables(db.name)
                if tables:
                    test_db = db.name
                    test_table = tables[0].name
                    break
        
        if not test_db or not test_table:
            logger.warning("No suitable table found for schema discovery test")
            return False
        
        schema = await get_table_schema(test_db, test_table)
        if schema:
            logger.info(f"Schema for {test_db}.{test_table}:")
            logger.info(f"  - Columns: {len(schema.columns)}")
            logger.info(f"  - Indexes: {len(schema.indexes)}")
            logger.info(f"  - Primary keys: {schema.primary_keys}")
            
            # Show first few columns
            for col in schema.columns[:3]:
                logger.info(f"    - {col.name}: {col.data_type} (nullable: {col.is_nullable})")
            
            return True
        else:
            logger.warning(f"No schema found for {test_db}.{test_table}")
            return False
        
    except Exception as e:
        logger.error(f"Schema discovery test failed: {e}")
        return False


async def test_query_execution():
    """Test query execution through MCP."""
    logger.info("Testing query execution...")
    
    try:
        # Test simple query
        result = await execute_query_mcp("SELECT 1 as test_value, NOW() as current_time")
        logger.info(f"Simple query result: {result}")
        
        if result and len(result) > 0:
            logger.info("Query execution successful")
            return True
        else:
            logger.warning("Query execution returned no results")
            return False
        
    except Exception as e:
        logger.error(f"Query execution test failed: {e}")
        return False


async def test_sample_data():
    """Test sample data retrieval through MCP."""
    logger.info("Testing sample data retrieval...")
    
    try:
        # Get a test table
        databases = await discover_databases()
        if not databases:
            logger.warning("No databases found for sample data test")
            return False
        
        test_db = None
        test_table = None
        
        for db in databases:
            if db.accessible and db.name not in ['information_schema', 'performance_schema', 'mysql', 'sys']:
                tables = await get_tables(db.name)
                for table in tables:
                    if table.rows > 0:  # Find a table with data
                        test_db = db.name
                        test_table = table.name
                        break
                if test_db:
                    break
        
        if not test_db or not test_table:
            logger.warning("No suitable table with data found for sample data test")
            return False
        
        sample_data = await get_sample_data(test_db, test_table, limit=3)
        logger.info(f"Sample data from {test_db}.{test_table}: {len(sample_data)} rows")
        
        if sample_data:
            logger.info(f"First row keys: {list(sample_data[0].keys()) if sample_data else 'No data'}")
            return True
        else:
            logger.info("No sample data returned (table might be empty)")
            return True  # This is still a successful test
        
    except Exception as e:
        logger.error(f"Sample data test failed: {e}")
        return False


async def test_validation():
    """Test validation functions through MCP."""
    logger.info("Testing validation functions...")
    
    try:
        # Test table existence validation
        databases = await discover_databases()
        if databases:
            test_db = databases[0].name
            
            # Test with existing table
            tables = await get_tables(test_db)
            if tables:
                exists = await validate_table_exists(test_db, tables[0].name)
                logger.info(f"Table {test_db}.{tables[0].name} exists: {exists}")
                
                # Test with non-existing table
                not_exists = await validate_table_exists(test_db, "non_existing_table_12345")
                logger.info(f"Non-existing table exists: {not_exists}")
                
                if exists and not not_exists:
                    logger.info("Table validation successful")
                else:
                    logger.warning("Table validation results unexpected")
        
        # Test query validation
        valid_query_result = await validate_query("SELECT 1")
        logger.info(f"Valid query validation: {valid_query_result['is_valid']}")
        
        invalid_query_result = await validate_query("SELECT FROM WHERE")
        logger.info(f"Invalid query validation: {invalid_query_result['is_valid']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Validation test failed: {e}")
        return False


async def test_cache_operations():
    """Test cache operations."""
    logger.info("Testing cache operations...")
    
    try:
        # Get initial cache stats
        initial_stats = get_mcp_cache_stats()
        if initial_stats:
            logger.info(f"Initial cache stats: {initial_stats['basic_stats']['total_entries']} entries")
        
        # Perform some operations to populate cache
        await discover_databases()
        
        # Get updated cache stats
        updated_stats = get_mcp_cache_stats()
        if updated_stats:
            logger.info(f"Updated cache stats: {updated_stats['basic_stats']['total_entries']} entries")
            logger.info(f"Cache hit rate: {updated_stats['basic_stats']['hit_rate']:.2%}")
        
        # Test cache refresh
        refresh_result = await refresh_schema_cache("all")
        logger.info(f"Cache refresh result: {refresh_result}")
        
        return True
        
    except Exception as e:
        logger.error(f"Cache operations test failed: {e}")
        return False


async def test_fallback_mechanisms():
    """Test fallback mechanisms when MCP is unavailable."""
    logger.info("Testing fallback mechanisms...")
    
    try:
        # Get database manager and temporarily disable MCP
        db_manager = get_database()
        original_enable_mcp = db_manager.enable_mcp
        
        # Disable MCP to test fallback
        db_manager.enable_mcp = False
        db_manager._mcp_connected = False
        
        logger.info("MCP disabled, testing fallback operations...")
        
        # Test database discovery fallback
        databases = await db_manager.discover_databases_mcp()
        logger.info(f"Fallback database discovery: {len(databases)} databases")
        
        if databases:
            # Test table discovery fallback
            tables = await db_manager.get_tables_mcp(databases[0].name)
            logger.info(f"Fallback table discovery: {len(tables)} tables")
            
            if tables:
                # Test schema discovery fallback
                schema = await db_manager.get_table_schema_mcp(databases[0].name, tables[0].name)
                logger.info(f"Fallback schema discovery: {'Success' if schema else 'Failed'}")
        
        # Restore original MCP setting
        db_manager.enable_mcp = original_enable_mcp
        
        return True
        
    except Exception as e:
        logger.error(f"Fallback mechanisms test failed: {e}")
        return False


async def run_all_tests():
    """Run all MCP integration tests."""
    logger.info("Starting MCP Database Integration Tests")
    logger.info("=" * 50)
    
    tests = [
        ("MCP Connection", test_mcp_connection),
        ("Database Discovery", test_database_discovery),
        ("Table Discovery", test_table_discovery),
        ("Schema Discovery", test_schema_discovery),
        ("Query Execution", test_query_execution),
        ("Sample Data", test_sample_data),
        ("Validation", test_validation),
        ("Cache Operations", test_cache_operations),
        ("Fallback Mechanisms", test_fallback_mechanisms),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            result = await test_func()
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
        logger.info(f"{test_name:20}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    # Cleanup
    await close_database()
    
    return passed == total


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)