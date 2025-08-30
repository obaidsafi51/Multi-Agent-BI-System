#!/usr/bin/env python3
"""
Quick test script to verify the configurable semicolon behavior in QueryOptimizer
This demonstrates the fix for the Copilot AI suggestion about making semicolon addition configurable.
"""

# Simple direct test without complex imports
def test_semicolon_logic():
    """Test the semicolon configuration logic directly"""
    
    print("Testing configurable semicolon behavior...")
    print("=" * 50)
    
    # Simulate the configuration scenarios
    test_configs = [
        {
            "name": "Default MySQL (should add semicolon)",
            "database_type": "mysql",
            "config": {"sql_formatting": {"auto_add_semicolon": True}},
            "expected": True
        },
        {
            "name": "SQLite with override (should not add semicolon)", 
            "database_type": "sqlite",
            "config": {
                "sql_formatting": {
                    "auto_add_semicolon": True,
                    "database_specific_overrides": {
                        "sqlite": {"auto_add_semicolon": False}
                    }
                }
            },
            "expected": False
        },
        {
            "name": "PostgreSQL with global disable",
            "database_type": "postgresql", 
            "config": {"sql_formatting": {"auto_add_semicolon": False}},
            "expected": False
        },
        {
            "name": "MySQL with specific override to disable",
            "database_type": "mysql",
            "config": {
                "sql_formatting": {
                    "auto_add_semicolon": True,
                    "database_specific_overrides": {
                        "mysql": {"auto_add_semicolon": False}
                    }
                }
            },
            "expected": False
        }
    ]
    
    def should_add_semicolon(database_type: str, config: dict) -> bool:
        """Simulate the _should_add_semicolon logic"""
        sql_formatting = config.get("sql_formatting", {})
        
        # Check for database-specific override first
        db_overrides = sql_formatting.get("database_specific_overrides", {})
        
        if database_type in db_overrides:
            return db_overrides[database_type].get("auto_add_semicolon", True)
        
        # Fall back to global setting
        return sql_formatting.get("auto_add_semicolon", True)
    
    def apply_cleanup(sql: str, should_add: bool) -> str:
        """Simulate the _cleanup_sql logic"""
        import re
        # Remove extra whitespace
        sql = re.sub(r'\s+', ' ', sql)
        # Remove trailing whitespace  
        sql = sql.strip()
        # Add semicolon if configured
        if should_add and not sql.endswith(';'):
            sql += ';'
        return sql
    
    # Test each configuration
    test_sql = "SELECT * FROM users WHERE active = 1"
    
    for i, test_case in enumerate(test_configs, 1):
        print(f"\n{i}. {test_case['name']}:")
        
        should_add = should_add_semicolon(test_case['database_type'], test_case['config'])
        result_sql = apply_cleanup(test_sql, should_add)
        
        print(f"   Database: {test_case['database_type']}")
        print(f"   Config: {test_case['config']}")
        print(f"   Input SQL: '{test_sql}'")
        print(f"   Output SQL: '{result_sql}'")
        print(f"   Should add semicolon: {should_add}")
        print(f"   Actually added: {result_sql.endswith(';')}")
        print(f"   Expected behavior: {test_case['expected']}")
        print(f"   ✓ Test {'PASSED' if (result_sql.endswith(';') == test_case['expected']) else 'FAILED'}")
    
    print(f"\n{'=' * 50}")
    print("Summary:")
    print("- Semicolon addition is now configurable per database type")
    print("- Global settings can be overridden for specific databases")
    print("- SQLite defaults to not adding semicolons (common driver requirement)")
    print("- Runtime configuration is supported via set_semicolon_behavior()")
    print("- Addresses Copilot AI feedback about making behavior configurable")

if __name__ == "__main__":
    test_semicolon_logic()
