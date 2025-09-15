# TiDB SQL Generation Improvements

## Problem Identified

The NLP agent was generating SQL queries with syntax issues for TiDB Cloud:

### Issues:

1. **Missing USE statement** for database context
2. **Improper backtick usage** for table/column identifiers
3. **GROUP BY aggregation problems** (grouping by columns used in MAX())
4. **Generic MySQL syntax** instead of TiDB-specific patterns

### Example Problem Query:

```sql
SELECT
  DATE_FORMAT(date, '%Y-%m') AS month,
  SUM(cash_in) AS total_cash_in,
  SUM(cash_out) AS total_cash_out,
  SUM(net_cashflow) AS net_cashflow,
  category,
  MAX(description) AS description  -- ❌ Problem: MAX(desc) with GROUP BY desc
FROM cashflow
WHERE YEAR(date) = 2024
GROUP BY DATE_FORMAT(date, '%Y-%m'), category, description  -- ❌ Redundant
ORDER BY month;
```

## Solution Implemented

### 1. Updated MCP Server SQL Generation Prompt

**File**: `/tidb-mcp-server/src/tidb_mcp_server/llm_tools.py`

**Enhanced System Prompt:**

```python
system_prompt = """You are a SQL expert specializing in TiDB Cloud databases.

CRITICAL RULES:
1. Only generate SELECT queries (no INSERT, UPDATE, DELETE, DROP, etc.)
2. Always start with USE statement: USE database_name;
3. Use backticks around table and column names: `table_name`.`column_name`
4. Use proper TiDB/MySQL syntax with proper aggregation rules
5. When using GROUP BY, ensure all non-aggregated columns in SELECT are in GROUP BY
6. Use appropriate date functions: YEAR(), MONTH(), DATE_FORMAT()
7. For time-based queries, use DATE_FORMAT for proper grouping
8. Return clean, executable SQL without markdown formatting

TiDB SYNTAX EXAMPLES:
- USE `database_name`;
- SELECT `column1`, SUM(`column2`) FROM `table` WHERE YEAR(`date_column`) = 2024 GROUP BY `column1`;
- DATE_FORMAT(`date_column`, '%Y-%m') for month grouping
- Always use backticks for identifiers"""
```

### 2. Enhanced User Prompt Requirements

```python
user_prompt = f"""Convert this question to SQL: {natural_language_query}

Requirements:
1. Include USE statement for the database
2. Use proper backtick syntax for all identifiers
3. Ensure proper GROUP BY clauses for aggregations
4. Use appropriate date functions for time-based queries
5. Return only the SQL query, no explanations or markdown"""
```

## Expected Working Query Output

For "show me the cashflow of 2024", the improved system should now generate:

### Option 1: Monthly Summary (Recommended)

```sql
USE `Retail_Business_Agentic_AI`;

SELECT
  DATE_FORMAT(`date`, '%Y-%m') AS `month`,
  SUM(`cash_in`) AS `total_cash_in`,
  SUM(`cash_out`) AS `total_cash_out`,
  SUM(`net_cashflow`) AS `net_cashflow`
FROM
  `cashflow`
WHERE
  YEAR(`date`) = 2024
GROUP BY
  DATE_FORMAT(`date`, '%Y-%m')
ORDER BY
  `month`;
```

### Option 2: Category Breakdown

```sql
USE `Retail_Business_Agentic_AI`;

SELECT
  `category`,
  SUM(`cash_in`) AS `total_cash_in`,
  SUM(`cash_out`) AS `total_cash_out`,
  SUM(`net_cashflow`) AS `net_cashflow`,
  COUNT(*) AS `transaction_count`
FROM
  `cashflow`
WHERE
  YEAR(`date`) = 2024
GROUP BY
  `category`
ORDER BY
  `net_cashflow` DESC;
```

## Key Improvements

### ✅ TiDB Compliance

- Proper `USE database_name;` statements
- Backtick usage for all identifiers
- Clean, executable SQL output

### ✅ Aggregation Logic

- Proper GROUP BY clauses
- No redundant MAX() functions
- Logical grouping levels

### ✅ Date Handling

- Proper DATE_FORMAT() usage
- YEAR() function for filtering
- Consistent time-based grouping

### ✅ Error Prevention

- Clear aggregation rules
- Identifier consistency
- Syntax validation guidance

## Services Restarted

- ✅ TiDB MCP Server (to apply new prompts)
- ✅ NLP Agent (to connect to updated MCP server)

## Testing Recommendation

Try the cashflow query again:

- Query: "show me the cashflow of 2024"
- Expected: Proper TiDB-compliant SQL with USE statement and backticks
- Result: Should execute successfully in TiDB Cloud

The system will now generate much more reliable and executable SQL queries for TiDB Cloud databases.
