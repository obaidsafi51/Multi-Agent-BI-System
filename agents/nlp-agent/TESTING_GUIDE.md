# 🚀 Quick Start Guide - Testing Optimized NLP Agent

## Option 1: Automated Testing (Recommended)

Run the comprehensive test script:

```bash
cd "/home/obaidsafi31/Desktop/Agentic BI /agents/nlp-agent"
./test_optimized_system.sh
```

This script will:

- Start both TiDB MCP Server and NLP Agent
- Run performance tests on all processing paths
- Measure response times and cache performance
- Show detailed results and cleanup

## Option 2: Manual Step-by-Step Testing

### Step 1: Start TiDB MCP Server

```bash
# Terminal 1
cd "/home/obaidsafi31/Desktop/Agentic BI /tidb-mcp-server"

# Create minimal .env if needed
echo "TIDB_HOST=localhost
TIDB_PORT=4000
TIDB_USER=root
TIDB_PASSWORD=
TIDB_DATABASE=test
USE_HTTP_API=true
LOG_LEVEL=INFO" > .env

# Start MCP server with WebSocket support
python -m tidb_mcp_server.main
```

Wait for: `✅ Server started successfully`

### Step 2: Start Optimized NLP Agent

```bash
# Terminal 2
cd "/home/obaidsafi31/Desktop/Agentic BI /agents/nlp-agent"

# Create .env for NLP agent
echo "MCP_SERVER_WS_URL=ws://localhost:8000/ws
MCP_SERVER_HTTP_URL=http://localhost:8000
KIMI_API_KEY=your_kimi_api_key_here
AGENT_ID=nlp-agent-001
AGENT_TYPE=nlp
PORT=8001
LOG_LEVEL=INFO" > .env

# Start optimized NLP agent
python main_optimized.py
```

Wait for: `✅ Enhanced NLP Agent started successfully!`

### Step 3: Test the System

```bash
# Terminal 3 - Run these tests

# 1. Health checks
curl http://localhost:8000/health  # MCP Server
curl http://localhost:8001/health  # NLP Agent

# 2. Test query classification
curl -X POST http://localhost:8001/classify \
  -H "Content-Type: application/json" \
  -d '{"query": "How many customers do we have?"}'

# 3. Test fast path (simple query)
time curl -X POST http://localhost:8001/process \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the total number of orders?"}'

# 4. Test standard path
time curl -X POST http://localhost:8001/process \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me sales data for last quarter"}'

# 5. Test comprehensive path
time curl -X POST http://localhost:8001/process \
  -H "Content-Type: application/json" \
  -d '{"query": "Generate comprehensive sales analysis", "force_comprehensive": true}'

# 6. Test cache performance (repeat same query)
time curl -X POST http://localhost:8001/process \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the total number of orders?"}'

# 7. Check detailed status
curl http://localhost:8001/status
```

## Expected Results

### Performance Targets:

- **Fast Path**: < 3 seconds
- **Standard Path**: < 15 seconds
- **Comprehensive Path**: < 30 seconds
- **Cache Hits**: < 1 second

### Success Indicators:

- ✅ WebSocket connection established
- ✅ Query classification working
- ✅ Parallel processing enabled
- ✅ Cache hit rates > 70%
- ✅ Significant response time improvements

## Troubleshooting

### Common Issues:

1. **"Import Error" for optimized components**

   ```bash
   # Fall back to regular agent
   python main.py
   ```

2. **WebSocket connection failed**

   ```bash
   # Check MCP server is running with WebSocket support
   curl http://localhost:8000/health
   ```

3. **Port already in use**
   ```bash
   # Kill existing processes
   pkill -f "python.*main"
   # Or use different ports
   export PORT=8002
   ```

### Debug Commands:

```bash
# Check what's running
ps aux | grep python
netstat -tlnp | grep :800

# View logs
tail -f logs/nlp_agent.log
tail -f /tmp/mcp_server.log
```

## Performance Monitoring

Monitor these metrics during testing:

1. **Response Times**: Should show 60-70% improvement
2. **Cache Hit Rate**: Should reach 70-80%
3. **WebSocket Stats**: Connection should stay stable
4. **Query Classification**: Should route to appropriate paths

## Next Steps After Testing

1. **If tests pass**: Deploy to production
2. **If tests fail**: Check logs and troubleshoot
3. **Performance tuning**: Adjust cache settings and timeouts
4. **Load testing**: Test with multiple concurrent requests

---

**Quick Test Command:**

```bash
# One-line test to verify everything works
cd "/home/obaidsafi31/Desktop/Agentic BI /agents/nlp-agent" && ./test_optimized_system.sh
```
