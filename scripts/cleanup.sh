#!/bin/bash
# cleanup.sh: Clean up development artifacts and prepare for Docker builds

echo "🧹 Cleaning up development artifacts..."

# Remove Python virtual environments
echo "Removing Python virtual environments..."
find . -name ".venv" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "venv" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "env" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove Python cache files
echo "Removing Python cache files..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
find . -name "*.pyd" -delete 2>/dev/null || true

# Remove Node.js artifacts (but keep node_modules in frontend)
echo "Removing Node.js build artifacts..."
find . -name ".next" -type d -not -path "./frontend/.next" -exec rm -rf {} + 2>/dev/null || true
find . -name "dist" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "build" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove IDE files
echo "Removing IDE files..."
find . -name ".vscode" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name ".idea" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.swp" -delete 2>/dev/null || true
find . -name "*.swo" -delete 2>/dev/null || true

# Remove OS files
echo "Removing OS files..."
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "Thumbs.db" -delete 2>/dev/null || true

# Remove log files
echo "Removing log files..."
find . -name "*.log" -delete 2>/dev/null || true

# Remove temporary files
echo "Removing temporary files..."
find . -name "tmp" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "temp" -type d -exec rm -rf {} + 2>/dev/null || true

# Docker cleanup
echo "Cleaning up Docker artifacts..."
docker system prune -f 2>/dev/null || true

echo "✅ Cleanup complete!"
echo ""
echo "🐳 To rebuild containers cleanly:"
echo "   docker-compose down --remove-orphans"
echo "   docker-compose build --no-cache"
echo "   docker-compose up -d"