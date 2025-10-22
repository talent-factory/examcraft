FROM python:3.11-slim

WORKDIR /app

# Build arguments
ARG BUILD_TIMESTAMP
ENV BUILD_TIMESTAMP=${BUILD_TIMESTAMP}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and pyproject.toml first for better caching
COPY packages/core/backend/requirements.txt .
COPY pyproject.toml /app/pyproject.toml

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies from pyproject.toml (qdrant-client, sentence-transformers, etc.)
RUN pip install --no-cache-dir -e .

# Copy application code
COPY packages/core/backend/ .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
