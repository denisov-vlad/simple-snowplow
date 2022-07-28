# simple-snowplow
A clear backend for Snowplow to work with raw data

## Installation

### Local
1. Install docker and docker-compose.
2. Download scripts from [snowplow-javascript-tracker](https://github.com/snowplow/snowplow-javascript-tracker) repo:
```shell
sh ./simple_snowplow/utils/download_scripts.sh
```
3. Run `docker-compose`. It will build application image if necessary.
```shell
docker-compose build
```
4. [Set up database](docs/database.md).
5. Run service:
```shell
docker-compose up
```

### Production
1. Install [ClickHouse](https://clickhouse.com/docs/en/quick-start).
2. [Set up database](docs/database.md).
3. Build docker image:
```shell
docker build -t simple-snowplow ./simple_snowplow
```
4. Run container in simple way (but better to use k8s or alternatives):
```shell
docker run -d -p 8000:80 simple-snowplow
```

## Usage

Now you are able to set up Snowplow on frontend.
Detailed guide is available at [Snowplow website](https://docs.snowplowanalytics.com/docs/collecting-data/collecting-from-own-applications/javascript-trackers/javascript-tracker/web-quick-start-guide/).
