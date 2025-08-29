#!/bin/bash

# Initialize uv projects for all Python components

echo "🚀 Initializing uv projects..."

# Initialize backend
echo "📦 Initializing backend..."
cd backend && uv sync --dev
cd ..

# Initialize agents
echo "📦 Initializing NLP agent..."
cd agents/nlp-agent && uv sync --dev
cd ../..

echo "📦 Initializing Data agent..."
cd agents/data-agent && uv sync --dev
cd ../..

echo "📦 Initializing Visualization agent..."
cd agents/viz-agent && uv sync --dev
cd ../..

echo "📦 Initializing Personalization agent..."
cd agents/personal-agent && uv sync --dev
cd ../..

echo "✅ All uv projects initialized!"
echo ""
echo "🔧 You can now use:"
echo "   - uv run <command> to run commands in the virtual environment"
echo "   - uv add <package> to add new dependencies"
echo "   - uv sync to install/update dependencies"