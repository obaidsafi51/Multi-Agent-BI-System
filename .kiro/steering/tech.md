# Technology Stack & Build System

## Package Management

- **Python**: Uses `uv` for fast dependency resolution and virtual environment management
- **Node.js**: Uses `npm` for frontend package management
- **Docker**: Multi-container setup with Docker Compose

## Backend Stack

- **Framework**: FastAPI with Python 3.11+
- **Database**: TiDB Cloud (MySQL-compatible distributed database)
- **LLM Integration**: KIMI API for natural language processing
- **Message Broker**: RabbitMQ for agent-to-agent communication
- **Caching**: Redis for context management and session storage
- **Task Queue**: Celery for background processing
- **WebSocket**: Built-in FastAPI WebSocket support

## Frontend Stack

- **Framework**: Next.js 15+ with TypeScript
- **UI Components**: shadcn/ui component library with Tailwind CSS
- **Visualization**: Recharts (built on D3.js) integrated with shadcn/ui
- **Layout**: CSS Grid for Bento grid dashboard layout
- **Drag & Drop**: @dnd-kit/core for card rearrangement
- **Animations**: Framer Motion for smooth transitions
- **Real-time**: Socket.io client for WebSocket communication

## Multi-Agent Architecture

- **NLP Agent**: KIMI integration for query understanding
- **Data Agent**: TiDB operations with query optimization
- **Visualization Agent**: Chart generation with Plotly/Python
- **Personalization Agent**: ML-based user preference learning
- **Communication Protocols**: MCP (Redis), A2A (RabbitMQ), ACP (Celery)

## Common Commands

### Development Setup

```bash
# Initial setup
./setup-dev.sh

# Install all Python dependencies
make install-all

# Start all services
make up

# View logs
make logs
```

### Individual Development

```bash
# Frontend development
cd frontend && npm run dev

# Backend development
cd backend && uv run uvicorn main:app --reload

# Agent development
cd agents/[agent-name] && uv sync && uv run python main.py
```

### Testing

```bash
# All tests
make test

# Backend tests
make test-backend

# Agent tests
make test-agents

# Frontend tests
cd frontend && npm test
```

### Docker Operations

```bash
# Build containers
make build

# Fast build with cache
make build-fast

# Clean build
make build-no-cache

# Stop services
make down

# Clean up
make clean
```

## Environment Configuration

- Uses `.env` file for configuration (copy from `.env.example`)
- Required variables: `TIDB_PASSWORD`, `KIMI_API_KEY`, `SECRET_KEY`
- Service ports: Frontend (3000), Backend (8000), Redis (6379), RabbitMQ (5672, 15672)

## Code Quality Tools

- **Python**: Black (formatting), isort (imports), flake8 (linting), mypy (typing)
- **TypeScript**: ESLint with Next.js config
- **Testing**: pytest (Python), Vitest (TypeScript/React)
