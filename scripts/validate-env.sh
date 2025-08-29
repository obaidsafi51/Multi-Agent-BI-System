#!/bin/bash
# validate-env.sh: Validate environment variables before starting services

set -e

echo "🔍 Validating environment configuration..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.example to .env and configure your settings."
    exit 1
fi

# Source the .env file
source .env

# Required environment variables
REQUIRED_VARS=(
    "TIDB_PASSWORD"
    "KIMI_API_KEY" 
    "SECRET_KEY"
)

# Check each required variable
missing_vars=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

# Report missing variables
if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "❌ Error: Missing required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please set these variables in your .env file."
    exit 1
fi

# Validate specific values
if [ "$TIDB_PASSWORD" = "your_tidb_password_here" ]; then
    echo "⚠️  Warning: TIDB_PASSWORD is still set to the default placeholder value."
    echo "   Consider setting a secure password for production use."
fi

if [ ${#SECRET_KEY} -lt 32 ]; then
    echo "⚠️  Warning: SECRET_KEY should be at least 32 characters long for security."
fi

echo "✅ Environment validation passed!"
echo ""
echo "Configuration summary:"
echo "  - TiDB Password: [SET]"
echo "  - KIMI API Key: [SET]"
echo "  - Secret Key: [SET]"
echo ""