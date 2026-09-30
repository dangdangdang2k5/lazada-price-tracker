# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend with FastAPI & Playwright Chromium
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install --with-deps chromium

# Copy backend source code & products data
COPY backend/ .
COPY products.json /app/products.json

# Copy built frontend assets to static folder inside backend
COPY --from=frontend-builder /app/frontend/dist ./static

ENV PORT=8000 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Run FastAPI with uvicorn listening on the port provided by Render / Cloud
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
