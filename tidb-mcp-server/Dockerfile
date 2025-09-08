# Ultra-fast build - minimal dependencies (no venv needed in Docker)
FROM python:3.11-slim

WORKDIR /app

# Install only essential dependencies in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Create user quickly
RUN useradd -m tidbmcp && chown tidbmcp:tidbmcp /app

# Copy source code directly (skip complex dependency management for now)
COPY --chown=tidbmcp:tidbmcp src/ ./src/
COPY --chown=tidbmcp:tidbmcp pyproject.toml ./

# Install minimal dependencies for HTTP API only - directly to system Python
RUN uv pip install --system \
    fastapi==0.115.5 \
    uvicorn==0.32.1 \
    pydantic==2.11.7 \
    pydantic-settings==2.6.1 \
    aiohttp==3.9.0 \
    fastmcp==2.12.2 \
    PyMySQL

# Create required directories
RUN mkdir -p logs cache && chown -R tidbmcp:tidbmcp /app

USER tidbmcp

ENV PYTHONPATH="/app/src"

EXPOSE 8000

# Simple startup command
CMD ["python", "-c", "import uvicorn; uvicorn.run('tidb_mcp_server.http_api:app', host='0.0.0.0', port=8000)"]