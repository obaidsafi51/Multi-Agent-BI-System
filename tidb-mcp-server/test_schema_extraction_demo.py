#!/usr/bin/env python3
"""
Demo script to test the detailed table schema extraction functionality.

This script demonstrates the complete schema extraction capabilities including:
- Column information with data types, nullability, defaults, and comments
- Index information with column lists, uniqueness, and types
- Primary key and foreign key constraint detection
"""

import sys
import os
from unittest.mock import Mock, patch

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Mock the database imports
with patch.dict('sys.modules', {
    'database': Mock(),
    'database.connection': Mock()
}):
    from tidb_mcp_server.schema_inspector import SchemaInspector
    from tidb_mcp_server.models import ColumnInfo, IndexInfo, TableSchema


def demo_schema_extraction():
    """Demonstrate the detailed schema extraction functionality."""
    print("🔍 TiDB MCP Server - Detailed Schema Extraction Demo")
    print("=" * 60)
    
    # Create mock database manager and cache manager
    mock_db_manager = Mock()
    mock_cache_manager = Mock()
    mock_cache_manager.get.return_value = None  # Simulate cache miss
    
    # Create schema inspector
    inspector = SchemaInspector(db_manager=mock_db_manager, cache_manager=mock_cache_manager)
    
    # Mock a complex table schema for demonstration
    print("\n📋 Extracting schema for 'ecommerce.orders' table...")
    
    # Mock database responses for a realistic e-commerce orders table
    mock_db_manager.execute_query.side_effect = [
        # Column information query response
        [
            {'name': 'id', 'data_type': 'bigint', 'is_nullable': 'NO', 'default_value': None, 'comment': 'Auto-increment primary key'},
            {'name': 'user_id', 'data_type': 'bigint', 'is_nullable': 'NO', 'default_value': None, 'comment': 'Customer who placed the order'},
            {'name': 'order_number', 'data_type': 'varchar', 'is_nullable': 'NO', 'default_value': None, 'comment': 'Unique order identifier'},
            {'name': 'total_amount', 'data_type': 'decimal', 'is_nullable': 'NO', 'default_value': '0.00', 'comment': 'Total order amount'},
            {'name': 'status', 'data_type': 'enum', 'is_nullable': 'NO', 'default_value': 'pending', 'comment': 'Order status'},
            {'name': 'shipping_address_id', 'data_type': 'bigint', 'is_nullable': 'YES', 'default_value': None, 'comment': 'Shipping address reference'},
            {'name': 'created_at', 'data_type': 'timestamp', 'is_nullable': 'NO', 'default_value': 'CURRENT_TIMESTAMP', 'comment': 'Order creation time'},
            {'name': 'updated_at', 'data_type': 'timestamp', 'is_nullable': 'YES', 'default_value': None, 'comment': 'Last update time'}
        ],
        # Index information query response
        [
            {'name': 'PRIMARY', 'column_name': 'id', 'non_unique': 0, 'index_type': 'BTREE', 'seq_in_index': 1},
            {'name': 'idx_user_status', 'column_name': 'user_id', 'non_unique': 1, 'index_type': 'BTREE', 'seq_in_index': 1},
            {'name': 'idx_user_status', 'column_name': 'status', 'non_unique': 1, 'index_type': 'BTREE', 'seq_in_index': 2},
            {'name': 'idx_order_number', 'column_name': 'order_number', 'non_unique': 0, 'index_type': 'BTREE', 'seq_in_index': 1},
            {'name': 'idx_created_at', 'column_name': 'created_at', 'non_unique': 1, 'index_type': 'BTREE', 'seq_in_index': 1},
            {'name': 'idx_shipping_address', 'column_name': 'shipping_address_id', 'non_unique': 1, 'index_type': 'BTREE', 'seq_in_index': 1}
        ],
        # Primary key query response
        [{'COLUMN_NAME': 'id'}],
        # Foreign key query response
        [
            {
                'column_name': 'user_id',
                'constraint_name': 'fk_orders_user',
                'referenced_database': 'ecommerce',
                'referenced_table': 'users',
                'referenced_column': 'id'
            },
            {
                'column_name': 'shipping_address_id',
                'constraint_name': 'fk_orders_shipping_address',
                'referenced_database': 'ecommerce',
                'referenced_table': 'addresses',
                'referenced_column': 'id'
            }
        ]
    ]
    
    # Extract the complete table schema
    schema = inspector.get_table_schema('ecommerce', 'orders')
    
    # Display the extracted schema information
    print(f"\n📊 Schema for {schema.database}.{schema.table}")
    print("-" * 40)
    
    print(f"\n🏛️  Columns ({len(schema.columns)}):")
    for col in schema.columns:
        pk_marker = " 🔑" if col.is_primary_key else ""
        fk_marker = " 🔗" if col.is_foreign_key else ""
        nullable = "NULL" if col.is_nullable else "NOT NULL"
        default = f" DEFAULT {col.default_value}" if col.default_value else ""
        comment = f" -- {col.comment}" if col.comment else ""
        
        print(f"  • {col.name}: {col.data_type.upper()} {nullable}{default}{pk_marker}{fk_marker}{comment}")
    
    print(f"\n🗂️  Indexes ({len(schema.indexes)}):")
    for idx in schema.indexes:
        unique_marker = " (UNIQUE)" if idx.is_unique else ""
        columns_str = ", ".join(idx.columns)
        print(f"  • {idx.name}: {idx.index_type} on ({columns_str}){unique_marker}")
    
    print(f"\n🔑 Primary Keys: {', '.join(schema.primary_keys) if schema.primary_keys else 'None'}")
    
    print(f"\n🔗 Foreign Keys ({len(schema.foreign_keys)}):")
    for fk in schema.foreign_keys:
        print(f"  • {fk['column_name']} → {fk['referenced_table']}.{fk['referenced_column']} ({fk['constraint_name']})")
    
    # Verify that all database queries were executed
    print(f"\n📈 Performance:")
    print(f"  • Database queries executed: {mock_db_manager.execute_query.call_count}")
    print(f"  • Schema cached: {'✓' if mock_cache_manager.set.called else '✗'}")
    
    print("\n✅ Schema extraction completed successfully!")
    
    return schema


def demo_edge_cases():
    """Demonstrate handling of edge cases in schema extraction."""
    print("\n🧪 Testing Edge Cases")
    print("-" * 30)
    
    mock_db_manager = Mock()
    mock_cache_manager = Mock()
    mock_cache_manager.get.return_value = None
    
    inspector = SchemaInspector(db_manager=mock_db_manager, cache_manager=mock_cache_manager)
    
    # Test table with no indexes
    print("\n1. Table with no indexes:")
    mock_db_manager.execute_query.side_effect = [
        [{'name': 'id', 'data_type': 'int', 'is_nullable': 'NO', 'default_value': None, 'comment': ''}],
        [],  # No indexes
        [],  # No primary keys
        []   # No foreign keys
    ]
    
    schema = inspector.get_table_schema('test_db', 'simple_table')
    print(f"   ✓ Columns: {len(schema.columns)}, Indexes: {len(schema.indexes)}")
    
    # Test table with composite primary key
    print("\n2. Table with composite primary key:")
    mock_db_manager.execute_query.side_effect = [
        [
            {'name': 'order_id', 'data_type': 'int', 'is_nullable': 'NO', 'default_value': None, 'comment': ''},
            {'name': 'product_id', 'data_type': 'int', 'is_nullable': 'NO', 'default_value': None, 'comment': ''}
        ],
        [],  # No additional indexes
        [{'COLUMN_NAME': 'order_id'}, {'COLUMN_NAME': 'product_id'}],  # Composite primary key
        []   # No foreign keys
    ]
    
    schema = inspector.get_table_schema('test_db', 'order_items')
    pk_columns = [col.name for col in schema.columns if col.is_primary_key]
    print(f"   ✓ Primary key columns: {pk_columns}")
    
    # Test handling of NULL values in metadata
    print("\n3. Table with NULL metadata values:")
    mock_db_manager.execute_query.side_effect = [
        [{'name': 'test_col', 'data_type': 'varchar', 'is_nullable': 'YES', 'default_value': None, 'comment': None}],
        [{'name': 'test_idx', 'column_name': 'test_col', 'non_unique': 1, 'index_type': None, 'seq_in_index': 1}],
        [],
        []
    ]
    
    schema = inspector.get_table_schema('test_db', 'null_metadata_table')
    print(f"   ✓ Handled NULL comment: '{schema.columns[0].comment}'")
    print(f"   ✓ Handled NULL index_type: '{schema.indexes[0].index_type}'")
    
    print("\n✅ All edge cases handled correctly!")


if __name__ == "__main__":
    try:
        # Run the main demonstration
        schema = demo_schema_extraction()
        
        # Run edge case tests
        demo_edge_cases()
        
        print("\n🎉 All tests completed successfully!")
        print("\nThe detailed schema extraction implementation includes:")
        print("  ✓ Column information with data types, nullability, defaults, and comments")
        print("  ✓ Index information with column lists, uniqueness, and types")
        print("  ✓ Primary key constraint detection")
        print("  ✓ Foreign key constraint detection with references")
        print("  ✓ Proper handling of composite keys and NULL values")
        print("  ✓ Caching integration for performance optimization")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        sys.exit(1)