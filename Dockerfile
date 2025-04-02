FROM python:3.13-alpine3.21 AS builder

WORKDIR /build

# Install build dependencies
RUN apk update && \
    apk add --no-cache \
        g++ \
        musl-dev \
        curl

# Use uv for faster pip install
RUN python -m pip install --no-cache-dir uv

# Only copy requirements file for better layer caching
COPY ./requirements.txt /build/requirements.txt

# Install dependencies
RUN python -m uv pip install --system \
    --no-cache-dir \
    -r /build/requirements.txt


# Create the final image
FROM python:3.13-alpine3.21

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SCRIPTS_OUTPUT_DIR=/app/static \
    SCRIPTS_VERSION=4.4.0

# Create a non-root user to run the app
RUN addgroup -S appgroup && \
    adduser -S appuser -G appgroup

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apk update && \
    apk add --no-cache \
        libstdc++ \
        curl \
        tini && \
    rm -rf /var/cache/apk/*

# Copy Python dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY . /app

# Download required scripts
RUN sh /app/utils/download_scripts.sh && \
    # Set proper permissions
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

# Use tini as init to properly handle signals
ENTRYPOINT ["/sbin/tini", "--"]

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--log-level", "warning"]
