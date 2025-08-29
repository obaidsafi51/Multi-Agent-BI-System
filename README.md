# AI-Powered CFO Business Intelligence Agent

A sophisticated multi-agent system that provides natural language querying capabilities with dynamic dashboard visualization, specifically designed for Chief Financial Officers (CFOs).

## 🏗️ Architecture

This system implements a microservices architecture with the following components:

- **Frontend**: Next.js with TypeScript and shadcn/ui for modern, responsive UI
- **Backend**: FastAPI gateway with WebSocket support for real-time communication
- **Multi-Agent System**: Specialized agents for NLP, Data, Visualization, and Personalization
- **Communication**: MCP (Redis), A2A (RabbitMQ), and ACP (Celery) protocols
- **Database**: TiDB for scalable financial data storage

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ and [uv](https://docs.astral.sh/uv/) (for local Python development)

### Development Setup

1. **Clone and setup environment**:

   ```bash
   git clone <repository-url>
   cd ai-cfo-bi-agent
   ./setup-dev.sh
   ```

   The setup script will:

   - Validate Docker installation
   - Create `.env` file from template
   - Validate environment configuration
   - Build and start all services with proper health checks

2. **Configure environment variables** (if not done during setup):

   ```bash
   cp .env.example .env
   # Edit .env with your configuration:
   # - TIDB_PASSWORD: Set a secure password
   # - KIMI_API_KEY: Your KIMI LLM API key
   # - SECRET_KEY: Generate with: openssl rand -hex 32
   ```

3. **Manual start** (alternative to setup script):

   ```bash
   # Validate environment
   ./scripts/validate-env.sh

   # Start services
   docker-compose up -d
   ```

4. **Access the application**:

   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Backend Health: http://localhost:8000/health
   - RabbitMQ Management: http://localhost:15672 (guest/guest)

5. **Troubleshooting**:

   ```bash
   # Run diagnostics
   ./scripts/troubleshoot.sh

   # View logs
   docker-compose logs -f [service-name]
   ```

## 📁 Project Structure

```
ai-cfo-bi-agent/
├── frontend/                 # Next.js frontend with shadcn/ui
├── backend/                  # FastAPI gateway
├── agents/
│   ├── nlp-agent/           # KIMI-powered NLP processing
│   ├── data-agent/          # TiDB data access
│   ├── viz-agent/           # Plotly visualization generation
│   └── personal-agent/      # ML-based personalization
├── config/                  # Configuration files
├── docker-compose.yml       # Container orchestration
├── .env.example            # Environment template
└── setup-dev.sh           # Development setup script
```

## 🛠️ Development

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Backend Development

```bash
cd backend
uv sync                    # Install dependencies
uv run uvicorn main:app --reload
```

### Agent Development

Each agent can be developed independently:

```bash
cd agents/[agent-name]
uv sync                    # Install dependencies
uv run python main.py
```

### Install All Dependencies

```bash
make install-all           # Install all Python dependencies with uv
```

## 📦 Package Management

This project uses [uv](https://docs.astral.sh/uv/) for Python package management, providing:

- **Fast dependency resolution**: 10-100x faster than pip
- **Reproducible builds**: Lock files ensure consistent environments
- **Better dependency management**: Automatic virtual environment handling
- **Modern Python tooling**: Built-in support for pyproject.toml

### Installing uv

```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 🔧 Scripts

- `./setup-dev.sh` - Complete development environment setup
- `./scripts/validate-env.sh` - Validate environment configuration
- `./scripts/troubleshoot.sh` - Diagnose common issues
- `./scripts/cleanup.sh` - Clean up development artifacts (.venv, cache, etc.)
- `./scripts/pre-build.sh` - Prepare environment for clean Docker builds
- `./scripts/wait-for-it.sh` - Wait for services to be ready

## 🐛 Troubleshooting

### Common Issues

1. **Docker build failures**:

   - Run `./scripts/cleanup.sh` to remove .venv directories and artifacts
   - Run `./scripts/troubleshoot.sh` for diagnostics
   - Try `./scripts/pre-build.sh` for clean build preparation

2. **Service startup issues**: Check logs with `docker-compose logs -f [service]`

3. **Environment errors**: Validate with `./scripts/validate-env.sh`

4. **Port conflicts**: Check if ports 3000, 8000, 4000, 5672, 6379 are available

5. **Permission issues with .venv**: Run `sudo ./scripts/cleanup.sh` if needed

### Health Checks

All services include health checks:

- Backend: `curl http://localhost:8000/health`
- Frontend: `curl http://localhost:3000`
- Redis: `docker-compose exec redis redis-cli ping`
- RabbitMQ: `docker-compose exec rabbitmq rabbitmq-diagnostics ping`
- TiDB: `docker-compose exec tidb mysql -h localhost -P 4000 -u root -p -e "SELECT 1"`

# Windows

powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# With pip

pip install uv

````

## 🔧 Configuration

### Environment Variables

- `TIDB_PASSWORD`: TiDB database password
- `KIMI_API_KEY`: KIMI LLM API key for natural language processing
- `SECRET_KEY`: JWT secret key (generate with `openssl rand -hex 32`)

### Service Ports

- Frontend: 3000
- Backend: 8000
- Redis: 6379
- RabbitMQ: 5672 (Management: 15672)
- TiDB: 4000

## 📊 Features

- **Natural Language Queries**: Ask financial questions in plain English
- **Dynamic Visualizations**: Automatic chart generation based on query context
- **Personalized Experience**: ML-powered recommendations and preferences
- **Real-time Updates**: WebSocket-based live data streaming
- **Bento Grid Dashboard**: Modern, customizable dashboard layout
- **Multi-Agent Architecture**: Scalable, fault-tolerant system design

## 🧪 Testing

```bash
# Frontend tests
cd frontend && npm test

# Backend tests
cd backend && uv run pytest

# Agent tests
cd agents/[agent-name] && uv run pytest

# All tests
make test
````

## 📝 API Documentation

Once the backend is running, visit:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.
