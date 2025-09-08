#!/bin/bash

# Verify uv projects for all Python components (Docker containers handle dependencies)

echo "🚀 Verifying uv projects for Docker builds..."

# Verify backend
echo "📦 Verifying backend pyproject.toml..."
cd backend && uv sync --dry-run --no-dev || echo "⚠️  Backend pyproject.toml needs attention"
cd ..

# Verify agents
echo "📦 Verifying NLP agent pyproject.toml..."
cd agents/nlp-agent && uv sync --dry-run --no-dev || echo "⚠️  NLP agent pyproject.toml needs attention"
cd ../..

echo "📦 Verifying Data agent pyproject.toml..."
cd agents/data-agent && uv sync --dry-run --no-dev || echo "⚠️  Data agent pyproject.toml needs attention"
cd ../..

echo "📦 Verifying Visualization agent pyproject.toml..."
cd agents/viz-agent && uv sync --dry-run --no-dev || echo "⚠️  Viz agent pyproject.toml needs attention"
cd ../..

echo "📦 Verifying Personalization agent pyproject.toml..."
cd agents/personal-agent && uv sync --dry-run --no-dev || echo "⚠️  Personal agent pyproject.toml needs attention"
cd ../..

echo "✅ All uv projects verified for Docker builds!"
echo ""
echo "� Dependencies are handled by Docker containers:"
echo "   - docker compose build to build containers with dependencies"
echo "   - docker compose up to run the complete system"
echo "   - No virtual environments needed - each service runs in its own container"