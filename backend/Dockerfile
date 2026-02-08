# Multi-stage build for Python application
FROM python:3.11-slim as builder

# Install system dependencies for document processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-vie \
    poppler-utils \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files and source code
COPY pyproject.toml ./
COPY agents ./agents
COPY api ./api
COPY config ./config
COPY database ./database
COPY domain ./domain
COPY services ./services
COPY utils ./utils
COPY workflow ./workflow
COPY scripts ./scripts
COPY __init__.py ./

# Install Python dependencies
# Note: Use pip in Docker for simplicity. UV is recommended for local dev.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-vie \
    poppler-utils \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN mkdir -p /app/logs /app/uploads /app/data && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

