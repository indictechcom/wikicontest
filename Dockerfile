# Multi-stage production Dockerfile for WikiContest
# Stage 1: Build frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Build frontend for production
RUN npm run build

# Stage 2: Production backend with built frontend
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ .

# Copy built frontend from previous stage
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Create necessary directories
RUN mkdir -p logs uploads

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port (Toolforge sets $PORT)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Run with Gunicorn
CMD exec gunicorn --bind=0.0.0.0:$PORT --workers=4 --access-logfile - --error-logfile - "app:app"
