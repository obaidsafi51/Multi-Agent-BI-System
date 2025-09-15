#!/bin/bash

echo "🧪 Testing Viz-Agent Dashboard Integration"
echo "=========================================="

# Configuration
BACKEND_URL="http://localhost:8000"
VIZ_AGENT_URL="http://localhost:8003"
SESSION_ID="test_session_$(date +%s)"
USER_ID="test_user"

echo "📋 Test Configuration:"
echo "  Backend URL: $BACKEND_URL"
echo "  Viz Agent URL: $VIZ_AGENT_URL"
echo "  Session ID: $SESSION_ID"
echo "  User ID: $USER_ID"
echo ""

# Test 1: Check Viz Agent Health
echo "🔍 Test 1: Checking Viz Agent Health..."
curl -s "$VIZ_AGENT_URL/health" | jq '.' || echo "❌ Viz Agent health check failed"
echo ""

# Test 2: Check Dashboard Stats
echo "🔍 Test 2: Checking Dashboard Integration Stats..."
curl -s "$VIZ_AGENT_URL/dashboard/stats" | jq '.' || echo "❌ Dashboard stats check failed"
echo ""

# Test 3: Select Database (Required for queries)
echo "🔍 Test 3: Selecting Database..."
DATABASE_SELECTION=$(curl -s -X POST "$BACKEND_URL/api/database/select" \
  -H "Content-Type: application/json" \
  -d "{
    \"database_name\": \"Agentic_BI\",
    \"session_id\": \"$SESSION_ID\"
  }")

echo "Database Selection Response:"
echo "$DATABASE_SELECTION" | jq '.'

if echo "$DATABASE_SELECTION" | jq -e '.success' > /dev/null; then
  echo "✅ Database selected successfully"
else
  echo "❌ Database selection failed"
  exit 1
fi
echo ""

# Test 4: Send Query to Backend (Should trigger Viz Agent)
echo "🔍 Test 4: Sending Query to Backend (should trigger Viz Agent)..."
QUERY_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/query" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"Show me the revenue trends for the last 6 months\",
    \"session_id\": \"$SESSION_ID\",
    \"user_id\": \"$USER_ID\",
    \"context\": {
      \"source\": \"dashboard_integration_test\"
    }
  }")

echo "Query Response:"
echo "$QUERY_RESPONSE" | jq '.'

if echo "$QUERY_RESPONSE" | jq -e '.result' > /dev/null; then
  echo "✅ Query processed successfully"
else
  echo "❌ Query processing failed"
  echo "$QUERY_RESPONSE" | jq '.error // empty'
fi
echo ""

# Test 5: Check Dashboard Cards
echo "🔍 Test 5: Checking Dashboard Cards Generated..."
sleep 2  # Give viz-agent time to process

DASHBOARD_CARDS=$(curl -s "$VIZ_AGENT_URL/dashboard/cards/$SESSION_ID")
echo "Dashboard Cards Response:"
echo "$DASHBOARD_CARDS" | jq '.'

if echo "$DASHBOARD_CARDS" | jq -e '.success' > /dev/null; then
  CARD_COUNT=$(echo "$DASHBOARD_CARDS" | jq '.total_cards')
  echo "✅ Found $CARD_COUNT dashboard cards"
  
  # Show card details
  echo "📊 Card Details:"
  echo "$DASHBOARD_CARDS" | jq '.cards[] | {id: .id, type: .card_type, title: .title, size: .size}'
else
  echo "❌ Failed to get dashboard cards"
fi
echo ""

# Test 6: Test Direct Dashboard Visualization
echo "🔍 Test 6: Testing Direct Dashboard Visualization..."
DIRECT_VIZ=$(curl -s -X POST "$VIZ_AGENT_URL/dashboard/visualize" \
  -H "Content-Type: application/json" \
  -d "{
    \"data\": [
      {\"month\": \"2025-01\", \"revenue\": 120000},
      {\"month\": \"2025-02\", \"revenue\": 135000},
      {\"month\": \"2025-03\", \"revenue\": 118000}
    ],
    \"columns\": [\"month\", \"revenue\"],
    \"query\": \"Monthly revenue trend\",
    \"query_id\": \"test_direct_viz_$(date +%s)\",
    \"session_id\": \"$SESSION_ID\",
    \"user_id\": \"$USER_ID\",
    \"intent\": {
      \"metric_type\": \"revenue\",
      \"time_period\": \"monthly\"
    }
  }")

echo "Direct Visualization Response:"
echo "$DIRECT_VIZ" | jq '.'

if echo "$DIRECT_VIZ" | jq -e '.success' > /dev/null; then
  echo "✅ Direct dashboard visualization successful"
  if echo "$DIRECT_VIZ" | jq -e '.dashboard_updated' > /dev/null; then
    echo "✅ Dashboard was updated"
  else
    echo "⚠️  Dashboard was not updated"
  fi
else
  echo "❌ Direct dashboard visualization failed"
fi
echo ""

# Test 7: Check Updated Dashboard Cards
echo "🔍 Test 7: Checking Updated Dashboard Cards..."
sleep 1  # Give viz-agent time to process

UPDATED_CARDS=$(curl -s "$VIZ_AGENT_URL/dashboard/cards/$SESSION_ID")
if echo "$UPDATED_CARDS" | jq -e '.success' > /dev/null; then
  NEW_CARD_COUNT=$(echo "$UPDATED_CARDS" | jq '.total_cards')
  echo "✅ Found $NEW_CARD_COUNT dashboard cards (updated)"
  
  # Show latest card
  echo "📊 Latest Card:"
  echo "$UPDATED_CARDS" | jq '.cards[-1] | {id: .id, type: .card_type, title: .title, created_at: .created_at}'
else
  echo "❌ Failed to get updated dashboard cards"
fi
echo ""

# Test 8: Test WebSocket Connection to Viz Agent
echo "🔍 Test 8: Testing WebSocket Connection to Viz Agent..."
# Note: This would require a WebSocket client, so we'll just check if the port is open
if command -v nc &> /dev/null; then
  if nc -z localhost 8013; then
    echo "✅ Viz Agent WebSocket port (8013) is accessible"
  else
    echo "❌ Viz Agent WebSocket port (8013) is not accessible"
  fi
else
  echo "⚠️  nc not available, skipping WebSocket port check"
fi
echo ""

# Test 9: Cleanup
echo "🧹 Test 9: Cleaning up test data..."
CLEANUP_RESPONSE=$(curl -s -X DELETE "$VIZ_AGENT_URL/dashboard/cards/$SESSION_ID")
if echo "$CLEANUP_RESPONSE" | jq -e '.success' > /dev/null; then
  echo "✅ Dashboard cards cleaned up"
else
  echo "⚠️  Failed to cleanup dashboard cards"
fi
echo ""

# Summary
echo "📋 Test Summary"
echo "==============="
echo "Session ID: $SESSION_ID"
echo "Test completed at: $(date)"
echo ""
echo "Next Steps:"
echo "1. Check the frontend dashboard to see if cards appear"
echo "2. Try sending queries through the UI"
echo "3. Verify that visualizations are displayed properly"
echo "4. Test the real-time updates when new queries are sent"
echo ""
echo "🎯 Key Integration Points Tested:"
echo "   ✅ Viz Agent health and dashboard stats"
echo "   ✅ Database selection and session management"
echo "   ✅ Backend query processing with viz-agent integration"
echo "   ✅ Dashboard card generation and retrieval"
echo "   ✅ Direct dashboard visualization endpoint"
echo "   ✅ Dashboard card cleanup"
echo ""
echo "💡 To see the dashboard integration in action:"
echo "   1. Open the frontend: http://localhost:3000"
echo "   2. Select the 'Agentic_BI' database"
echo "   3. Ask questions like 'Show me revenue trends'"
echo "   4. Watch as cards appear on the dashboard automatically!"
