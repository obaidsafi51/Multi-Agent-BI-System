# Project Structure & Organization

## Root Directory Layout

```
ai-cfo-bi-agent/
├── frontend/                 # Next.js frontend application
├── backend/                  # FastAPI gateway service
├── agents/                   # Multi-agent system components
├── config/                   # Configuration files
├── scripts/                  # Development and deployment scripts
├── system-tests/             # End-to-end system tests
├── Project/                  # Project documentation and specs
├── docker-compose.yml        # Container orchestration
├── Makefile                  # Development commands
└── .env.example             # Environment template
```

## Frontend Structure (`frontend/`)

- **Framework**: Next.js 15+ with App Router
- **Components**: Organized by feature with co-located tests
  - `src/components/ui/` - shadcn/ui base components
  - `src/components/bento-grid/` - Dashboard grid system
  - `src/components/charts/` - Visualization components
  - `src/components/chat/` - Chat interface
- **Types**: TypeScript definitions in `src/types/`
- **Hooks**: Custom React hooks in `src/hooks/`
- **Lib**: Utilities and API clients in `src/lib/`

## Backend Structure (`backend/`)

- **Framework**: FastAPI with async/await patterns
- **Models**: Pydantic models organized by domain
  - `models/core.py` - Core business entities
  - `models/ui.py` - UI-specific models
  - `models/user.py` - User and personalization models
- **Database**: Connection management and schema
- **Communication**: Agent communication protocols
- **Tests**: Comprehensive test suite with pytest

## Agent Architecture (`agents/`)

Each agent follows consistent structure:

```
agents/[agent-name]/
├── src/                     # Source code
│   ├── __init__.py
│   ├── agent.py            # Main agent class
│   └── [domain-modules]/   # Domain-specific modules
├── tests/                  # Agent-specific tests
├── main.py                 # Agent entry point
├── Dockerfile              # Container definition
└── pyproject.toml          # Dependencies with uv
```

### Agent Responsibilities

- **nlp-agent**: KIMI integration, query parsing, intent extraction
- **data-agent**: TiDB operations, query optimization, caching
- **viz-agent**: Chart generation, visualization selection
- **personal-agent**: User preferences, ML-based recommendations

## Configuration Management

- **Environment**: `.env` files for secrets and configuration
- **Schema Knowledge**: JSON configs in `backend/schema_knowledge/config/`
  - `business_terms.json` - CFO terminology mappings
  - `query_templates.json` - SQL template definitions
  - `metrics_config.json` - Financial metric definitions
- **Agent Config**: Individual agent configurations

## Database Schema (`config/`)

- **TiDB Cloud**: MySQL-compatible distributed database
- **Schema**: Financial data tables with time-series support
- **Migrations**: Database schema versioning

## Development Scripts (`scripts/`)

- `setup-dev.sh` - Complete development environment setup
- `validate-env.sh` - Environment validation
- `troubleshoot.sh` - Diagnostic utilities
- `cleanup.sh` - Development artifact cleanup

## Testing Strategy

- **Unit Tests**: Individual component testing
- **Integration Tests**: Agent communication testing
- **System Tests**: End-to-end workflow validation
- **Frontend Tests**: Component and hook testing with Vitest

## Code Organization Patterns

- **Separation of Concerns**: Clear boundaries between agents and services
- **Domain-Driven Design**: Business logic organized by financial domains
- **Async/Await**: Consistent async patterns throughout
- **Type Safety**: Strong typing with TypeScript and Pydantic
- **Error Handling**: Graceful degradation and fallback mechanisms

## Communication Patterns

- **HTTP APIs**: RESTful endpoints for synchronous operations
- **WebSockets**: Real-time chat and dashboard updates
- **Message Queues**: Asynchronous agent-to-agent communication
- **Caching**: Redis for session state and query results

## Naming Conventions

- **Files**: snake_case for Python, kebab-case for TypeScript
- **Components**: PascalCase for React components
- **Variables**: camelCase for TypeScript, snake_case for Python
- **Constants**: UPPER_SNAKE_CASE
- **Database**: snake_case for tables and columns
