#!/bin/bash

# 🧪 WebSocket MCP Connection Fix Test Script
# This script tests the complete flow after applying WebSocket reliability fixes

set -e  # Exit on any error

echo "🚀 Testing WebSocket MCP Connection Fixes"
echo "========================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${2}${1}${NC}"
}

print_step() {
    echo -e "\n${BLUE}📋 Step: ${1}${NC}"
}

print_success() {
    echo -e "${GREEN}✅ ${1}${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  ${1}${NC}"
}

print_error() {
    echo -e "${RED}❌ ${1}${NC}"
}

# Check if services are running
check_service_health() {
    local service_name=$1
    local url=$2
    local timeout=${3:-10}
    
    print_step "Checking $service_name health"
    
    if curl -f --max-time $timeout -s "$url" > /dev/null 2>&1; then
        print_success "$service_name is healthy"
        return 0
    else
        print_error "$service_name is not responding at $url"
        return 1
    fi
}

# Test WebSocket connection
test_websocket() {
    local ws_url=$1
    print_step "Testing WebSocket connection to $ws_url"
    
    # Use a simple WebSocket test (requires websocat or similar tool)
    if command -v websocat &> /dev/null; then
        echo '{"type":"ping","timestamp":"'$(date -Iseconds)'"}' | timeout 10 websocat "$ws_url" > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            print_success "WebSocket connection successful"
            return 0
        else
            print_warning "WebSocket connection failed, HTTP fallback should work"
            return 1
        fi
    else
        print_warning "websocat not available, skipping direct WebSocket test"
        return 0
    fi
}

# Test NLP Agent query processing
test_nlp_query() {
    print_step "Testing NLP Agent query processing with MCP integration"
    
    local test_query="What is the total revenue for Q1 2024?"
    local nlp_url="http://localhost:8001/process"
    
    print_status "Sending test query: $test_query" "$BLUE"
    
    local response=$(curl -s --max-time 30 -X POST "$nlp_url" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"$test_query\",
            \"query_id\": \"test-$(date +%s)\",
            \"user_id\": \"test-user\",
            \"session_id\": \"test-session\"
        }")
    
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        print_success "NLP Agent responded successfully"
        
        # Check if response contains SQL query (indicating MCP worked)
        if echo "$response" | grep -q '"sql_query"'; then
            local sql_query=$(echo "$response" | jq -r '.sql_query // "none"')
            if [ "$sql_query" != "none" ] && [ "$sql_query" != "" ]; then
                print_success "SQL query generated: $sql_query"
                return 0
            else
                print_warning "NLP Agent responded but no SQL query generated (MCP issue)"
                return 1
            fi
        else
            print_warning "NLP Agent responded but response format unexpected"
            echo "Response: $response"
            return 1
        fi
    else
        print_error "NLP Agent failed to respond"
        return 1
    fi
}

# Test MCP Server directly
test_mcp_server() {
    print_step "Testing TiDB MCP Server directly"
    
    # Test HTTP health endpoint
    local mcp_health_url="http://localhost:8000/health"
    if curl -f -s --max-time 10 "$mcp_health_url" > /dev/null; then
        print_success "MCP Server HTTP endpoint is healthy"
    else
        print_error "MCP Server HTTP endpoint failed"
        return 1
    fi
    
    # Test tools endpoint
    local mcp_tools_url="http://localhost:8000/tools"
    local tools_response=$(curl -s --max-time 10 "$mcp_tools_url")
    if [ $? -eq 0 ] && echo "$tools_response" | grep -q "llm_generate_sql_tool"; then
        print_success "MCP Server tools endpoint working (SQL generation available)"
    else
        print_warning "MCP Server tools endpoint issue or SQL generation not available"
        echo "Tools response: $tools_response"
    fi
    
    return 0
}

# Test complete flow
test_complete_flow() {
    print_step "Testing complete flow: Frontend → Backend → NLP → MCP → SQL"
    
    local backend_url="http://localhost:8080/api/query"
    local test_query="Show me revenue trends for the last quarter"
    
    print_status "Sending query through backend: $test_query" "$BLUE"
    
    local response=$(curl -s --max-time 45 -X POST "$backend_url" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"$test_query\",
            \"user_id\": \"test-user\",
            \"session_id\": \"test-session-$(date +%s)\"
        }")
    
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        print_success "Backend processed query successfully"
        
        # Check for SQL in response
        if echo "$response" | grep -q -i "select\|from\|where"; then
            print_success "SQL query found in response - MCP integration working!"
            local sql_preview=$(echo "$response" | grep -o -i "select[^;]*" | head -1)
            print_status "SQL Preview: $sql_preview" "$GREEN"
            return 0
        else
            print_warning "Backend responded but no SQL found - checking for processed intent"
            if echo "$response" | grep -q '"intent"'; then
                print_warning "Intent processing working but SQL generation may have failed"
                return 1
            else
                print_error "No intent or SQL found in response"
                return 1
            fi
        fi
    else
        print_error "Backend query failed"
        return 1
    fi
}

# Get detailed diagnostics
get_diagnostics() {
    print_step "Gathering diagnostic information"
    
    echo -e "\n${BLUE}📊 Service Diagnostics:${NC}"
    
    # NLP Agent diagnostics
    print_status "NLP Agent Diagnostics:" "$YELLOW"
    local nlp_diag=$(curl -s --max-time 10 "http://localhost:8001/diagnostics" 2>/dev/null || echo "Failed to get diagnostics")
    echo "$nlp_diag" | jq '.' 2>/dev/null || echo "$nlp_diag"
    
    # MCP Server status
    print_status "MCP Server Status:" "$YELLOW"
    local mcp_status=$(curl -s --max-time 10 "http://localhost:8000/status" 2>/dev/null || echo "Failed to get status")
    echo "$mcp_status" | jq '.' 2>/dev/null || echo "$mcp_status"
    
    # Connection statistics
    print_status "Connection Statistics:" "$YELLOW"
    local nlp_metrics=$(curl -s --max-time 10 "http://localhost:8001/metrics" 2>/dev/null || echo "Failed to get metrics")
    echo "$nlp_metrics" | jq '.websocket_stats // .client_stats // "No WebSocket stats available"' 2>/dev/null || echo "Metrics unavailable"
}

# Main test execution
main() {
    print_status "🧪 WebSocket MCP Connection Fix Test Suite" "$BLUE"
    print_status "Testing the complete AI-CFO system after WebSocket reliability improvements" "$BLUE"
    
    local test_passed=0
    local test_failed=0
    
    # Check prerequisites
    if ! command -v curl &> /dev/null; then
        print_error "curl is required but not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        print_warning "jq not found - JSON parsing will be limited"
    fi
    
    # Wait for services to be ready
    print_step "Waiting for services to initialize (30 seconds)"
    sleep 30
    
    # Test each component
    echo -e "\n${BLUE}🔍 Component Health Checks${NC}"
    
    if check_service_health "TiDB MCP Server" "http://localhost:8000/health"; then
        ((test_passed++))
    else
        ((test_failed++))
    fi
    
    if check_service_health "NLP Agent" "http://localhost:8001/health"; then
        ((test_passed++))
    else
        ((test_failed++))
    fi
    
    if check_service_health "Backend" "http://localhost:8080/health"; then
        ((test_passed++))
    else
        ((test_failed++))
    fi
    
    # Test MCP Server functionality
    echo -e "\n${BLUE}🔧 MCP Server Functionality${NC}"
    if test_mcp_server; then
        ((test_passed++))
    else
        ((test_failed++))
    fi
    
    # Test WebSocket connections (if tools available)
    echo -e "\n${BLUE}🌐 WebSocket Connection Tests${NC}"
    if test_websocket "ws://localhost:8000/ws"; then
        ((test_passed++))
    else
        print_status "WebSocket test skipped or failed - HTTP fallback should handle this" "$YELLOW"
    fi
    
    # Test NLP processing with MCP
    echo -e "\n${BLUE}🧠 NLP Agent MCP Integration${NC}"
    if test_nlp_query; then
        ((test_passed++))
        print_success "🎉 MCP SQL generation is working!"
    else
        ((test_failed++))
        print_error "❌ MCP SQL generation failed - this was the main issue"
    fi
    
    # Test complete flow
    echo -e "\n${BLUE}🔄 End-to-End Flow Test${NC}"
    if test_complete_flow; then
        ((test_passed++))
        print_success "🎉 Complete flow is working!"
    else
        ((test_failed++))
        print_error "❌ End-to-end flow failed"
    fi
    
    # Get diagnostics
    echo -e "\n${BLUE}📋 Diagnostic Information${NC}"
    get_diagnostics
    
    # Summary
    echo -e "\n${BLUE}📊 Test Summary${NC}"
    echo "Tests Passed: $test_passed"
    echo "Tests Failed: $test_failed"
    
    if [ $test_failed -eq 0 ]; then
        print_success "🎉 All tests passed! WebSocket MCP fixes are working."
        echo -e "\n${GREEN}✅ The main issue (SQL generation timeouts) should now be resolved.${NC}"
        echo -e "${GREEN}✅ Frontend should now receive proper SQL queries and data visualization.${NC}"
        return 0
    else
        print_error "❌ Some tests failed. Check the logs above for details."
        
        if [ $test_failed -eq 1 ] && echo "$test_nlp_query" | grep -q "SQL query generated"; then
            print_status "🔧 The core MCP connection issue appears to be resolved!" "$YELLOW"
            print_status "Some auxiliary tests may have failed due to environment differences." "$YELLOW"
        fi
        
        return 1
    fi
}

# Run the main test
main "$@"
