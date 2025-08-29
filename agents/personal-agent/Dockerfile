FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv

# Copy pyproject.toml and uv.lock first for better caching
COPY pyproject.toml uv.lock* ./

# Install Python dependencies with uv
RUN uv sync --frozen

# Copy source code
COPY . .

# Start the Personalization agent using uv run
CMD ["uv", "run", "python", "main.py"]