#!/usr/bin/env python3
"""
Test SQL cleaning function to debug the USE statement removal issue.
"""

def clean_sql_query(sql_query: str) -> str:
    """
    Clean SQL query to remove patterns that cause MCP server issues.
    
    Args:
        sql_query: Original SQL query
        
    Returns:
        Cleaned SQL query
    """
    # Remove USE database statements that cause the dangerous pattern error
    lines = sql_query.strip().split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip USE statements
        if line.upper().startswith('USE '):
            print(f"Removing USE statement: {line}")
            continue
        # Skip empty lines
        if not line:
            continue
        cleaned_lines.append(line)
    
    cleaned_sql = '\n'.join(cleaned_lines)
    
    # Also remove multiple semicolons and clean up
    cleaned_sql = cleaned_sql.replace(';;', ';').strip()
    if cleaned_sql.endswith(';'):
        cleaned_sql = cleaned_sql[:-1]  # Remove trailing semicolon
    
    return cleaned_sql

# Test with the exact SQL from the logs
test_sql = """USE `Retail_Business_Agentic_AI`;
SELECT SUM(`total_revenue`) AS `total_revenue_2024` FROM `revenue` WHERE YEAR(`date`) = 2024;"""

print("Original SQL:")
print(repr(test_sql))
print("\nOriginal SQL (pretty):")
print(test_sql)

cleaned = clean_sql_query(test_sql)

print("\nCleaned SQL:")
print(repr(cleaned))
print("\nCleaned SQL (pretty):")
print(cleaned)

print(f"\nOriginal contains 'USE '? {';' in test_sql and 'USE ' in test_sql}")
print(f"Cleaned contains 'USE '? {';' in cleaned and 'USE ' in cleaned}")
