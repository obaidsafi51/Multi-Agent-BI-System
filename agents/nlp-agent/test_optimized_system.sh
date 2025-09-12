#!/bin/bash
# Test Runner for Optimized NLP Agent System
# This script will test the optimized NLP Agent with WebSocket connectivity

set -e  # Exit on any error

echo "🚀 Starting Optimized NLP Agent System Test"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a service is running
check_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Checking $service_name at $url..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            print_success "$service_name is running!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start within $((max_attempts * 2)) seconds"
    return 1
}

# Function to test an endpoint
test_endpoint() {
    local url=$1
    local method=$2
    local data=$3
    local description=$4
    
    print_status "Testing: $description"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "%{http_code}" "$url")
        http_code="${response: -3}"
    else
        response=$(curl -s -w "%{http_code}" -X "$method" -H "Content-Type: application/json" -d "$data" "$url")
        http_code="${response: -3}"
    fi
    
    if [ "$http_code" = "200" ]; then
        print_success "$description - HTTP $http_code"
        echo "Response: ${response%???}" | head -c 200
        echo ""
    else
        print_error "$description - HTTP $http_code"
        echo "Response: ${response%???}"
        return 1
    fi
}

# Step 1: Check if TiDB MCP Server is running
print_status "Step 1: Checking TiDB MCP Server..."
if ! check_service "http://localhost:8000/health" "TiDB MCP Server"; then
    print_warning "TiDB MCP Server not running. Let's start it..."
    
    # Start TiDB MCP Server in background
    cd "../../tidb-mcp-server"
    print_status "Starting TiDB MCP Server with WebSocket support..."
    
    # Check if we have .env file
    if [ ! -f ".env" ]; then
        print_warning "No .env file found. Creating minimal configuration..."
        cat > .env << EOF
TIDB_HOST=localhost
TIDB_PORT=4000
TIDB_USER=root
TIDB_PASSWORD=
TIDB_DATABASE=test
USE_HTTP_API=true
LOG_LEVEL=INFO
EOF
    fi
    
    # Start server in background
    python -m tidb_mcp_server.main &
    MCP_SERVER_PID=$!
    echo $MCP_SERVER_PID > /tmp/mcp_server.pid
    
    print_status "Waiting for MCP Server to start (PID: $MCP_SERVER_PID)..."
    sleep 5
    
    if ! check_service "http://localhost:8000/health" "TiDB MCP Server"; then
        print_error "Failed to start TiDB MCP Server"
        exit 1
    fi
    
    cd "../agents/nlp-agent"
fi

# Step 2: Start Optimized NLP Agent
print_status "Step 2: Starting Optimized NLP Agent..."

# Create minimal .env if not exists
if [ ! -f ".env" ]; then
    print_status "Creating .env file for NLP Agent..."
    cat > .env << EOF
MCP_SERVER_WS_URL=ws://localhost:8000/ws
MCP_SERVER_HTTP_URL=http://localhost:8000
KIMI_API_KEY=your_kimi_api_key_here
KIMI_API_BASE_URL=https://api.moonshot.ai/v1
AGENT_ID=nlp-agent-001
AGENT_TYPE=nlp
HOST=0.0.0.0
PORT=8001
MAX_CONCURRENT_REQUESTS=10
CONNECTION_POOL_SIZE=20
CACHE_TTL_SECONDS=300
LOG_LEVEL=INFO
EOF
fi

# Start NLP Agent in background
print_status "Starting Optimized NLP Agent..."
python main_optimized.py &
NLP_AGENT_PID=$!
echo $NLP_AGENT_PID > /tmp/nlp_agent.pid

print_status "Waiting for NLP Agent to start (PID: $NLP_AGENT_PID)..."
sleep 8

if ! check_service "http://localhost:8001/health" "Optimized NLP Agent"; then
    print_error "Failed to start Optimized NLP Agent"
    
    # Check if we can fall back to regular agent
    print_warning "Trying to start regular NLP Agent as fallback..."
    kill $NLP_AGENT_PID 2>/dev/null || true
    python main.py &
    NLP_AGENT_PID=$!
    echo $NLP_AGENT_PID > /tmp/nlp_agent.pid
    
    sleep 5
    if ! check_service "http://localhost:8001/health" "NLP Agent"; then
        print_error "Failed to start any NLP Agent"
        exit 1
    fi
fi

# Step 3: Run Tests
print_status "Step 3: Running Performance Tests..."

echo ""
print_status "=== BASIC HEALTH CHECKS ==="

# Test MCP Server health
test_endpoint "http://localhost:8000/health" "GET" "" "MCP Server Health Check"

# Test NLP Agent health
test_endpoint "http://localhost:8001/health" "GET" "" "NLP Agent Health Check"

# Test NLP Agent status
test_endpoint "http://localhost:8001/status" "GET" "" "NLP Agent Status"

echo ""
print_status "=== QUERY CLASSIFICATION TESTS ==="

# Test query classification
test_endpoint "http://localhost:8001/classify" "POST" '{"query": "How many customers do we have?"}' "Simple Query Classification"

test_endpoint "http://localhost:8001/classify" "POST" '{"query": "Show me detailed sales analysis with correlation trends"}' "Complex Query Classification"

echo ""
print_status "=== QUERY PROCESSING TESTS ==="

# Test fast path query
print_status "Testing Fast Path Query Processing..."
start_time=$(date +%s.%N)
test_endpoint "http://localhost:8001/process" "POST" '{"query": "What is the total number of orders?", "use_cache": true}' "Fast Path Query"
end_time=$(date +%s.%N)
fast_duration=$(echo "$end_time - $start_time" | bc -l)
printf "Fast Path Duration: %.3f seconds\n" $fast_duration

# Test standard path query
print_status "Testing Standard Path Query Processing..."
start_time=$(date +%s.%N)
test_endpoint "http://localhost:8001/process" "POST" '{"query": "Show me sales data for the last quarter", "use_cache": true}' "Standard Path Query"
end_time=$(date +%s.%N)
standard_duration=$(echo "$end_time - $start_time" | bc -l)
printf "Standard Path Duration: %.3f seconds\n" $standard_duration

# Test comprehensive path query
print_status "Testing Comprehensive Path Query Processing..."
start_time=$(date +%s.%N)
test_endpoint "http://localhost:8001/process" "POST" '{"query": "Generate a comprehensive analysis of customer behavior patterns with detailed insights", "force_comprehensive": true}' "Comprehensive Path Query"
end_time=$(date +%s.%N)
comprehensive_duration=$(echo "$end_time - $start_time" | bc -l)
printf "Comprehensive Path Duration: %.3f seconds\n" $comprehensive_duration

echo ""
print_status "=== CACHE TESTING ==="

# Test cache hit by repeating a query
print_status "Testing Cache Performance (repeating same query)..."
start_time=$(date +%s.%N)
test_endpoint "http://localhost:8001/process" "POST" '{"query": "What is the total number of orders?", "use_cache": true}' "Cache Hit Test"
end_time=$(date +%s.%N)
cache_duration=$(echo "$end_time - $start_time" | bc -l)
printf "Cache Hit Duration: %.3f seconds\n" $cache_duration

echo ""
print_status "=== PERFORMANCE SUMMARY ==="
echo "Fast Path:        $(printf "%.3f" $fast_duration)s"
echo "Standard Path:    $(printf "%.3f" $standard_duration)s"
echo "Comprehensive:    $(printf "%.3f" $comprehensive_duration)s"
echo "Cache Hit:        $(printf "%.3f" $cache_duration)s"

# Calculate improvements (assuming baseline times)
if (( $(echo "$fast_duration < 3.0" | bc -l) )); then
    print_success "Fast path meets target (<3s)"
else
    print_warning "Fast path slower than target (3s)"
fi

if (( $(echo "$cache_duration < 1.0" | bc -l) )); then
    print_success "Cache performance excellent (<1s)"
else
    print_warning "Cache performance could be better"
fi

echo ""
print_status "=== CLEANUP ==="

# Function to cleanup
cleanup() {
    print_status "Stopping services..."
    
    if [ -f "/tmp/nlp_agent.pid" ]; then
        NLP_PID=$(cat /tmp/nlp_agent.pid)
        kill $NLP_PID 2>/dev/null || true
        rm -f /tmp/nlp_agent.pid
        print_status "Stopped NLP Agent (PID: $NLP_PID)"
    fi
    
    if [ -f "/tmp/mcp_server.pid" ]; then
        MCP_PID=$(cat /tmp/mcp_server.pid)
        kill $MCP_PID 2>/dev/null || true
        rm -f /tmp/mcp_server.pid
        print_status "Stopped MCP Server (PID: $MCP_PID)"
    fi
}

# Ask user if they want to keep services running
echo ""
read -p "Keep services running for manual testing? (y/N): " keep_running

if [[ $keep_running =~ ^[Yy]$ ]]; then
    print_success "Services are still running:"
    print_success "- TiDB MCP Server: http://localhost:8000"
    print_success "- NLP Agent: http://localhost:8001"
    print_status "Use 'pkill -f \"python.*main\"' to stop all services when done"
else
    cleanup
    print_success "All services stopped"
fi

print_success "Test completed! Check the results above for performance metrics."
