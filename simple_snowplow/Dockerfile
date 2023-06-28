FROM python:3.11-alpine3.18 as builder


ENV SCRIPTS_VERSION=3.13.0
ENV SCRIPTS_OUTPUT_DIR=/app/static
ENV CARGO_NET_GIT_FETCH_WITH_CLI=true


RUN apk update
RUN apk add gcc g++ rust musl-dev cargo patchelf wget maturin git
RUN git clone -b 3.9.1 https://github.com/ijl/orjson.git
RUN cd orjson && maturin build --release --strip
RUN python -m pip install --upgrade pip setuptools wheel
RUN python -m pip install --no-index --find-links=/orjson/target/wheels orjson

COPY ./requirements.txt /app/requirements.txt
RUN python -m pip install -r /app/requirements.txt

COPY ./utils /app/utils/
RUN sh /app/utils/download_scripts.sh

FROM python:3.11-alpine3.18

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apk update && apk add --no-cache libstdc++  # orjson dependency

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY . /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--log-level", "warning"]
