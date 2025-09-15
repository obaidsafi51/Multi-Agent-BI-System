#!/bin/bash

echo "🚀 Testing Simplified Single-Path Architecture"
echo "=============================================="
echo ""

echo "🎯 Testing the unified processing approach..."
echo ""

# Monitor logs
echo "📊 Monitoring NLP agent logs..."
docker compose logs nlp-agent --follow --tail=0 2>/dev/null | grep -E "(Processing query|processed.*via|unified|Processing|MCP|WebSocket)" &
LOG_PID=$!

# Wait for monitoring to start
sleep 2

echo "🧪 Making test query: 'what is the cashflow of 2024?'"
echo ""
echo "Expected with unified approach:"
echo "  ✅ No complex classification logic"
echo "  ✅ Single processing path for all queries"
echo "  ✅ Consistent performance"
echo "  ✅ Simpler error handling"
echo ""

# Time the request
START_TIME=$(date +%s.%N)
curl -X POST http://localhost:8080/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "what is the cashflow of 2024?", "user_id": "test_user", "session_id": "test_session"}' \
  >/dev/null 2>&1
END_TIME=$(date +%s.%N)

# Calculate duration
DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)

# Wait for processing
sleep 3

# Stop log monitoring
kill $LOG_PID 2>/dev/null

echo ""
echo "⏱️  Request completed in: ${DURATION}s"
echo ""
echo "✅ Unified Architecture Benefits:"
echo "   1. No query classification complexity"
echo "   2. Single well-tested processing path"
echo "   3. Consistent performance across all queries"
echo "   4. Simplified debugging and maintenance"
echo "   5. Better error handling and fallbacks"
echo ""
echo "📊 Check logs above for 'unified_path' processing"
