"""
Demonstration of MCP schema discovery functionality.
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema_management.config import MCPSchemaConfig, SchemaValidationConfig
from schema_management.manager import MCPSchemaManager
from schema_management.models import serialize_schema_model


async def demo_schema_discovery():
    """Demonstrate schema discovery functionality."""
    print("=== MCP Schema Discovery Demo ===\n")
    
    # Initialize configuration
    config = MCPSchemaConfig(
        mcp_server_url="http://tidb-mcp-server:8000",
        cache_ttl=300,
        enable_caching=True,
        fallback_enabled=True
    )
    
    validation_config = SchemaValidationConfig(
        strict_mode=False,
        validate_types=True,
        validate_constraints=True
    )
    
    # Initialize schema manager
    manager = MCPSchemaManager(config, validation_config)
    
    print("1. Configuration:")
    print(f"   MCP Server URL: {config.mcp_server_url}")
    print(f"   Cache TTL: {config.cache_ttl} seconds")
    print(f"   Caching Enabled: {config.enable_caching}")
    print(f"   Fallback Enabled: {config.fallback_enabled}")
    print()
    
    try:
        # Test connection
        print("2. Testing MCP Server Connection...")
        connected = await manager.connect()
        if connected:
            print("   ✓ Successfully connected to MCP server")
        else:
            print("   ✗ Failed to connect to MCP server (using fallback mode)")
        print()
        
        # Discover databases
        print("3. Discovering Databases...")
        start_time = datetime.now()
        databases = await manager.discover_databases()
        discovery_time = (datetime.now() - start_time).total_seconds() * 1000
        
        print(f"   Found {len(databases)} databases (took {discovery_time:.1f}ms)")
        for db in databases:
            print(f"   - {db.name} ({db.charset}/{db.collation}) - {db.table_count or 'unknown'} tables")
        print()
        
        if databases:
            # Use the first database for further exploration
            test_db = databases[0].name
            print(f"4. Exploring Database: {test_db}")
            
            # Discover tables
            print("   Discovering tables...")
            start_time = datetime.now()
            tables = await manager.get_tables(test_db)
            discovery_time = (datetime.now() - start_time).total_seconds() * 1000
            
            print(f"   Found {len(tables)} tables (took {discovery_time:.1f}ms)")
            for table in tables[:5]:  # Show first 5 tables
                print(f"   - {table.name} ({table.type}) - {table.rows} rows, {table.size_mb:.2f}MB")
                if table.comment:
                    print(f"     Comment: {table.comment}")
            
            if len(tables) > 5:
                print(f"   ... and {len(tables) - 5} more tables")
            print()
            
            if tables:
                # Get detailed schema for first table
                test_table = tables[0].name
                print(f"5. Detailed Schema for {test_db}.{test_table}")
                
                start_time = datetime.now()
                schema = await manager.get_table_schema(test_db, test_table)
                discovery_time = (datetime.now() - start_time).total_seconds() * 1000
                
                if schema:
                    print(f"   Schema retrieved (took {discovery_time:.1f}ms)")
                    print(f"   Columns: {len(schema.columns)}")
                    print(f"   Indexes: {len(schema.indexes)}")
                    print(f"   Primary Keys: {schema.primary_keys}")
                    print(f"   Foreign Keys: {len(schema.foreign_keys)}")
                    
                    print("\n   Column Details:")
                    for col in schema.columns[:10]:  # Show first 10 columns
                        nullable = "NULL" if col.is_nullable else "NOT NULL"
                        pk_marker = " (PK)" if col.is_primary_key else ""
                        fk_marker = " (FK)" if col.is_foreign_key else ""
                        length_info = f"({col.max_length})" if col.max_length else ""
                        
                        print(f"   - {col.name}: {col.data_type}{length_info} {nullable}{pk_marker}{fk_marker}")
                        if col.comment:
                            print(f"     Comment: {col.comment}")
                    
                    if len(schema.columns) > 10:
                        print(f"   ... and {len(schema.columns) - 10} more columns")
                else:
                    print("   ✗ Failed to retrieve schema")
                print()
                
                # Test column info retrieval
                if schema and schema.columns:
                    test_column = schema.columns[0].name
                    print(f"6. Column Information for {test_db}.{test_table}.{test_column}")
                    
                    column_info = await manager.get_column_info(test_db, test_table, test_column)
                    if column_info:
                        print(f"   Name: {column_info.name}")
                        print(f"   Type: {column_info.data_type}")
                        print(f"   Nullable: {column_info.is_nullable}")
                        print(f"   Default: {column_info.default_value}")
                        print(f"   Primary Key: {column_info.is_primary_key}")
                        print(f"   Auto Increment: {column_info.is_auto_increment}")
                    else:
                        print("   ✗ Failed to retrieve column info")
                    print()
        
        # Test cache functionality
        print("7. Cache Performance")
        
        # Generate some cache activity by repeating operations
        print("   Performing cached operations...")
        for i in range(3):
            await manager.discover_databases()  # Should hit cache after first call
            if databases:
                await manager.get_tables(databases[0].name)  # Should hit cache after first call
        
        # Get cache statistics
        stats = manager.get_cache_stats()
        print(f"   Cache Entries: {stats.total_entries}")
        print(f"   Hit Rate: {stats.hit_rate:.2%}")
        print(f"   Miss Rate: {stats.miss_rate:.2%}")
        print(f"   Memory Usage: {stats.memory_usage_mb:.2f}MB")
        print(f"   Oldest Entry: {stats.oldest_entry_age_seconds}s ago")
        
        # Get detailed cache stats
        detailed_stats = manager.get_detailed_cache_stats()
        print(f"   Operation Breakdown: {detailed_stats['operation_breakdown']}")
        print(f"   Cache Health: {detailed_stats['cache_health']}")
        print()
        
        # Test cache invalidation
        print("8. Cache Management")
        print("   Testing cache invalidation...")
        
        # Invalidate specific cache entries
        invalidated = await manager.invalidate_cache_by_pattern("tables:*")
        print(f"   Invalidated {invalidated} table cache entries")
        
        # Refresh all cache
        success = await manager.refresh_schema_cache("all")
        print(f"   Cache refresh: {'✓ Success' if success else '✗ Failed'}")
        
        final_stats = manager.get_cache_stats()
        print(f"   Cache entries after refresh: {final_stats.total_entries}")
        print()
        
        # Test serialization
        if databases:
            print("9. Serialization Example")
            db_info = databases[0]
            serialized = serialize_schema_model(db_info)
            print(f"   Serialized database info:")
            print(f"   {serialized}")
            print()
        
        print("✓ Schema discovery demo completed successfully!")
        
    except Exception as e:
        print(f"✗ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        await manager.disconnect()
        print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(demo_schema_discovery())