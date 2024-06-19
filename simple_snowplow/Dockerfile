FROM python:3.12-alpine3.20 as builder

RUN apk update
RUN apk add g++
RUN python -m pip install --upgrade pip setuptools wheel

COPY ./requirements.txt /app/requirements.txt
RUN python -m pip install -r /app/requirements.txt


FROM python:3.12-alpine3.20

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apk update && apk add --no-cache curl libstdc++  # orjson dependency

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY . /app

ENV SCRIPTS_OUTPUT_DIR=/app/static
ENV SCRIPTS_VERSION=3.15.0
RUN sh /app/utils/download_scripts.sh

HEALTHCHECK --interval=10s --timeout=1s CMD curl -f http://localhost:80/ || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--log-level", "warning"]
