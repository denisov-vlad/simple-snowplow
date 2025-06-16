FROM python:3.13-alpine3.21

COPY --from=ghcr.io/astral-sh/uv:python3.13-alpine /usr/local/bin/uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON=python3.13

WORKDIR /app

# Install build dependencies and runtime libraries
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=utils/download_scripts.sh,target=utils/download_scripts.sh \
    apk update && \
    apk add --no-cache \
        g++ \
        libgcc \
        curl \
        tini && \
    uv sync --frozen && \
    sh ./utils/download_scripts.sh && \
    apk del g++ && \
    rm -rf /var/cache/apk/*

WORKDIR /app/simple_snowplow

COPY ./simple_snowplow /app/simple_snowplow

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

# Use tini as init to properly handle signals
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
