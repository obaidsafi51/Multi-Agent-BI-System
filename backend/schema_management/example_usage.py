"""
Example usage of MCP Schema Management foundation.

This demonstrates how to use the MCP schema management components
for dynamic schema discovery and validation.
"""

import asyncio
import logging
from typing import List

from .config import MCPSchemaConfig, SchemaValidationConfig
from .manager import MCPSchemaManager
from .models import DatabaseInfo, TableSchema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_schema_discovery():
    """Example of using MCP Schema Manager for schema discovery."""
    
    # Initialize configuration
    mcp_config = MCPSchemaConfig.from_env()
    validation_config = SchemaValidationConfig.from_env()
    
    # Create schema manager
    manager = MCPSchemaManager(mcp_config, validation_config)
    
    try:
        # Connect to MCP server
        logger.info("Connecting to MCP server...")
        connected = await manager.connect()
        
        if not connected:
            logger.error("Failed to connect to MCP server")
            return
        
        # Discover databases
        logger.info("Discovering databases...")
        databases = await manager.discover_databases()
        
        if not databases:
            logger.warning("No databases found or connection failed")
            return
        
        logger.info(f"Found {len(databases)} databases:")
        for db in databases:
            logger.info(f"  - {db.name} (charset: {db.charset}, accessible: {db.accessible})")
        
        # Get tables for the first database
        if databases:
            first_db = databases[0]
            logger.info(f"Getting tables for database: {first_db.name}")
            
            tables = await manager.get_tables(first_db.name)
            logger.info(f"Found {len(tables)} tables:")
            
            for table in tables[:5]:  # Show first 5 tables
                logger.info(f"  - {table.name} ({table.type}, {table.rows} rows, {table.size_mb:.2f} MB)")
            
            # Get schema for the first table
            if tables:
                first_table = tables[0]
                logger.info(f"Getting schema for table: {first_table.name}")
                
                schema = await manager.get_table_schema(first_db.name, first_table.name)
                if schema:
                    logger.info(f"Table {schema.table} has {len(schema.columns)} columns:")
                    for col in schema.columns[:5]:  # Show first 5 columns
                        logger.info(f"  - {col.name}: {col.data_type} (nullable: {col.is_nullable})")
        
        # Show cache statistics
        cache_stats = manager.get_cache_stats()
        logger.info(f"Cache stats: {cache_stats.total_entries} entries, "
                   f"{cache_stats.hit_rate:.2%} hit rate")
        
    except Exception as e:
        logger.error(f"Error during schema discovery: {e}")
    
    finally:
        # Disconnect
        await manager.disconnect()
        logger.info("Disconnected from MCP server")


async def example_health_check():
    """Example of health checking MCP components."""
    
    manager = MCPSchemaManager()
    
    try:
        logger.info("Performing health check...")
        
        # Check if we can connect
        connected = await manager.connect()
        if connected:
            logger.info("✓ MCP server connection successful")
            
            # Check server health
            healthy = await manager.health_check()
            if healthy:
                logger.info("✓ MCP server is healthy")
            else:
                logger.warning("⚠ MCP server health check failed")
        else:
            logger.error("✗ Failed to connect to MCP server")
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
    
    finally:
        await manager.disconnect()


async def example_cache_management():
    """Example of cache management operations."""
    
    manager = MCPSchemaManager()
    
    try:
        await manager.connect()
        
        # Perform some operations to populate cache
        logger.info("Populating cache with schema operations...")
        databases = await manager.discover_databases()
        
        if databases:
            tables = await manager.get_tables(databases[0].name)
            if tables:
                schema = await manager.get_table_schema(databases[0].name, tables[0].name)
        
        # Show cache stats
        stats = manager.get_cache_stats()
        logger.info(f"Cache populated: {stats.total_entries} entries")
        
        # Refresh cache
        logger.info("Refreshing cache...")
        await manager.refresh_schema_cache("all")
        
        stats = manager.get_cache_stats()
        logger.info(f"Cache after refresh: {stats.total_entries} entries")
    
    except Exception as e:
        logger.error(f"Cache management example failed: {e}")
    
    finally:
        await manager.disconnect()


if __name__ == "__main__":
    print("MCP Schema Management Examples")
    print("=" * 40)
    
    # Note: These examples require a running TiDB MCP server
    # In a real environment, uncomment the lines below to run the examples
    
    print("Example 1: Schema Discovery")
    print("Note: Requires running TiDB MCP server")
    # asyncio.run(example_schema_discovery())
    
    print("\nExample 2: Health Check")
    print("Note: Requires running TiDB MCP server")
    # asyncio.run(example_health_check())
    
    print("\nExample 3: Cache Management")
    print("Note: Requires running TiDB MCP server")
    # asyncio.run(example_cache_management())
    
    print("\nTo run these examples, ensure the TiDB MCP server is running")
    print("and uncomment the asyncio.run() calls above.")