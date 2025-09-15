# Agentic BI

A sophisticated multi-agent system that provides natural language querying capabilities with dynamic dashboard visualization, designed for comprehensive business intelligence analysis.

## 🏗️ Architecture

This system implements a microservices architecture with the following components:

- **Frontend**: Next.js with TypeScript and shadcn/ui for modern, responsive UI
- **Backend**: Python-based orchestration layer with WebSocket support for real-time communication
- **Multi-Agent System**: Specialized agents for NLP, Data, and Visualization
- **Communication**: MCP (Model Context Protocol), WebSockets, and HTTP
- **Database**: TiDB for scalable data storage

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ and [uv](https://docs.astral.sh/uv/) (for local Python development)

### Setup and Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/obaidsafi51/Multi-Agent-BI-System.git
   cd "Agentic BI"
   ```

2. **Configure environment variables**:

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Build and start services**:

   ```bash
   docker compose up -d
   ```

   This will build and start all containers defined in the docker-compose.yml file.

4. **Access the application**:

   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - TiDB MCP Server: http://localhost:8080
   - TiDB Dashboard: http://localhost:8080/dashboard

5. **Check service status**:

   ```bash
   docker compose ps
   ```

6. **View logs**:

   ```bash
   docker compose logs -f [service-name]
   ```

## 📁 Project Structure

```
Agentic BI/
├── frontend/                # Next.js frontend with UI components
├── backend/                # Python-based orchestration backend
├── agents/
│   ├── nlp-agent/         # Natural Language Processing Agent
│   ├── data-agent/        # Data Query and Processing Agent
│   └── viz-agent/         # Visualization Generation Agent
├── tidb-mcp-server/       # TiDB Model Context Protocol Server
├── shared/                # Shared code and models
├── config/                # Configuration files
└── docker-compose.yml     # Container orchestration
```

## 🛠️ Development Workflow

### Full System

The easiest way to run the complete system is with Docker Compose:

```bash
# Start all services
docker compose up -d

# Restart a specific service
docker compose restart [service-name]

# View logs from all services
docker compose logs -f

# View logs from a specific service
docker compose logs -f [service-name]

# Stop all services
docker compose down
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:3000.

### Backend Development

```bash
cd backend
uv sync  # Install dependencies
python main.py
```

The backend will be available at http://localhost:8000.

### Agent Development

Each agent can be developed independently:

```bash
cd agents/[agent-name]
uv sync  # Install dependencies
python main.py
```

## 🔄 System Components

### NLP Agent

The NLP Agent processes natural language queries, extracts intent and entities, and coordinates with the Data and Viz agents to produce results.

Configuration:
- Environment variables in `.env`
- Performance settings in `performance_config.py`

Start independently:
```bash
cd agents/nlp-agent
python main_optimized.py
```

### Data Agent

The Data Agent handles database connections, query generation, validation, and execution.

Configuration:
- Database connection in `.env`

Start independently:
```bash
cd agents/data-agent
python main.py
```

### Viz Agent

The Viz Agent generates visualizations based on data and query intent.

Configuration:
- Styling and chart options in environment variables

Start independently:
```bash
cd agents/viz-agent
python main.py
```

### TiDB MCP Server

The TiDB MCP Server provides schema intelligence and query validation through the Model Context Protocol.

Configuration:
- TiDB connection settings in `.env`

Start independently:
```bash
cd tidb-mcp-server
python main.py
```

### Backend Orchestration

The Backend coordinates communication between agents and manages WebSocket connections with the frontend.

Configuration:
- Connection settings in `.env`
- Logging in `logging_config.yaml`

Start independently:
```bash
cd backend
python main.py
```

## 📊 Features

- **Natural Language Querying**: Ask business questions in plain English
- **Dynamic Visualization**: Automatic chart generation based on query context
- **Interactive Dashboards**: Customizable visualization layouts
- **Real-time Updates**: WebSocket-based live data streaming
- **Schema Intelligence**: Smart query validation and schema awareness
- **Multi-Agent Architecture**: Specialized agents for different aspects of BI
- **Performance Optimization**: Caching and parallel processing

## 🔧 Configuration

### Environment Variables

Key environment variables to configure:

```
# Database
TIDB_HOST=tidb
TIDB_PORT=4000
TIDB_USER=root
TIDB_PASSWORD=your_password
TIDB_DATABASE=your_database

# API Keys
LLM_API_KEY=your_llm_api_key

# Ports
BACKEND_PORT=8000
FRONTEND_PORT=3000
NLP_AGENT_PORT=8001
DATA_AGENT_PORT=8002
VIZ_AGENT_PORT=8003
MCP_SERVER_PORT=8080

# WebSockets
WEBSOCKET_PROTOCOL=ws
WEBSOCKET_HOST=localhost
```

### Service Ports

- Frontend: 3000
- Backend: 8000
- NLP Agent: 8001
- Data Agent: 8002
- Viz Agent: 8003
- TiDB MCP Server: 8080
- TiDB: 4000

## 🛠️ Advanced Configuration

### Customizing WebSocket Settings

Edit `backend/websocket_agent_manager.py` to adjust WebSocket behavior:

```python
# Configuration options
RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 1.5  # seconds
PING_INTERVAL = 30  # seconds
```

### Optimizing NLP Agent Performance

Edit `agents/nlp-agent/performance_config.py`:

```python
# Adjust cache size and optimization level
CACHE_SIZE = 2000
SEMANTIC_SIMILARITY_THRESHOLD = 0.85
PARALLEL_PROCESSING = True
```

### Customizing Visualization Styling

The Viz Agent supports different styling options:

```
VIZ_COLOR_SCHEME=professional
VIZ_INTERACTIVE_FEATURES=true
VIZ_DEFAULT_CHART_TYPE=auto
```

## 🐛 Troubleshooting

### Common Issues

1. **Connection errors**: Ensure all services are running with `docker compose ps`

2. **Database connection issues**:
   - Check TiDB is running: `docker compose logs tidb`
   - Verify database credentials in `.env`

3. **WebSocket connection errors**:
   - Check WebSocket server is running: `docker compose logs backend`
   - Verify WebSocket settings in frontend configuration

4. **Visualization errors**:
   - Ensure data format is correct
   - Check Viz Agent logs: `docker compose logs viz-agent`

5. **Slow performance**:
   - Check NLP Agent cache settings
   - Verify database has proper indexes

### Diagnostics

For a complete system health check:

```bash
docker compose ps
docker compose logs -f
```

## 📝 API Documentation

### Key Endpoints

- **Frontend**: http://localhost:3000
  - Web interface for querying and visualization

- **Backend**:
  - `GET /health` - System health check
  - `POST /query` - Submit a natural language query
  - `WS /ws` - WebSocket connection endpoint

- **NLP Agent**:
  - `POST /process` - Process natural language query
  - `GET /health` - Agent health status

- **TiDB MCP Server**:
  - `WS /ws` - WebSocket endpoint for MCP
  - `GET /health` - Server health status

## 🧪 Testing

```bash
# Frontend tests
cd frontend && npm test

# Backend tests
cd backend && pytest

# Agent tests
cd agents/[agent-name] && pytest

# End-to-end tests
cd system-tests && pytest
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.
