FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and frontend source files
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# Set working directory to backend
WORKDIR /app/backend

# Create uploads directory for persistent storage
RUN mkdir -p /app/backend/uploads

EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Start FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
