# ==========================================
# Stage 1: Build the React 18 Frontend
# ==========================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy source code and build production bundle
COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Production Python Backend
# ==========================================
FROM python:3.12-slim AS production

# Environment configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    HOST=0.0.0.0 \
    ENVIRONMENT=production

WORKDIR /app

# Install system dependencies needed for compiling C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application directories
COPY backend/ /app/backend/
COPY data/ /app/data/
COPY scripts/ /app/scripts/
COPY shared/ /app/shared/
COPY run.py /app/run.py

# Copy precompiled frontend assets from frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Expose container port (compatible with Cloud Run, Render, Railway $PORT)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Launch the unified platform server
CMD ["python", "run.py"]
