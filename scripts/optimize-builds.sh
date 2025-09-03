#!/bin/bash

# Docker Build Optimization Script
# This script optimizes Docker builds for faster development

set -e

echo "🚀 Optimizing Docker builds..."

# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Clean up unused Docker resources
echo "🧹 Cleaning up Docker resources..."
docker system prune -f
docker builder prune -f

# Build with parallel builds and cache optimization
echo "🔨 Building with optimizations..."
docker-compose build \
    --parallel \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    --build-arg BUILDKIT_MULTI_PLATFORM=1

echo "✅ Build optimization complete!"
echo ""
echo "💡 Tips for faster builds:"
echo "   - Use 'docker-compose build --parallel' for parallel builds"
echo "   - Use 'docker-compose build --no-cache' only when needed"
echo "   - Keep base images updated"
echo "   - Use multi-stage builds (already implemented)"
echo "   - Optimize .dockerignore files (already implemented)" 