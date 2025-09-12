# Optimized TiDB MCP Server Dockerfile for Production
FROM python:3.11-slim AS runtime

# Install system dependencies and curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV for fast dependency management
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies directly to system Python (no venv needed in Docker)
RUN uv pip install --system .

# Set environment variables
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1
ENV USE_HTTP_API=true
ENV DOCKER_ENV=true

# Copy source code
COPY src/ ./src/

# Create directories and non-root user
RUN mkdir -p logs cache && \
    useradd -m tidbmcp && \
    chown -R tidbmcp:tidbmcp /app

# Switch to non-root user
USER tidbmcp

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the TiDB MCP server directly with system Python
CMD ["python", "-m", "tidb_mcp_server.main"]
