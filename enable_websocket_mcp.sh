#!/bin/bash

# Enable WebSocket MCP Communication

echo "🔧 Configuring WebSocket MCP Communication..."

# Update environment variables for WebSocket mode
export USE_WEBSOCKET_MCP=true
export TIDB_MCP_SERVER_URL=ws://tidb-mcp-server:8000

# Update docker-compose.yml environment variables
if [ -f "docker-compose.yml" ]; then
    echo "📝 Updating docker-compose.yml with WebSocket configuration..."
    
    # Add environment variable to backend service
    if grep -q "USE_WEBSOCKET_MCP" docker-compose.yml; then
        echo "✅ USE_WEBSOCKET_MCP already configured"
    else
        # Add environment variable to backend service
        sed -i '/backend:/,/^[[:space:]]*[a-zA-Z]/ {
            /environment:/a\
      - USE_WEBSOCKET_MCP=true
        }' docker-compose.yml
        echo "✅ Added USE_WEBSOCKET_MCP=true to backend service"
    fi
fi

echo "🚀 WebSocket MCP configuration complete!"
echo ""
echo "Benefits of WebSocket communication:"
echo "  ✨ Persistent connections (eliminates connection overhead)"
echo "  🚀 Request deduplication (prevents redundant schema calls)"
echo "  💾 Client-side caching (intelligent result caching)"
echo "  📡 Real-time updates (schema change notifications)"
echo "  ⚡ Better performance (especially for frequent schema operations)"
echo ""
echo "To apply changes, restart the services:"
echo "  docker compose down && docker compose up -d"
