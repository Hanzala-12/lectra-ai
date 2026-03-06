# Multi-stage Dockerfile for production deployment

FROM python:3.10-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy application code
COPY src/ ./src/
COPY backend.py config.yaml ./

# Create directories for models and outputs
# Models will be downloaded on first use or mounted as volumes
RUN mkdir -p /app/models /app/outputs

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"]
