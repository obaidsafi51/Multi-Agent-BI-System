# Optimized NLP Agent Dockerfile for Production
FROM python:3.11-slim AS runtime

# Install system dependencies and curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install UV for fast dependency management
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock* ./

# Install dependencies directly to system Python (no venv needed in Docker)
RUN uv pip install --system .

# Set environment variables
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# Copy source code, shared models, and WebSocket server
COPY src/ ./src/
COPY shared/ ./shared/
COPY main_optimized.py ./main.py
COPY performance_config.py ./performance_config.py
# websocket_server.py removed - NLP agent acts as client only
COPY startup.py ./startup.py

# Create directories and non-root user
RUN mkdir -p logs cache && \
    groupadd -r nlpagent && \
    useradd -r -g nlpagent nlpagent && \
    chown -R nlpagent:nlpagent /app

# Switch to non-root user
USER nlpagent

# Environment variables for container
ENV HOST=0.0.0.0
ENV PORT=8001

# Expose main API port only (no WebSocket server)
EXPOSE 8001

# Health check for optimized agent
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Start HTTP and WebSocket server using main.py directly
CMD ["python", "main.py"]
