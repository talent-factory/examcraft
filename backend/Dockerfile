FROM python:3.11-slim

WORKDIR /app

# Build arguments
ARG BUILD_TIMESTAMP
ENV BUILD_TIMESTAMP=${BUILD_TIMESTAMP}

# Install system dependencies
# Note: PyMuPDF (fitz) requires mupdf libraries for PDF processing
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    openssh-client \
    libpq-dev \
    python3-dev \
    libmagic1 \
    libmupdf-dev \
    mupdf \
    && rm -rf /var/lib/apt/lists/*

# Add GitHub SSH host key to known_hosts
RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts

# Copy requirements and pyproject.toml first for better caching
COPY backend/requirements.txt .
COPY pyproject.toml /app/pyproject.toml

# Install Python dependencies (SSH mount for private git repos)
RUN --mount=type=ssh pip install --no-cache-dir -r requirements.txt

# Install additional dependencies from pyproject.toml (qdrant-client, sentence-transformers, etc.)
RUN pip install --no-cache-dir -e .

# Copy application code
COPY backend/ .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
