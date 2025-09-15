#!/bin/bash
# Test WebSocket Implementation in Production Mode

echo "=== WebSocket Implementation Test ==="
echo "Date: $(date)"
echo ""

# Step 1: Build frontend in production mode
echo "1. Building frontend in production mode..."
cd "/home/obaidsafi31/Desktop/Agentic BI "
docker compose build frontend --no-cache

if [ $? -eq 0 ]; then
    echo "✅ Frontend build successful"
else
    echo "❌ Frontend build failed"
    exit 1
fi

# Step 2: Restart frontend container
echo ""
echo "2. Restarting frontend container..."
docker compose restart frontend

if [ $? -eq 0 ]; then
    echo "✅ Frontend restart successful"
else
    echo "❌ Frontend restart failed"
    exit 1
fi

# Step 3: Wait and check for automatic connections (should be none)
echo ""
echo "3. Checking for automatic WebSocket connections (expecting none)..."
sleep 15

WEBSOCKET_LOGS=$(docker compose logs backend --since=15s | grep -i websocket)

if [ -z "$WEBSOCKET_LOGS" ]; then
    echo "✅ No automatic WebSocket connections detected"
else
    echo "⚠️  WebSocket connections detected:"
    echo "$WEBSOCKET_LOGS"
fi

# Step 4: Check container health
echo ""
echo "4. Checking container health..."
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# Step 5: Test frontend accessibility
echo ""
echo "5. Testing frontend accessibility..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)

if [ "$FRONTEND_STATUS" = "200" ]; then
    echo "✅ Frontend accessible at http://localhost:3000"
else
    echo "⚠️  Frontend returned status: $FRONTEND_STATUS"
fi

echo ""
echo "=== Test Complete ==="
echo ""
echo "Manual Testing Instructions:"
echo "1. Open http://localhost:3000 in browser"
echo "2. Look for WebSocket connection control button in the header"
echo "3. Click 'Connect' to establish WebSocket connection"
echo "4. Verify connection status changes to 'Connected'"
echo "5. Check backend logs for single connection establishment"
echo "6. Click 'Disconnect' to close connection"
echo "7. Verify clean disconnection without reconnection attempts"
echo ""
echo "Expected behavior:"
echo "- No automatic connections on page load"
echo "- Manual connect/disconnect works properly"
echo "- No connection storms or duplicate connections"
echo "- Proper React Strict Mode handling"
