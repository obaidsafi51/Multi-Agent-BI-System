# AI CFO BI Agent - Development Commands

.PHONY: help setup build up down logs clean test

help: ## Show this help message
	@echo "AI CFO BI Agent - Development Commands"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Initial setup - copy env file and build containers
	@echo "🚀 Setting up development environment..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "📝 Created .env file - please update with your values"; fi
	@docker-compose build
	@echo "✅ Setup complete!"

setup-uv: ## Initialize uv projects for local development
	@echo "📦 Setting up uv projects..."
	@./init-uv.sh
	@echo "✅ uv setup complete!"

build: ## Build all Docker containers
	@echo "🔨 Building containers..."
	@docker-compose build

up: ## Start all services
	@echo "🚀 Starting services..."
	@docker-compose up -d
	@echo "✅ Services started!"
	@echo "🌐 Frontend: http://localhost:3000"
	@echo "🔧 Backend: http://localhost:8000"
	@echo "🐰 RabbitMQ: http://localhost:15672"

down: ## Stop all services
	@echo "🛑 Stopping services..."
	@docker-compose down

logs: ## Show logs for all services
	@docker-compose logs -f

logs-frontend: ## Show frontend logs
	@docker-compose logs -f frontend

logs-backend: ## Show backend logs
	@docker-compose logs -f backend

logs-agents: ## Show all agent logs
	@docker-compose logs -f nlp-agent data-agent viz-agent personal-agent

restart: ## Restart all services
	@echo "🔄 Restarting services..."
	@docker-compose restart

clean: ## Clean up containers and volumes
	@echo "🧹 Cleaning up..."
	@docker-compose down -v
	@docker system prune -f

test: ## Run tests for all components
	@echo "🧪 Running tests..."
	@cd frontend && npm test
	@cd backend && uv run pytest
	@echo "✅ Tests completed!"

test-backend: ## Run backend tests with uv
	@cd backend && uv run pytest

test-agents: ## Run agent tests with uv
	@cd agents/nlp-agent && uv run pytest
	@cd agents/data-agent && uv run pytest
	@cd agents/viz-agent && uv run pytest
	@cd agents/personal-agent && uv run pytest

dev-frontend: ## Start frontend in development mode
	@cd frontend && npm run dev

dev-backend: ## Start backend in development mode
	@cd backend && uv run uvicorn main:app --reload

install-backend: ## Install backend dependencies with uv
	@cd backend && uv sync

install-agents: ## Install all agent dependencies with uv
	@cd agents/nlp-agent && uv sync
	@cd agents/data-agent && uv sync
	@cd agents/viz-agent && uv sync
	@cd agents/personal-agent && uv sync

install-all: ## Install all Python dependencies with uv
	@echo "📦 Installing all Python dependencies with uv..."
	@$(MAKE) install-backend
	@$(MAKE) install-agents
	@echo "✅ All dependencies installed!"

status: ## Show status of all services
	@docker-compose ps