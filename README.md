# simple-snowplow
A clear backend for Snowplow to work with raw data

## Installation

### Local
1. Install docker and docker-compose.
2. Download scripts from the [snowplow-javascript-tracker](https://github.com/snowplow/snowplow-javascript-tracker) repo:
```shell
sh ./simple_snowplow/utils/download_scripts.sh
```
3. Run `docker-compose`. It will build an application image if necessary.
```shell
docker-compose -f docker-compose-dev.yml up
```


### Production
1. Install [ClickHouse](https://clickhouse.com/docs/en/quick-start).
2. Build docker image:
```shell
docker build -t simple-snowplow ./simple_snowplow
```
3. Run container on your host machine (but better to use k8s or alternatives):
```shell
docker run -d -p 8000:80 simple-snowplow
```

## Usage

### Local

1. Open http://127.0.0.1:8000/demo/ page.
2. Open the `Network` tab, and you will see request to the `/tracker` endpoint.
3. Open clickhouse client: `docker exec -it simple-snowplow-ch clickhouse-client`
4. Check data in a table:
```clickhouse
SELECT * FROM snowplow.buffer LIMIT 1
```
5. Done!

### Production

Now you can set up a Snowplow on the frontend.
A detailed guide is available on the [Snowplow website](https://docs.snowplowanalytics.com/docs/collecting-data/collecting-from-own-applications/javascript-trackers/javascript-tracker/web-quick-start-guide/).

TBD
