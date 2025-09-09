#!/usr/bin/env python3
"""
Example usage script for Phase 2: Semantic Understanding and Query Intelligence.

This script demonstrates how to use the new semantic mapping, intelligent query building,
and schema change detection features.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the enhanced schema manager
from backend.schema_management.manager import MCPSchemaManager
from backend.schema_management.config import MCPSchemaConfig


async def demonstrate_semantic_mapping(schema_manager: MCPSchemaManager):
    """Demonstrate semantic mapping capabilities."""
    print("\n" + "="*60)
    print("SEMANTIC MAPPING DEMONSTRATION")
    print("="*60)
    
    # Business terms to test
    business_terms = [
        'revenue',
        'customer',
        'order',
        'product',
        'date',
        'profit'
    ]
    
    for term in business_terms:
        print(f"\n--- Mapping business term: '{term}' ---")
        
        try:
            mappings = await schema_manager.map_business_term_to_schema(
                business_term=term,
                context="Sales and financial analysis",
                filter_criteria={'element_type': 'column'}
            )
            
            if mappings:
                print(f"Found {len(mappings)} mappings:")
                for i, mapping in enumerate(mappings[:3], 1):  # Show top 3
                    print(f"  {i}. {mapping['schema_element_path']}")
                    print(f"     Confidence: {mapping['confidence_score']:.2f}")
                    print(f"     Type: {mapping['similarity_type']}")
                    if mapping['context_match']:
                        print(f"     ✓ Context match")
            else:
                print(f"  No mappings found for '{term}'")
                
        except Exception as e:
            print(f"  Error mapping '{term}': {e}")


async def demonstrate_intelligent_query_building(schema_manager: MCPSchemaManager):
    """Demonstrate intelligent query building."""
    print("\n" + "="*60)
    print("INTELLIGENT QUERY BUILDING DEMONSTRATION")
    print("="*60)
    
    # Example query intents
    query_examples = [
        {
            'description': 'Total revenue by month for last year',
            'intent': {
                'metric_type': 'revenue',
                'filters': {'year': 2023},
                'time_period': 'last_year',
                'aggregation_type': 'sum',
                'group_by': ['month'],
                'order_by': 'month',
                'limit': 12,
                'confidence': 0.9,
                'parsed_entities': {'revenue': 'total_amount', 'month': 'order_date'}
            },
            'context': {
                'user_id': 'analyst_001',
                'session_id': 'demo_session',
                'query_history': [],
                'available_schemas': ['sales_db', 'crm_db'],
                'user_preferences': {'default_limit': 1000},
                'business_context': 'Monthly revenue analysis for 2023'
            }
        },
        {
            'description': 'Customer count by region',
            'intent': {
                'metric_type': 'customer',
                'filters': {},
                'time_period': None,
                'aggregation_type': 'count',
                'group_by': ['region'],
                'order_by': 'customer_count',
                'limit': 50,
                'confidence': 0.8,
                'parsed_entities': {'customer': 'customer_id', 'region': 'customer_region'}
            },
            'context': {
                'user_id': 'analyst_001',
                'session_id': 'demo_session',
                'query_history': [],
                'available_schemas': ['crm_db'],
                'user_preferences': {'default_limit': 1000},
                'business_context': 'Customer distribution analysis'
            }
        },
        {
            'description': 'Top products by sales this quarter',
            'intent': {
                'metric_type': 'sales',
                'filters': {'quarter': 'current'},
                'time_period': 'this_quarter',
                'aggregation_type': 'sum',
                'group_by': ['product'],
                'order_by': 'sales',
                'limit': 10,
                'confidence': 0.85,
                'parsed_entities': {'sales': 'sales_amount', 'product': 'product_name'}
            },
            'context': {
                'user_id': 'analyst_001',
                'session_id': 'demo_session',
                'query_history': [],
                'available_schemas': ['sales_db', 'product_db'],
                'user_preferences': {'default_limit': 1000},
                'business_context': 'Product performance analysis for current quarter'
            }
        }
    ]
    
    for example in query_examples:
        print(f"\n--- Query: {example['description']} ---")
        
        try:
            result = await schema_manager.build_intelligent_query(
                query_intent=example['intent'],
                query_context=example['context']
            )
            
            if result['success']:
                print("Generated SQL:")
                print(f"```sql")
                print(result['sql'])
                print(f"```")
                print(f"Confidence Score: {result['confidence_score']:.2f}")
                print(f"Processing Time: {result['processing_time_ms']}ms")
                
                if result['estimated_rows']:
                    print(f"Estimated Result Size: {result['estimated_rows']} rows")
                
                if result['optimization_hints']:
                    print("Optimization Hints:")
                    for hint in result['optimization_hints']:
                        print(f"  • {hint}")
                
                if result['used_mappings']:
                    print("Used Mappings:")
                    for mapping in result['used_mappings']:
                        print(f"  • {mapping['business_term']} → {mapping['schema_element_path']} "
                              f"(confidence: {mapping['confidence_score']:.2f})")
                
                if result['alternative_queries']:
                    print(f"Alternative queries available: {len(result['alternative_queries'])}")
            else:
                print(f"Query building failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"  Error building query: {e}")


async def demonstrate_schema_change_detection(schema_manager: MCPSchemaManager):
    """Demonstrate schema change detection."""
    print("\n" + "="*60)
    print("SCHEMA CHANGE DETECTION DEMONSTRATION")
    print("="*60)
    
    # Check if change detection is enabled
    stats = await schema_manager.get_change_detection_statistics()
    
    if not stats.get('enabled', False):
        print("Schema change detection is not enabled")
        return
    
    print("Change Detection Status: ✓ Enabled")
    print(f"Monitoring Active: {stats.get('recent_activity', {}).get('monitoring_enabled', False)}")
    
    # Force a schema check
    print("\n--- Forcing immediate schema check ---")
    check_result = await schema_manager.force_schema_change_check()
    
    if check_result['success']:
        print(f"Schema check completed: {check_result['changes_detected']} changes detected")
        
        if check_result['changes_detected'] > 0:
            print("Detected changes:")
            for change in check_result['changes']:
                print(f"  • {change['change_type']} in {change['database']}.{change['table']}")
                print(f"    Element: {change['element_name']} (Severity: {change['severity']})")
    else:
        print(f"Schema check failed: {check_result.get('error', 'Unknown error')}")
    
    # Get change history
    print("\n--- Recent schema change history ---")
    try:
        changes = await schema_manager.get_schema_change_history(limit=5)
        
        if changes:
            print(f"Found {len(changes)} recent changes:")
            for change in changes:
                print(f"  • {change['detected_at'][:19]}: {change['change_type']}")
                print(f"    {change['database']}.{change.get('table', 'N/A')}.{change['element_name']}")
                print(f"    Severity: {change['severity']}")
                
                if change.get('migration_suggestions'):
                    print(f"    Migration suggestions:")
                    for suggestion in change['migration_suggestions'][:2]:
                        print(f"      - {suggestion}")
        else:
            print("No recent schema changes found")
            
    except Exception as e:
        print(f"Failed to get change history: {e}")
    
    # Show change statistics
    print("\n--- Change Detection Statistics ---")
    print(f"Total changes tracked: {stats.get('total_changes', 0)}")
    
    if stats.get('by_severity'):
        print("Changes by severity:")
        for severity, count in stats['by_severity'].items():
            print(f"  {severity}: {count}")
    
    if stats.get('by_type'):
        print("Changes by type:")
        for change_type, count in list(stats['by_type'].items())[:5]:
            print(f"  {change_type}: {count}")


async def demonstrate_learning_capabilities(schema_manager: MCPSchemaManager):
    """Demonstrate learning from successful queries."""
    print("\n" + "="*60)
    print("LEARNING CAPABILITIES DEMONSTRATION")
    print("="*60)
    
    # Simulate successful query mappings
    successful_mappings = [
        {
            'business_term': 'revenue',
            'schema_element_path': 'sales_db.orders.total_amount',
            'success_score': 1.0
        },
        {
            'business_term': 'customer',
            'schema_element_path': 'crm_db.customers.customer_id',
            'success_score': 0.9
        },
        {
            'business_term': 'profit_margin',
            'schema_element_path': 'sales_db.order_items.profit_margin',
            'success_score': 0.8
        }
    ]
    
    print("Learning from successful query mappings...")
    
    for mapping in successful_mappings:
        try:
            schema_manager.learn_from_successful_query(
                business_term=mapping['business_term'],
                schema_element_path=mapping['schema_element_path'],
                success_score=mapping['success_score']
            )
            print(f"✓ Learned: '{mapping['business_term']}' → '{mapping['schema_element_path']}'")
        except Exception as e:
            print(f"✗ Failed to learn mapping: {e}")
    
    # Show updated semantic mapping statistics
    print("\n--- Updated Semantic Mapping Statistics ---")
    try:
        stats = await schema_manager.get_semantic_mapping_statistics()
        
        if stats.get('enabled', False):
            print(f"Total schema elements: {stats.get('total_schema_elements', 0)}")
            print(f"Total business terms: {stats.get('total_business_terms', 0)}")
            print(f"Learned mappings: {stats.get('learned_mappings_count', 0)}")
            
            if stats.get('business_term_categories'):
                print("Business term categories:")
                for category, count in stats['business_term_categories'].items():
                    print(f"  {category}: {count}")
        else:
            print("Semantic mapping is not enabled")
            
    except Exception as e:
        print(f"Failed to get semantic mapping statistics: {e}")


async def setup_change_listener(schema_manager: MCPSchemaManager):
    """Set up a schema change listener."""
    
    def change_listener(change):
        """Example change listener function."""
        print(f"\n🔔 SCHEMA CHANGE ALERT:")
        print(f"   Type: {change.change_type.value}")
        print(f"   Severity: {change.severity.value}")
        print(f"   Location: {change.database}.{change.table or 'N/A'}.{change.element_name}")
        print(f"   Time: {change.detected_at}")
        
        if change.impact_analysis:
            impact = change.impact_analysis
            if impact.get('breaking_change'):
                print("   ⚠️  BREAKING CHANGE DETECTED!")
            
            if impact.get('migration_required'):
                print("   📋 Migration required")
        
        if change.migration_suggestions:
            print("   💡 Migration suggestions:")
            for suggestion in change.migration_suggestions[:2]:
                print(f"      - {suggestion}")
    
    # Add the listener
    try:
        schema_manager.add_schema_change_listener(change_listener)
        print("✓ Schema change listener added")
    except Exception as e:
        print(f"✗ Failed to add change listener: {e}")


async def main():
    """Main demonstration function."""
    print("🚀 Phase 2: Semantic Understanding and Query Intelligence Demo")
    print("=" * 80)
    
    # Initialize schema manager with Phase 2 features enabled
    config = MCPSchemaConfig.from_env()
    
    schema_manager = MCPSchemaManager(
        mcp_config=config,
        enable_semantic_mapping=True,
        enable_change_detection=True,
        enable_monitoring=True
    )
    
    try:
        # Connect to the MCP server
        print("Connecting to MCP server...")
        connected = await schema_manager.connect()
        
        if not connected:
            print("❌ Failed to connect to MCP server")
            print("Please ensure the MCP server is running and configured correctly.")
            return
        
        print("✅ Connected to MCP server")
        
        # Set up change listener
        await setup_change_listener(schema_manager)
        
        # Run demonstrations
        await demonstrate_semantic_mapping(schema_manager)
        await demonstrate_intelligent_query_building(schema_manager)
        await demonstrate_schema_change_detection(schema_manager)
        await demonstrate_learning_capabilities(schema_manager)
        
        print("\n" + "="*80)
        print("🎉 Phase 2 demonstration completed successfully!")
        print("="*80)
        
        # Keep the script running briefly to allow any background monitoring
        print("\nMonitoring for schema changes for 10 seconds...")
        await asyncio.sleep(10)
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        print(f"❌ Demonstration failed: {e}")
    
    finally:
        # Clean shutdown
        try:
            await schema_manager.disconnect()
            print("✅ Disconnected from MCP server")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())
