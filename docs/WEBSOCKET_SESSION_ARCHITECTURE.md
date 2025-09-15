# WebSocket Session Management Architecture

## Overview

This document outlines the recommended session management strategy for the AGENT BI system to maintain persistent user connections across page reloads and browser sessions.

## Current State Analysis

- ✅ WebSocket implementation exists for real-time chat
- ✅ JWT authentication for HTTP endpoints
- ✅ Redis integration for session storage
- ⚠️ Session persistence across page reloads not implemented

## Recommended Architecture

### 1. Hybrid Session Management

#### Session Token Strategy

```typescript
interface UserSession {
  sessionId: string; // Persistent session identifier
  userId: string; // User identifier
  jwtToken: string; // JWT for HTTP authentication
  wsConnectionId?: string; // Current WebSocket connection ID
  lastActivity: timestamp; // For session timeout
  preferences: UserPreferences; // Cached user settings
  queryHistory: QueryEntry[]; // Recent query context
}
```

#### Connection Flow

1. **Initial Auth**: User logs in → JWT + Session Token created
2. **WebSocket Connect**: Session token validates → WebSocket connection established
3. **Page Reload**: Session token persists → Auto-reconnect WebSocket
4. **Session Recovery**: Previous query context restored

### 2. Frontend Implementation

#### WebSocket Manager with Reconnection

```typescript
class PersistentWebSocketManager {
  private sessionToken: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1s, exponential backoff

  constructor(sessionToken: string) {
    this.sessionToken = sessionToken;
    this.connect();
    this.setupPageVisibilityHandlers();
  }

  private async connect() {
    try {
      this.ws = new WebSocket(`${WS_URL}/ws/chat/${this.sessionToken}`);
      this.setupEventHandlers();
    } catch (error) {
      this.handleReconnection();
    }
  }

  private handleReconnection() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.reconnectAttempts++;
        this.connect();
      }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts));
    }
  }

  private setupPageVisibilityHandlers() {
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") {
        if (this.ws?.readyState !== WebSocket.OPEN) {
          this.connect();
        }
      }
    });
  }
}
```

#### Local Storage Session Persistence

```typescript
class SessionManager {
  private static SESSION_KEY = "ai_cfo_session";

  static saveSession(session: UserSession) {
    localStorage.setItem(this.SESSION_KEY, JSON.stringify(session));
  }

  static getSession(): UserSession | null {
    const data = localStorage.getItem(this.SESSION_KEY);
    return data ? JSON.parse(data) : null;
  }

  static clearSession() {
    localStorage.removeItem(this.SESSION_KEY);
  }
}
```

### 3. Backend Session Management

#### Enhanced WebSocket Endpoint

```python
@app.websocket("/ws/chat/{session_token}")
async def websocket_endpoint(websocket: WebSocket, session_token: str):
    """WebSocket endpoint with session-based authentication"""

    # Validate session token
    session = await validate_session_token(session_token)
    if not session:
        await websocket.close(code=4001, reason="Invalid session")
        return

    await websocket.accept()

    # Register connection with session
    user_id = session['user_id']
    connection_id = str(uuid.uuid4())

    # Store connection mapping
    websocket_connections[connection_id] = {
        'websocket': websocket,
        'user_id': user_id,
        'session_token': session_token,
        'connected_at': datetime.utcnow(),
        'last_activity': datetime.utcnow()
    }

    # Update session with current connection
    await update_session_connection(session_token, connection_id)

    # Send session restoration data
    await restore_user_session(websocket, session)

    try:
        while True:
            data = await websocket.receive_json()
            await process_websocket_message(connection_id, data)

    except WebSocketDisconnect:
        await cleanup_connection(connection_id)
```

#### Session Token Validation

```python
async def validate_session_token(session_token: str) -> Optional[Dict]:
    """Validate session token and return session data"""
    try:
        # Check Redis for session
        session_data = await redis_client.get(f"session:{session_token}")
        if not session_data:
            return None

        session = json.loads(session_data)

        # Check if session is still valid
        if datetime.fromisoformat(session['expires_at']) < datetime.utcnow():
            await redis_client.delete(f"session:{session_token}")
            return None

        return session

    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return None

async def restore_user_session(websocket: WebSocket, session: Dict):
    """Send session restoration data to client"""
    restoration_data = {
        "type": "session_restored",
        "user_preferences": session.get('preferences', {}),
        "query_history": session.get('query_history', [])[-10:],  # Last 10 queries
        "dashboard_layout": session.get('dashboard_layout'),
        "timestamp": datetime.utcnow().isoformat()
    }

    await websocket.send_json(restoration_data)
```

### 4. Redis Session Storage

```python
class SessionStore:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def create_session(self, user_id: str, jwt_token: str) -> str:
        session_token = str(uuid.uuid4())
        session_data = {
            'user_id': user_id,
            'jwt_token': jwt_token,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(days=7)).isoformat(),
            'preferences': await self.get_user_preferences(user_id),
            'query_history': []
        }

        # Store session with 7-day expiry
        await self.redis.setex(
            f"session:{session_token}",
            604800,  # 7 days
            json.dumps(session_data)
        )

        return session_token

    async def update_query_history(self, session_token: str, query: Dict):
        session_key = f"session:{session_token}"
        session_data = await self.redis.get(session_key)

        if session_data:
            session = json.loads(session_data)
            session['query_history'].append(query)

            # Keep only last 50 queries
            session['query_history'] = session['query_history'][-50:]

            await self.redis.set(session_key, json.dumps(session))
```

## Implementation Benefits

### Performance Improvements

- **Reduced Latency**: Persistent connections eliminate handshake overhead
- **Better Resource Usage**: Connection pooling and reuse
- **Efficient Data Streaming**: Real-time updates without polling

### User Experience

- **Seamless Continuity**: Context preserved across page reloads
- **Faster Interactions**: Immediate response to user actions
- **Offline Resilience**: Automatic reconnection when network restores

### System Reliability

- **Graceful Degradation**: Falls back to HTTP if WebSocket fails
- **Connection Monitoring**: Health checks and automatic recovery
- **Session Persistence**: User state maintained across disconnections

## Migration Strategy

### Phase 1: Session Infrastructure

1. Implement session token system
2. Add Redis session storage
3. Update authentication flow

### Phase 2: Frontend Enhancements

1. Create persistent WebSocket manager
2. Add session restoration logic
3. Implement automatic reconnection

### Phase 3: Full Integration

1. Migrate real-time features to WebSocket
2. Optimize agent communication
3. Add performance monitoring

## Security Considerations

- Session tokens are separate from JWT (defense in depth)
- Session expiry and cleanup mechanisms
- WebSocket origin validation
- Rate limiting on connection attempts
- Secure token storage in HTTP-only cookies or secure local storage
