#!/bin/bash
# troubleshoot.sh: Diagnose common Docker and service issues

echo "🔧 AI CFO BI Agent - Troubleshooting Script"
echo "=========================================="

# Check Docker status
echo "🐳 Checking Docker status..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running or accessible"
    echo "   Try: sudo systemctl start docker"
    exit 1
else
    echo "✅ Docker is running"
fi

# Check Docker Compose
echo ""
echo "📦 Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    exit 1
else
    echo "✅ Docker Compose is available"
    docker-compose version
fi

# Check environment file
echo ""
echo "🔍 Checking environment configuration..."
if [ ! -f .env ]; then
    echo "❌ .env file not found"
    echo "   Run: cp .env.example .env"
    exit 1
else
    echo "✅ .env file exists"
    
    # Check for placeholder values
    if grep -q "your_tidb_password_here" .env; then
        echo "⚠️  TIDB_PASSWORD is still set to placeholder value"
    fi
    
    if grep -q "your_kimi_api_key_here" .env; then
        echo "⚠️  KIMI_API_KEY is still set to placeholder value"
    fi
fi

# Check service status
echo ""
echo "🚀 Checking service status..."
docker-compose ps

# Check service health
echo ""
echo "🏥 Checking service health..."

services=("redis:6379" "rabbitmq:5672" "tidb:4000" "backend:8000" "frontend:3000")

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if nc -z localhost "$port" 2>/dev/null; then
        echo "✅ $name is responding on port $port"
    else
        echo "❌ $name is not responding on port $port"
    fi
done

# Check logs for errors
echo ""
echo "📋 Recent error logs..."
docker-compose logs --tail=10 | grep -i error || echo "No recent errors found"

# Check disk space
echo ""
echo "💾 Checking disk space..."
df -h | head -2

# Check memory usage
echo ""
echo "🧠 Checking memory usage..."
free -h

# Docker system info
echo ""
echo "🐳 Docker system info..."
docker system df

echo ""
echo "🔧 Common troubleshooting steps:"
echo "1. Restart all services: docker-compose restart"
echo "2. Rebuild containers: docker-compose up -d --build"
echo "3. Clean restart: docker-compose down && docker-compose up -d"
echo "4. View service logs: docker-compose logs -f [service-name]"
echo "5. Check environment: ./scripts/validate-env.sh"
echo ""
echo "📞 If issues persist, check the logs with:"
echo "   docker-compose logs -f"