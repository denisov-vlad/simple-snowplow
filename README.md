# simple-snowplow

Simple Snowplow is a backend application designed to work with raw data from Snowplow. This guide provides instructions on how to install, configure, and use the application.

## Installation

### Local Installation

To install Simple Snowplow locally, follow these steps:

1. Make sure you have Docker and Docker Compose installed on your machine.
2. Run the following command to start the application using Docker Compose:
   ```shell
   docker-compose up
   ```

### Production Installation

For a production environment, follow these steps:

1. Install ClickHouse version 22.11 or later. You can refer to the [ClickHouse documentation](https://clickhouse.com/docs/en/quick-start) for installation instructions.
2. Build the Docker image using the following command:
   ```shell
   docker build -t simple-snowplow ./simple_snowplow
   ```
3. Run the Docker container on your host machine. It is recommended to use Kubernetes (k8s) or alternative orchestration tools for production deployments. However, for a quick start, you can use the following command:
   ```shell
   docker run -d -p 8000:80 simple-snowplow
   ```

## Usage

### Local Usage

To use Simple Snowplow locally, follow these steps:

1. Open http://127.0.0.1:8000/demo/ in your web browser.
2. Open the browser's developer tools and navigate to the "Network" tab. You should see requests to the `/tracker` endpoint.
3. To view the data collected by Simple Snowplow, open the ClickHouse client using the following command:
   ```shell
   docker exec -it simple-snowplow-ch clickhouse-client
   ```
4. Once inside the ClickHouse client, you can query the data in the "snowplow.local" table. For example:
   ```clickhouse
   SELECT * FROM snowplow.local LIMIT 1
   ```
5. That's it! You have successfully set up Simple Snowplow locally.

### Production Usage

In a production environment, you can integrate Simple Snowplow with Snowplow on the frontend. Refer to the [Snowplow website](https://docs.snowplowanalytics.com/docs/collecting-data/collecting-from-own-applications/javascript-trackers/javascript-tracker/web-quick-start-guide/) for a detailed guide on setting up Snowplow.

TBD

## Development

### Initial Setup

To contribute to the development of Simple Snowplow, follow these steps:

1. Clone the repository.
2. Create a virtual environment and activate it.
3. Install the `pre-commit` tool using pip:
   ```shell
   pip install pre-commit
   ```
4. Run `pre-commit` for the first time to set up the Git pre-commit hooks:
   ```shell
   pre-commit run -a
   ```
5. Download Snowplow scripts:
   ```shell
   sh ./simple_snowplow/utils/download_scripts.sh
   ```

Feel free to modify or extend this documentation as needed.
