FROM python:3.14.4-alpine3.23

COPY --from=ghcr.io/astral-sh/uv:0.11.6-python3.14-alpine3.23 /usr/local/bin/uv /usr/local/bin/uv

# Space-separated list of optional dependency groups to install, e.g.
#   docker build --build-arg EXTRAS="apm sentry" .
# Corresponds to [project.optional-dependencies] in pyproject.toml.
ARG EXTRAS=""
ARG TARGETOS
ARG TARGETARCH
ARG TARGETVARIANT

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON=python3.14

WORKDIR /app

# Install build dependencies and runtime libraries.
RUN --mount=type=cache,id=root-cache-${TARGETOS}-${TARGETARCH}${TARGETVARIANT},sharing=locked,target=/root/.cache \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    apk update && \
    apk add --no-cache \
        g++ \
        libgcc \
        curl \
        tini && \
    extra_args="" && \
    for extra in ${EXTRAS}; do extra_args="${extra_args} --extra ${extra}"; done && \
    uv sync --locked --no-install-project ${extra_args} && \
    apk del g++ && \
    rm -rf /var/cache/apk/*

WORKDIR /app/simple_snowplow

COPY ./simple_snowplow /app/simple_snowplow

RUN --mount=type=cache,id=root-cache-${TARGETOS}-${TARGETARCH}${TARGETVARIANT},sharing=locked,target=/root/.cache \
    uv run cli.py scripts download --version 4.6.9 --output_dir static --force

# Use tini as init to properly handle signals
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
