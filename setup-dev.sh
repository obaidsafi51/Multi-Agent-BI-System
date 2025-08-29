#!/bin/bash

# AI CFO BI Agent - Development Setup Script

set -e  # Exit on any error

echo "🚀 Setting up AI CFO BI Agent development environment..."

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if uv is installed for local development
if ! command -v uv &> /dev/null; then
    echo "⚠️  uv is not installed. For local Python development, install uv:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "   This is optional - Docker containers will work without it."
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your actual configuration values:"
    echo "   - TIDB_PASSWORD: Set a secure password for TiDB"
    echo "   - KIMI_API_KEY: Your KIMI LLM API key"
    echo "   - SECRET_KEY: Generate with: openssl rand -hex 32"
    echo ""
    echo "Press Enter to continue after updating .env file..."
    read -r
fi

# Validate environment
echo "🔍 Validating environment configuration..."
./scripts/validate-env.sh

# Clean up development artifacts and containers
echo "🧹 Cleaning up development artifacts..."
./scripts/cleanup.sh

echo "🧹 Cleaning up existing containers..."
docker-compose down --remove-orphans

# Build containers
echo "🔨 Building Docker containers..."
docker-compose build --no-cache

# Start infrastructure services first
echo "🚀 Starting infrastructure services..."
docker-compose up -d redis rabbitmq tidb

# Wait for infrastructure to be ready
echo "⏳ Waiting for infrastructure services..."
./scripts/wait-for-it.sh localhost:6379 -t 60 -- echo "Redis is ready"
./scripts/wait-for-it.sh localhost:5672 -t 60 -- echo "RabbitMQ is ready"
./scripts/wait-for-it.sh localhost:4000 -t 120 -- echo "TiDB is ready"

# Start application services
echo "🚀 Starting application services..."
docker-compose up -d

# Wait for all services to be ready
echo "⏳ Waiting for all services to start..."
sleep 15

# Check service health
echo "🔍 Checking service health..."
docker-compose ps

# Test basic connectivity
echo "🧪 Testing service connectivity..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend health check passed"
else
    echo "⚠️  Backend health check failed - service may still be starting"
fi

if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend connectivity check passed"
else
    echo "⚠️  Frontend connectivity check failed - service may still be starting"
fi

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "🌐 Access points:"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:8000"
echo "   - Backend Health: http://localhost:8000/health"
echo "   - RabbitMQ Management: http://localhost:15672 (guest/guest)"
echo "   - Redis: localhost:6379"
echo "   - TiDB: localhost:4000"
echo ""
echo "📝 Useful commands:"
echo "   - View logs: docker-compose logs -f [service-name]"
echo "   - Stop all: docker-compose down"
echo "   - Restart service: docker-compose restart [service-name]"
echo "   - Rebuild service: docker-compose up -d --build [service-name]"
echo ""
echo "🔧 For development:"
echo "   - Backend logs: docker-compose logs -f backend"
echo "   - All agent logs: docker-compose logs -f nlp-agent data-agent viz-agent personal-agent"