#!/bin/bash
# pre-build.sh: Prepare environment for clean Docker builds

set -e

echo "🔧 Preparing for Docker build..."

# Clean up development artifacts
echo "Running cleanup..."
./scripts/cleanup.sh

# Validate environment
echo "Validating environment..."
./scripts/validate-env.sh

# Check Docker status
echo "Checking Docker status..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running"
    exit 1
fi

# Stop existing containers
echo "Stopping existing containers..."
docker-compose down --remove-orphans 2>/dev/null || true

# Remove old images (optional - uncomment if needed)
# echo "Removing old images..."
# docker-compose down --rmi all 2>/dev/null || true

echo "✅ Pre-build preparation complete!"
echo ""
echo "🚀 Ready to build. Run:"
echo "   docker-compose build --no-cache"
echo "   docker-compose up -d"