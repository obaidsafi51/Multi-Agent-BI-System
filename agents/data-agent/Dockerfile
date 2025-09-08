# Ultra-fast data agent build (no venv needed in Docker)
FROM python:3.11-slim

WORKDIR /app

# Minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Create user
RUN useradd -m appuser && chown appuser:appuser /app

# Copy source code directly
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser main.py ./

# Install only essential dependencies directly to system Python
RUN uv pip install --system \
    fastapi==0.115.5 \
    uvicorn==0.32.1 \
    pydantic==2.11.7 \
    python-dotenv==1.0.0 \
    redis==5.0.1 \
    sqlalchemy==2.0.35 \
    pymysql==1.1.0 \
    aiomysql==0.2.0 \
    aiohttp==3.9.0 \
    structlog==23.2.0

USER appuser

CMD ["python", "-u", "main.py"]