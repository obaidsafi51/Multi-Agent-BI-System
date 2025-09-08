"""
Example usage of the refactored Schema Knowledge Base with MCP integration.

This example demonstrates how to use the enhanced SchemaKnowledgeBase
that integrates with MCP for dynamic schema management while preserving
all business logic functionality.
"""

import asyncio
import sys
import os
from datetime import date

# Add the backend path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from schema_knowledge.knowledge_base import SchemaKnowledgeBase
    from models.core import QueryIntent
except ImportError as e:
    print(f"Import error: {e}")
    print("Note: This example requires the backend modules to be properly set up")
    sys.exit(1)


class MCPClientExample:
    """
    Example MCP client implementation for demonstration.
    In a real implementation, this would connect to your actual MCP server.
    """
    
    async def call_tool(self, tool_name: str, params: dict):
        """Mock MCP tool calls for demonstration."""
        if tool_name == "list_databases":
            return {
                "databases": [
                    {"name": "financial_db", "accessible": True, "charset": "utf8mb4"},
                    {"name": "analytics_db", "accessible": True, "charset": "utf8mb4"}
                ]
            }
        
        elif tool_name == "list_tables":
            database = params.get("database")
            if database == "financial_db":
                return {
                    "tables": [
                        {"name": "financial_overview", "type": "BASE TABLE", "rows": 15000},
                        {"name": "cash_flow", "type": "BASE TABLE", "rows": 12000},
                        {"name": "budget_tracking", "type": "BASE TABLE", "rows": 8500}
                    ]
                }
        
        elif tool_name == "get_table_schema":
            database = params.get("database")
            table = params.get("table")
            
            if database == "financial_db" and table == "financial_overview":
                return {
                    "columns": [
                        {"name": "id", "data_type": "int", "is_nullable": False},
                        {"name": "revenue", "data_type": "decimal", "is_nullable": True},
                        {"name": "net_profit", "data_type": "decimal", "is_nullable": True},
                        {"name": "gross_profit", "data_type": "decimal", "is_nullable": True},
                        {"name": "period_date", "data_type": "date", "is_nullable": False}
                    ],
                    "indexes": [
                        {"name": "PRIMARY", "columns": ["id"], "is_unique": True},
                        {"name": "idx_period", "columns": ["period_date"], "is_unique": False}
                    ],
                    "primary_keys": ["id"],
                    "foreign_keys": [],
                    "row_count": 15000
                }
        
        return None


async def example_basic_usage():
    """Example of basic usage without MCP integration."""
    print("📊 Basic Usage Example (Without MCP)")
    print("-" * 50)
    
    # Initialize without MCP client for basic functionality
    kb = SchemaKnowledgeBase()
    
    # Extract financial entities from natural language
    query_text = "Show me revenue and profit trends for the last quarter"
    entities = kb.extract_financial_entities(query_text)
    
    print(f"Query: '{query_text}'")
    print(f"Extracted {len(entities)} financial entities:")
    
    for entity in entities:
        print(f"  - {entity.entity_value} ({entity.entity_type})")
        print(f"    Confidence: {entity.confidence_score:.2f}")
        print(f"    Database mapping: {entity.database_mapping}")
    
    # Process time period
    time_period = kb.extract_time_period(query_text)
    if time_period:
        print(f"\nTime period: {time_period.period_label}")
        print(f"Period type: {time_period.period_type}")
    
    # Generate query intent
    query_intent = kb.process_query_intent(query_text)
    print(f"\nQuery Intent:")
    print(f"  Metric: {query_intent.metric_type}")
    print(f"  Time period: {query_intent.time_period}")
    print(f"  Aggregation: {query_intent.aggregation_level}")
    print(f"  Confidence: {query_intent.confidence_score:.2f}")


async def example_mcp_integration():
    """Example of enhanced usage with MCP integration."""
    print("\n🔧 MCP Integration Example")
    print("-" * 50)
    
    # Create mock MCP client
    mcp_client = MCPClientExample()
    
    # Initialize with MCP client for enhanced functionality
    kb = SchemaKnowledgeBase(mcp_client=mcp_client)
    
    # Validate business term mappings against real schema
    print("Validating business term mappings...")
    validation = await kb.validate_business_term_mappings()
    
    print(f"Validation Results:")
    print(f"  Total terms: {validation['total_terms']}")
    print(f"  Valid terms: {validation['valid_terms']}")
    print(f"  Validation rate: {validation['validation_rate']:.1f}%")
    
    if validation['invalid_terms']:
        print(f"  Invalid terms: {validation['invalid_terms']}")
    
    # Get available metrics with live schema validation
    print("\nChecking available metrics...")
    metrics = await kb.get_available_metrics()
    
    available_metrics = [m for m in metrics if m['is_available']]
    print(f"Available metrics: {len(available_metrics)}/{len(metrics)}")
    
    for metric in available_metrics[:3]:  # Show first 3
        print(f"  ✅ {metric['term']}: {metric['description']}")
        print(f"     Table: {metric.get('table', 'N/A')}")
        print(f"     Rows: {metric.get('row_count', 'N/A'):,}")


async def example_dynamic_query_generation():
    """Example of dynamic SQL query generation with schema validation."""
    print("\n🔍 Dynamic Query Generation Example")
    print("-" * 50)
    
    # Create mock MCP client
    mcp_client = MCPClientExample()
    kb = SchemaKnowledgeBase(mcp_client=mcp_client)
    
    # Create a query intent
    query_intent = QueryIntent(
        metric_type="revenue",
        time_period="Q1 2024",
        aggregation_level="monthly",
        filters={"department": "sales"},
        comparison_periods=["vs last year"],
        visualization_hint="line",
        confidence_score=0.95
    )
    
    print("Generating SQL query with schema validation...")
    print(f"Intent: {query_intent.metric_type} for {query_intent.time_period}")
    
    try:
        generated_query = await kb.generate_dynamic_sql_query(query_intent)
        
        print(f"\nGenerated Query:")
        print(f"  Type: {generated_query.query_type}")
        print(f"  Execution time (est.): {generated_query.estimated_execution_time}s")
        print(f"  Supports caching: {generated_query.supports_caching}")
        print(f"  Optimization notes: {len(generated_query.optimization_notes)}")
        
        for note in generated_query.optimization_notes:
            print(f"    - {note}")
        
        if generated_query.sql_query:
            print(f"\n  SQL Preview: {generated_query.sql_query[:100]}...")
        
    except Exception as e:
        print(f"  Error: {e}")


async def example_health_monitoring():
    """Example of system health monitoring."""
    print("\n🏥 Health Monitoring Example")
    print("-" * 50)
    
    # Create mock MCP client
    mcp_client = MCPClientExample()
    kb = SchemaKnowledgeBase(mcp_client=mcp_client)
    
    # Perform health check
    print("Performing system health check...")
    health = await kb.health_check()
    
    print(f"\nHealth Status: {'✅ Healthy' if health['overall_healthy'] else '❌ Issues Detected'}")
    print(f"Check time: {health['timestamp']}")
    
    print(f"\nComponent Status:")
    for component, status in health['components'].items():
        if isinstance(status, dict):
            healthy = status.get('healthy', False)
            symbol = "✅" if healthy else "❌"
            print(f"  {symbol} {component}")
            
            # Show additional details
            for key, value in status.items():
                if key != 'healthy':
                    print(f"      {key}: {value}")
        else:
            print(f"  - {component}: {status}")
    
    if health['warnings']:
        print(f"\n⚠️  Warnings:")
        for warning in health['warnings']:
            print(f"  - {warning}")
    
    if health['errors']:
        print(f"\n❌ Errors:")
        for error in health['errors']:
            print(f"  - {error}")


async def example_cache_management():
    """Example of cache management and statistics."""
    print("\n📊 Cache Management Example")
    print("-" * 50)
    
    # Create mock MCP client
    mcp_client = MCPClientExample()
    kb = SchemaKnowledgeBase(mcp_client=mcp_client)
    
    # Perform some operations to populate cache
    await kb.validate_business_term_mappings()
    await kb.get_available_metrics()
    
    # Get statistics
    stats = kb.get_statistics()
    
    print("System Statistics:")
    print(f"  Term mappings: {stats['term_mappings']['total_terms']}")
    print(f"  Cache hit rate: {stats['cache_performance']['hit_rate']:.1f}%")
    print(f"  Cache hits: {stats['cache_performance']['hits']}")
    print(f"  Cache misses: {stats['cache_performance']['misses']}")
    
    mcp_stats = stats['mcp_integration']
    print(f"\nMCP Integration:")
    print(f"  Adapter available: {mcp_stats['adapter_available']}")
    
    if mcp_stats['cache_stats']:
        cache_stats = mcp_stats['cache_stats']
        print(f"  MCP cache size: {cache_stats['size']}")
        print(f"  MCP cache TTL: {cache_stats['ttl']}s")
    
    # Refresh schema knowledge
    print(f"\nRefreshing schema knowledge...")
    refresh_result = await kb.refresh_schema_knowledge()
    
    if refresh_result['success']:
        print(f"  ✅ Refresh completed")
        print(f"  Available metrics: {refresh_result['available_metrics_count']}")
        print(f"  Validation rate: {refresh_result['validation_results']['validation_rate']:.1f}%")
    else:
        print(f"  ❌ Refresh failed: {refresh_result.get('error')}")


async def main():
    """Run all examples."""
    print("🚀 Schema Knowledge Base - Usage Examples")
    print("=" * 60)
    
    try:
        # Run examples
        await example_basic_usage()
        await example_mcp_integration()
        await example_dynamic_query_generation()
        await example_health_monitoring()
        await example_cache_management()
        
        print("\n" + "=" * 60)
        print("🎉 All examples completed successfully!")
        
        print("\n📋 Key Features Demonstrated:")
        print("  ✅ Basic business logic functionality")
        print("  ✅ MCP integration for dynamic schema")
        print("  ✅ Real-time schema validation")
        print("  ✅ Enhanced query generation")
        print("  ✅ System health monitoring")
        print("  ✅ Cache management and statistics")
        
        print("\n💡 Next Steps:")
        print("  1. Connect to your actual MCP server")
        print("  2. Customize business terms for your use case")
        print("  3. Add your own query templates")
        print("  4. Implement error handling for production")
        print("  5. Set up monitoring and alerting")
        
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
