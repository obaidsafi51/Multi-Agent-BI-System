"""
Configuration for Enhanced NLP Agent with WebSocket optimizations
"""
import os

# Environment Variables Configuration
ENVIRONMENT_VARIABLES = {
    # WebSocket MCP Server
    "MCP_SERVER_WS_URL": os.getenv("MCP_SERVER_WS_URL", "ws://localhost:8000/ws"),
    "MCP_SERVER_HTTP_URL": os.getenv("MCP_SERVER_HTTP_URL", "http://localhost:8000"),
    
    # KIMI API Configuration
    "KIMI_API_KEY": "your_kimi_api_key_here",
    "KIMI_API_BASE_URL": "https://api.moonshot.ai/v1",
    "KIMI_MODEL": "moonshot-v1-8k",
    
    # Agent Configuration
    "AGENT_ID": "nlp-agent-001",
    "AGENT_TYPE": "nlp",
    "HOST": "0.0.0.0",
    "PORT": "8001",
    
    # Performance Configuration
    "MAX_CONCURRENT_REQUESTS": "10",
    "REQUEST_TIMEOUT": "30",
    "CONNECTION_POOL_SIZE": "20",
    "RATE_LIMIT_PER_MINUTE": "100",
    
    # Cache Configuration
    "CACHE_TTL_SECONDS": "300",
    "CACHE_MAX_SIZE": "1000",
    "SEMANTIC_SIMILARITY_THRESHOLD": "0.85",
    
    # WebSocket Configuration
    "WS_HEARTBEAT_INTERVAL": "30",
    "WS_RECONNECT_DELAY": "5",
    "WS_MAX_RECONNECT_ATTEMPTS": "5",
    "WS_BATCH_SIZE": "10",
    "WS_BATCH_TIMEOUT": "1.0",
    
    # Logging Configuration
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "text",
    
    # Development Settings
    "DEBUG": "false",
    "RELOAD": "false"
}

# Query Classification Patterns
QUERY_PATTERNS = {
    "fast_path": [
        r"what is",
        r"how many",
        r"count",
        r"sum",
        r"average",
        r"simple",
        r"basic"
    ],
    "comprehensive_path": [
        r"complex analysis",
        r"correlation",
        r"trend",
        r"forecast",
        r"detailed report",
        r"comprehensive"
    ]
}

# Processing Path Configuration
PROCESSING_PATHS = {
    "fast": {
        "description": "Quick responses for simple queries",
        "timeout": 5,
        "cache_priority": "high",
        "parallel_processing": False
    },
    "standard": {
        "description": "Balanced processing for most queries",
        "timeout": 15,
        "cache_priority": "medium",
        "parallel_processing": True
    },
    "comprehensive": {
        "description": "Detailed processing for complex queries",
        "timeout": 30,
        "cache_priority": "low",
        "parallel_processing": True
    }
}

# Performance Monitoring
METRICS_CONFIG = {
    "track_response_times": True,
    "track_cache_hit_rate": True,
    "track_websocket_stats": True,
    "track_query_complexity": True,
    "metrics_retention_days": 7
}

def get_env_file_content():
    """Generate .env file content"""
    content = "# Enhanced NLP Agent Configuration\n\n"
    
    for key, value in ENVIRONMENT_VARIABLES.items():
        content += f"{key}={value}\n"
    
    return content

def generate_docker_compose():
    """Generate docker-compose.yml for the optimized setup"""
    return """
version: '3.8'

services:
  nlp-agent:
    build: 
      context: .
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    environment:
      - MCP_SERVER_WS_URL=ws://tidb-mcp-server:8000/ws
      - MCP_SERVER_HTTP_URL=http://tidb-mcp-server:8000
      - KIMI_API_KEY=${KIMI_API_KEY}
      - KIMI_API_BASE_URL=https://api.moonshot.ai/v1
      - AGENT_ID=nlp-agent-001
      - AGENT_TYPE=nlp
      - MAX_CONCURRENT_REQUESTS=10
      - CONNECTION_POOL_SIZE=20
      - CACHE_TTL_SECONDS=300
      - LOG_LEVEL=INFO
    depends_on:
      - tidb-mcp-server
    networks:
      - agentic-bi
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  tidb-mcp-server:
    build:
      context: ../../tidb-mcp-server
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - TIDB_HOST=${TIDB_HOST}
      - TIDB_PORT=${TIDB_PORT}
      - TIDB_USER=${TIDB_USER}
      - TIDB_PASSWORD=${TIDB_PASSWORD}
      - TIDB_DATABASE=${TIDB_DATABASE}
      - USE_HTTP_API=true
      - LOG_LEVEL=INFO
    networks:
      - agentic-bi
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  agentic-bi:
    driver: bridge

"""

if __name__ == "__main__":
    print("Enhanced NLP Agent Configuration")
    print("=" * 40)
    print("\n.env file content:")
    print(get_env_file_content())
    print("\ndocker-compose.yml content:")
    print(generate_docker_compose())
