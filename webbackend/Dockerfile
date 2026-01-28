# Stage 1: Build stage - install all dependencies
FROM python:3.12-slim-bullseye AS builder

WORKDIR /build

# Install build dependencies for any compiled Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual env for clean copy
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies first (cached layer)
COPY requirements.txt core_requirements.txt
COPY webbackend/requirements.txt backend_requirements.txt
RUN pip install --no-cache-dir -r core_requirements.txt && \
    pip install --no-cache-dir -r backend_requirements.txt

# Stage 2: Runtime stage - minimal image with pre-installed deps
FROM python:3.12-slim-bullseye

WORKDIR /app

# Install ONLY g++ runtime (not full build-essential) in a single layer
# Use --no-install-recommends to minimize size
RUN apt-get update && \
    apt-get install -y --no-install-recommends g++ && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Copy virtual env from builder (all deps pre-installed)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY webbackend/src/ .
COPY py2c/ py2c/

# Pre-compile Python bytecode for faster startup
RUN python -m compileall -q .

# Use exec form for proper signal handling
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
