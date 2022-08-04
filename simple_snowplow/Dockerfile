FROM python:3.9-alpine3.14 as builder

ENV SCRIPTS_VERSION=3.5.0
ENV SCRIPTS_OUTPUT_DIR=/app/static

COPY . /app

RUN apk add --no-cache gcc g++ musl-dev rust cargo patchelf wget
RUN python -m pip install -r /app/requirements.txt
RUN sh /app/utils/download_scripts.sh


FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9-alpine3.14-2021-10-02

ENV UVICORN_LOG_LEVEL=warning
ENV UVICORN_PORT=5000
ENV WORKER_CLASS=uvicorn.workers.UvicornH11Worker
ENV PYTHONUNBUFFERED=1

COPY . /app
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /app/static /app/static

RUN pip install --upgrade fastapi
