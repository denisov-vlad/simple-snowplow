FROM python:3.11-alpine3.17

WORKDIR /app

ENV SCRIPTS_VERSION=3.8.0
ENV SCRIPTS_OUTPUT_DIR=/app/static

COPY . /app

RUN apk update \
    && apk add --no-cache gcc g++ musl-dev rust cargo patchelf wget \
    && rm -rf /var/cache/apk/* \
    && python -m pip install --upgrade pip setuptools \
    && python -m pip install -r /app/requirements.txt  \
    && sh /app/utils/download_scripts.sh \
    && apk del g++ rust cargo patchelf wget

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
