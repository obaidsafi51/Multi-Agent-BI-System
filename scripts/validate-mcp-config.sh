#!/bin/bash

# Validate MCP Schema Management Configuration
# This script checks that all required environment variables and configurations are properly set

set -e

echo "============================================================"
echo "MCP SCHEMA MANAGEMENT CONFIGURATION VALIDATION"
echo "============================================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy from .env.example and configure."
    exit 1
fi

echo "✅ .env file found"

# Source the .env file
set -a
source .env
set +a

# Check required TiDB variables
required_vars=("TIDB_HOST" "TIDB_USER" "TIDB_PASSWORD" "TIDB_DATABASE")
missing_vars=()

echo ""
echo "📋 Checking required environment variables..."

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
        echo "❌ $var is not set"
    else
        echo "✅ $var is set"
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo ""
    echo "❌ Missing required variables: ${missing_vars[*]}"
    echo "Please set these variables in your .env file"
    exit 1
fi

# Check MCP configuration variables
echo ""
echo "⚙️  Checking MCP configuration variables..."

mcp_vars=("TIDB_MCP_SERVER_URL" "MCP_CONNECTION_TIMEOUT" "MCP_REQUEST_TIMEOUT" "MCP_MAX_RETRIES" "MCP_CACHE_TTL")
for var in "${mcp_vars[@]}"; do
    if [ -n "${!var}" ]; then
        echo "✅ $var = ${!var}"
    else
        echo "ℹ️  $var not set (will use default)"
    fi
done

# Check schema validation variables
echo ""
echo "🔍 Checking schema validation variables..."

validation_vars=("SCHEMA_STRICT_MODE" "SCHEMA_VALIDATE_TYPES" "SCHEMA_VALIDATE_CONSTRAINTS" "SCHEMA_VALIDATE_RELATIONSHIPS" "SCHEMA_ALLOW_UNKNOWN_COLUMNS")
for var in "${validation_vars[@]}"; do
    if [ -n "${!var}" ]; then
        echo "✅ $var = ${!var}"
    else
        echo "ℹ️  $var not set (will use default)"
    fi
done

# Test configuration loading
echo ""
echo "🧪 Testing configuration loading..."

if python3 backend/test_mcp_config.py > /dev/null 2>&1; then
    echo "✅ Configuration loading test passed"
else
    echo "❌ Configuration loading test failed"
    echo "Running detailed test..."
    python3 backend/test_mcp_config.py
    exit 1
fi

# Check Docker Compose configuration
echo ""
echo "🐳 Checking Docker Compose configuration..."

if command -v docker-compose > /dev/null 2>&1; then
    if docker-compose config > /dev/null 2>&1; then
        echo "✅ Docker Compose configuration is valid"
        
        # Check if tidb-mcp-server service is configured
        if docker-compose config | grep -q "tidb-mcp-server:"; then
            echo "✅ TiDB MCP Server service is configured"
        else
            echo "❌ TiDB MCP Server service not found in docker-compose.yml"
            exit 1
        fi
    else
        echo "❌ Docker Compose configuration is invalid"
        docker-compose config
        exit 1
    fi
elif command -v docker > /dev/null 2>&1 && docker compose version > /dev/null 2>&1; then
    if docker compose config > /dev/null 2>&1; then
        echo "✅ Docker Compose configuration is valid"
        
        # Check if tidb-mcp-server service is configured
        if docker compose config | grep -q "tidb-mcp-server:"; then
            echo "✅ TiDB MCP Server service is configured"
        else
            echo "❌ TiDB MCP Server service not found in docker-compose.yml"
            exit 1
        fi
    else
        echo "❌ Docker Compose configuration is invalid"
        docker compose config
        exit 1
    fi
else
    echo "ℹ️  Docker Compose not available - skipping Docker configuration check"
    echo "ℹ️  Please ensure Docker and Docker Compose are installed for full validation"
fi

echo ""
echo "🎯 VALIDATION COMPLETE"
echo "✅ All MCP schema management configuration checks passed!"
echo ""
echo "You can now start the services with:"
echo "  make up"
echo "or:"
echo "  docker-compose up -d"
echo ""