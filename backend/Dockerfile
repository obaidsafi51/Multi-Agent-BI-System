# Use slim-buster for better compatibility and smaller size
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies in a single RUN command
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# Copy dependency files first for better layer caching
COPY --chown=appuser:appuser pyproject.toml uv.lock* ./

# Install Python dependencies directly to system Python (no venv needed in containers)
RUN uv pip install --system \
    fastapi==0.115.5 \
    uvicorn[standard]==0.32.1 \
    sqlalchemy==2.0.35 \
    pydantic==2.11.7 \
    python-dotenv==1.0.0 \
    aiofiles==24.1.0 \
    structlog==23.2.0 \
    pymysql==1.1.0 \
    cryptography==43.0.3 \
    redis==5.0.1 \
    aio-pika==9.4.3 \
    celery==5.4.0 \
    kombu==5.4.2 \
    websockets==13.1 \
    httpx==0.28.1 \
    aiohttp==3.11.10 \
    pyjwt==2.10.1 \
    passlib[bcrypt]==1.7.4 \
    python-multipart==0.0.18 \
    slowapi==0.1.9

# Copy source code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Start FastAPI server using uvicorn directly (no venv needed)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]