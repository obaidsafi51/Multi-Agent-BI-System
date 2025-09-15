#!/bin/bash

echo "🎯 Testing Query Classification Fix"
echo "=================================="
echo ""

echo "📋 Making test query: 'what is the cashflow of 2024?'"
echo "Expected: Should use STANDARD_PATH (not FAST_PATH)"
echo ""

# Start monitoring logs in background
echo "📊 Monitoring NLP agent logs..."
docker compose logs nlp-agent --follow --tail=0 | grep -E "(classified|processing|path|Processing|Query)" &
LOG_PID=$!

# Wait a moment for log monitoring to start
sleep 2

# Make the query
echo "🚀 Sending query..."
curl -X POST http://localhost:8080/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "what is the cashflow of 2024?", "user_id": "test_user", "session_id": "test_session"}' \
  >/dev/null 2>&1

# Wait for processing
sleep 3

# Stop log monitoring
kill $LOG_PID 2>/dev/null

echo ""
echo "✅ Test completed! Check the logs above for the processing path."
echo "If you see 'standard_path' instead of 'fast_path', the fix is working!"
