FROM python:3.11-alpine3.17 as builder


ENV SCRIPTS_VERSION=3.8.0
ENV SCRIPTS_OUTPUT_DIR=/app/static

COPY ./requirements.txt /app/requirements.txt
COPY ./utils /app/utils/

RUN apk update
RUN apk add --no-cache gcc g++ musl-dev rust cargo patchelf wget
RUN python -m pip install --no-cache-dir --upgrade pip setuptools
RUN python -m pip install --no-cache-dir -r /app/requirements.txt
RUN sh /app/utils/download_scripts.sh

FROM python:3.11-alpine3.17

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apk update && apk add --no-cache libstdc++  # orjson dependency

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY . /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
