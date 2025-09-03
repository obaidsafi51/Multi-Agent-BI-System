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

# Install Python dependencies with uv (faster than pip)
RUN uv sync --frozen --no-dev

# Copy source code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI server using uv run
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]