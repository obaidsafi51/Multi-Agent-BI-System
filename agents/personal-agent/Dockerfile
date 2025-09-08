FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies in a single RUN command
RUN apt-get update && apt-get install -y gcc curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir uv

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# Copy dependency files first for better layer caching
COPY --chown=appuser:appuser pyproject.toml uv.lock* ./

# Install Python dependencies directly to system Python (no venv needed in containers)
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Start the Personalization agent using system python
CMD ["python", "main.py"]