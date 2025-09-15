#!/usr/bin/env bash

echo "=== Testing Complete MCP to Frontend Flow ==="
echo

echo "1. Testing MCP Server directly..."
curl -s -X POST "http://localhost:8000/tools/llm_generate_sql_tool" \
-H "Content-Type: application/json" \
-d '{"natural_language_query": "Show total revenue for Q1 2024"}' | jq -r '.generated_text'

echo
echo "2. Testing NLP Agent..."
curl -s -X POST "http://localhost:8001/process" \
-H "Content-Type: application/json" \
-d '{
  "query": "Show total revenue for Q1 2024",
  "query_id": "test_flow_001",
  "user_id": "test_user",
  "session_id": "test_session",
  "use_cache": false
}' | jq -r '.sql_query'

echo
echo "3. If NLP agent returns empty SQL, the issue is in the NLP agent MCP integration"
echo "4. If MCP server returns SQL but NLP agent doesn't, the issue is SQL extraction"
