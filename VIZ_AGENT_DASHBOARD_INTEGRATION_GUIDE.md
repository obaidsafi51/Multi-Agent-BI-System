# Viz-Agent Dashboard Integration System

## Overview

The viz-agent has been enhanced with a comprehensive dashboard integration system that enables real-time visualization display on the frontend dashboard. This system bridges the gap between data visualization generation and dashboard presentation.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Frontend      │    │     Backend      │    │    Viz-Agent        │
│   Dashboard     │◄───┤   WebSocket      │◄───┤   WebSocket Server  │
│                 │    │   Agent Manager  │    │                     │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
         │                        │                         │
         │                        │                         │
         ▼                        ▼                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│  BentoGrid      │    │  Query           │    │  Dashboard          │
│  Cards          │    │  Processing      │    │  Integration        │
│                 │    │                  │    │  Manager            │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
```

## Key Components

### 1. Dashboard Integration Manager (`src/dashboard_integration.py`)

**Purpose**: Central component that manages dashboard card creation, session tracking, and frontend communication.

**Key Features**:

- **Real-time Card Generation**: Converts visualization results into dashboard-ready cards
- **Session Management**: Tracks cards per user session
- **Intelligent Positioning**: Automatically determines optimal card placement
- **Smart Sizing**: Dynamically sizes cards based on content type and data volume
- **Error Handling**: Creates fallback error cards when visualization fails

**Main Methods**:

```python
async def create_visualization_card(viz_response, session_id, user_id, query_context)
async def send_dashboard_update(update_type, session_id, user_id, cards, query_id)
async def process_query_for_dashboard(data, columns, query, query_id, session_id, user_id, intent)
```

### 2. Enhanced WebSocket Server (`websocket_server.py`)

**Updates**:

- Integrated with dashboard manager
- Enhanced `handle_viz_query` method to create dashboard cards
- Real-time dashboard update notifications
- Session-aware processing

**Key Enhancement**:

```python
async def handle_viz_query(self, websocket, data, client_id, message_id):
    # Extract session and user context
    session_id = data.get("session_id", "default_session")
    user_id = data.get("user_id", "anonymous")

    # Process query and create dashboard visualization
    dashboard_result = await dashboard_integration_manager.process_query_for_dashboard(...)

    # Send response with dashboard update information
    response = {
        "success": True,
        "chart_config": dashboard_result.get("chart_config"),
        "dashboard_updated": True
    }
```

### 3. New HTTP Endpoints (`main.py`)

**New Endpoints**:

1. **`POST /dashboard/visualize`** - Create dashboard-specific visualizations
2. **`GET /dashboard/cards/{session_id}`** - Retrieve all cards for a session
3. **`DELETE /dashboard/cards/{session_id}`** - Clear session cards
4. **`GET /dashboard/stats`** - Get dashboard integration statistics

### 4. Backend Integration (`backend/main.py`)

**Updates**:

- Enhanced agent communication to include session context
- Updated query processing to pass session_id and user_id to viz-agent
- Improved error handling for dashboard integration

**Key Change**:

```python
viz_result = await send_to_agent_enhanced(
    AgentType.VIZ,
    {
        "type": "viz_query",
        "data": query_data,
        "columns": columns,
        "query": query_request.query,
        "intent": query_intent,
        "query_id": query_id,
        "session_id": session_id,  # ← New: Dashboard integration
        "user_id": user_id,        # ← New: Dashboard integration
        "context": {
            "timestamp": datetime.utcnow().isoformat(),
            "source": "backend_api_websocket",
            "database_context": database_context
        }
    }
)
```

### 5. Frontend Integration (`frontend/src/lib/api.ts`, `frontend/src/hooks/useRealData.ts`)

**New Features**:

- Direct viz-agent dashboard card fetching
- Enhanced card transformation
- Intelligent card sizing
- Real-time dashboard updates

**Key Methods**:

```typescript
async getDashboardCards(sessionId: string): Promise<{
  success: boolean;
  cards: BentoGridCard[];
  total_cards: number;
}>

async clearDashboardCards(sessionId: string): Promise<{
  success: boolean;
  message: string;
}>
```

## Data Flow

### 1. Query Processing Flow

```
1. User asks question in frontend chat
2. Frontend sends query to backend with session_id
3. Backend processes query through NLP → Data → Viz agents
4. Viz-agent receives query with session context
5. Dashboard Integration Manager creates visualization card
6. Card is stored in session-specific card collection
7. Backend receives success response from viz-agent
8. Frontend updates dashboard with new cards
```

### 2. Dashboard Card Structure

```python
@dataclass
class DashboardCard:
    id: str                    # Unique card identifier
    card_type: str            # "chart", "kpi", "table", "insight"
    title: str                # Display title
    position: Dict[str, int]  # {"row": 0, "col": 0}
    size: str                 # "small", "medium_h", "medium_v", "large"
    content: Dict[str, Any]   # Chart data, config, etc.
    metadata: Dict[str, Any]  # Query ID, processing time, etc.
    created_at: str           # ISO timestamp
    updated_at: str           # ISO timestamp
```

### 3. Card Type Mapping

| Data Type     | Visualization    | Card Type | Size       | Use Case         |
| ------------- | ---------------- | --------- | ---------- | ---------------- |
| Single KPI    | Gauge/Metric     | `kpi`     | `small`    | Revenue, Profit  |
| Time Series   | Line/Area Chart  | `chart`   | `medium_h` | Trends over time |
| Categories    | Bar/Column Chart | `chart`   | `medium_v` | Comparisons      |
| Tabular Data  | Table            | `table`   | `large`    | Detailed data    |
| Text/Insights | Text Display     | `insight` | `medium_h` | Analysis results |

## Configuration

### Environment Variables

```bash
# Viz Agent Configuration
VIZ_AGENT_URL=http://viz-agent:8003
VIZ_AGENT_WS_URL=ws://viz-agent:8013
VIZ_AGENT_USE_WS=true

# Frontend Configuration
NEXT_PUBLIC_VIZ_AGENT_URL=http://localhost:8003
```

### Dashboard Settings

```python
# Dashboard Integration Manager Settings
DEFAULT_CARD_SIZE = "medium_h"
MAX_CARDS_PER_SESSION = 50
CARD_CACHE_TTL = 3600  # 1 hour
AUTO_CLEANUP_SESSIONS = True
```

## Testing

### Automated Test Script

Run the comprehensive test:

```bash
./test_viz_dashboard_integration.sh
```

### Manual Testing Steps

1. **Start all services**:

   ```bash
   docker compose up -d
   ```

2. **Open frontend**: http://localhost:3000

3. **Select database**: Choose "Agentic_BI" from database selector

4. **Ask questions**:

   - "Show me revenue trends for the last 6 months"
   - "What are our top performing products?"
   - "Analyze cash flow patterns"

5. **Verify dashboard updates**: Cards should appear automatically

### Test Endpoints Directly

```bash
# Check viz-agent health
curl http://localhost:8003/health

# Get dashboard stats
curl http://localhost:8003/dashboard/stats

# Get session cards
curl http://localhost:8003/dashboard/cards/{session_id}

# Clear session cards
curl -X DELETE http://localhost:8003/dashboard/cards/{session_id}
```

## Troubleshooting

### Common Issues

1. **Cards not appearing on dashboard**:

   - Check viz-agent WebSocket connection: `curl http://localhost:8003/health`
   - Verify session_id is being passed correctly
   - Check browser console for errors

2. **Visualization errors**:

   - Check viz-agent logs: `docker compose logs viz-agent`
   - Verify data format is correct
   - Check dashboard integration manager initialization

3. **Session not found**:
   - Ensure database is selected before sending queries
   - Check session_id consistency between frontend and backend
   - Verify session storage in browser

### Debug Commands

```bash
# Check viz-agent dashboard stats
curl http://localhost:8003/dashboard/stats | jq '.'

# Check backend health
curl http://localhost:8000/health | jq '.'

# Check WebSocket connections
curl http://localhost:8000/api/orchestration/metrics | jq '.websocket_connections'

# View viz-agent logs
docker compose logs viz-agent --tail=50 -f
```

## Performance Considerations

### Optimization Features

1. **Card Caching**: Generated cards are cached per session
2. **Intelligent Sizing**: Cards are sized based on data complexity
3. **Batch Updates**: Multiple cards can be updated in single operations
4. **Session Cleanup**: Old sessions and cards are automatically cleaned up

### Scalability

- **Session Storage**: Cards are stored in memory per session
- **Connection Pooling**: WebSocket connections are pooled and reused
- **Async Processing**: All visualization processing is asynchronous
- **Circuit Breakers**: Built-in circuit breakers prevent cascade failures

## Future Enhancements

### Planned Features

1. **Real-time Collaboration**: Multi-user dashboard sharing
2. **Card Persistence**: Save dashboard layouts to database
3. **Advanced Animations**: Smooth card transitions and updates
4. **Export Capabilities**: Export entire dashboard as PDF/PNG
5. **Custom Card Types**: User-defined card templates
6. **Dashboard Templates**: Pre-built dashboard configurations

### Integration Roadmap

1. **Phase 1**: ✅ Basic dashboard integration (Current)
2. **Phase 2**: Real-time multi-user updates
3. **Phase 3**: Advanced visualization features
4. **Phase 4**: AI-powered dashboard optimization

## Conclusion

The viz-agent dashboard integration system provides a seamless bridge between data visualization generation and frontend dashboard display. It enables:

- **Automatic Dashboard Updates**: Cards appear instantly when queries are processed
- **Intelligent Layout**: Smart positioning and sizing of dashboard cards
- **Session Management**: Per-user dashboard state management
- **Real-time Communication**: WebSocket-based updates for responsive UX
- **Error Resilience**: Graceful handling of visualization failures

This system transforms the viz-agent from a simple chart generator into a comprehensive dashboard orchestration platform, enabling rich, interactive financial dashboards that update in real-time as users explore their data.
