FROM python:3.14.2-alpine3.23

COPY --from=ghcr.io/astral-sh/uv:0.9.26-python3.14-alpine3.23 /usr/local/bin/uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON=python3.14

WORKDIR /app

# Install build dependencies and runtime libraries
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    apk update && \
    apk add --no-cache \
        g++ \
        libgcc \
        curl \
        tini && \
    uv sync --locked --no-install-project && \
    apk del g++ && \
    rm -rf /var/cache/apk/*

WORKDIR /app/simple_snowplow

COPY ./simple_snowplow /app/simple_snowplow

RUN uv run cli.py scripts download --version 4.6.8 --output_dir static --force

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

# Use tini as init to properly handle signals
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
