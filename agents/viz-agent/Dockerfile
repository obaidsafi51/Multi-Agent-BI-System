FROM python:3.11-slim

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

# increase uv's HTTP timeout
ENV UV_HTTP_TIMEOUT=120

# Install Python dependencies directly to system Python (no venv needed in containers)
RUN uv pip install --system \
    fastapi==0.115.5 \
    uvicorn==0.32.1 \
    pydantic==2.11.7 \
    python-dotenv==1.0.0 \
    redis==5.0.1 \
    pika==1.3.2 \
    plotly==5.24.1 \
    matplotlib==3.9.2 \
    pandas==2.2.3 \
    numpy==1.26.4 \
    orjson==3.10.12 \
    structlog==23.2.0 \
    reportlab==4.2.5 \
    openpyxl==3.1.5 \
    psutil==6.1.0 \
    kaleido==0.2.1 \
    websockets==12.0

# Copy source code and shared models
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser shared/ ./shared/
COPY --chown=appuser:appuser main.py main_fixed.py standardized_response_template.py websocket_server.py startup.py ./

# Switch to non-root user
USER appuser

# Start both HTTP and WebSocket servers using startup script
CMD ["python", "startup.py"]