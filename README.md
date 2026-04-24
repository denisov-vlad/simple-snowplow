# Simple Snowplow

Simple Snowplow is a lightweight, self-hosted analytics collector compatible with the Snowplow analytics protocol. It allows you to collect event data from websites and applications while maintaining full control over your data and infrastructure.

## Features

- Compatible with Snowplow JavaScript tracker
- Collects web analytics data including page views, events, and user information
- Stores data in ClickHouse for high-performance analytics queries
- Optional RabbitMQ-backed ingest mode with batch worker
- Allowlisted proxy endpoint for serving third-party analytics scripts from your own domain
- Configurable data retention and storage settings
- Horizontal scaling capabilities with ClickHouse cluster support
- Built with FastAPI (Python 3.14) for high performance
- Optional demo mode for easy testing

## Architecture

Simple Snowplow consists of the following components:

1. **FastAPI Backend**: Handles incoming tracking events
2. **ClickHouse Database**: Stores and processes analytics data
3. **RabbitMQ + Worker**: Optional durable buffer and batch writer for fault-tolerant ingest
4. **JavaScript Tracking Libraries**: Compatible with standard Snowplow js trackers

## Installation

### Local Development

To install Simple Snowplow for local development:

1. Make sure you have Docker and Docker Compose installed
2. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/simple-snowplow.git
   cd simple-snowplow
   ```
3. (One‑time) Initialize ClickHouse databases & tables:
   ```bash
   # Ensure ClickHouse service is up first (in a separate terminal)
   docker compose up -d clickhouse

   # Create tables (idempotent – safe to re-run)
   docker compose run app uv run python cli.py db init
   ```

4. Start the application using Docker Compose:
   ```bash
   docker compose up
   ```

### Production Deployment

For a production environment:

1. Install ClickHouse version 22.11 or later (follow the [ClickHouse documentation](https://clickhouse.com/docs/en/quick-start))
2. Build the Docker image:
   ```bash
   docker build -t simple-snowplow ./simple_snowplow
   ```
3. Set the configuration you need using environment variables (see [Configuration](#configuration))
4. Run the Docker container:
   ```bash
   docker run -d \
     -p 8000:80 \
     -e SNOWPLOW_ENV=production \
     -e SNOWPLOW_CLICKHOUSE__CONNECTION__HOST=my-clickhouse-host \
     simple-snowplow

You can supply additional configuration through more `-e` flags.

## Configuration

Simple Snowplow is configured via a **single Pydantic `BaseSettings` model**. The application reads values from environment variables using the `SNOWPLOW_` prefix and double underscores (`__`) for nesting. For example:

```bash
SNOWPLOW_COMMON__SERVICE_NAME=my-snowplow
SNOWPLOW_COMMON__DEMO=true
SNOWPLOW_CLICKHOUSE__CONNECTION__HOST=my-clickhouse-server
SNOWPLOW_COMMON__SNOWPLOW__USER_IP_HEADER=CF-Connecting-IP
SNOWPLOW_INGEST__MODE=rabbitmq
SNOWPLOW_INGEST__RABBITMQ__HOST=my-rabbitmq
```

`SNOWPLOW_COMMON__SNOWPLOW__USER_IP_HEADER` controls which request header is
used to resolve the client IP (default: `X-Forwarded-For`). If the header
contains multiple comma-separated addresses, the first valid IP is used.

The structure mirrors the configuration sections:

- `common`: Basic application options (service name, hostname, demo mode)
- `clickhouse`: Connection details and table definitions
- `ingest`: Delivery mode (`direct` or `rabbitmq`) and RabbitMQ/worker tuning
- `logging`: Format and level for application logs
- `security`: Docs availability and HTTPS enforcement
- `proxy`: Allowlist of external domains and paths that `/proxy/route/...`
  is permitted to forward to. Hosts not in `proxy.domains` get a 403; only
  `http` and `https` schemes are accepted.
- `performance`: Connection pool, concurrency, and middleware cost controls.
  For high-volume collectors, `enable_access_log=false` and
  `enable_brotli=false` remove those middleware layers entirely. To keep them
  enabled but bypass collector routes, set
  `access_log_excluded_paths='["/tracker", "/i"]'` and
  `brotli_excluded_paths='["/tracker", "/i"]'`.
- `elastic_apm`, `prometheus`, `sentry`: Optional observability integrations.
  - Elastic APM requires the `apm` extra (`uv sync --extra apm`); without it,
    tracing decorators silently no-op and enabling `elastic_apm.enabled`
    fails at startup with a clear error.
  - Sentry requires the `sentry` extra (`uv sync --extra sentry`); enabling
    `sentry.enabled` without it fails at startup with a clear error.

#### Building the Docker image with optional extras

The Dockerfile accepts a space-separated `EXTRAS` build arg mapped to
`[project.optional-dependencies]` groups. Examples:

```bash
# Lean image (default)
docker build -t simple-snowplow .

# With Elastic APM + Sentry bundled
docker build --build-arg EXTRAS="apm sentry" -t simple-snowplow .

# With Compose: export once, then build normally
SNOWPLOW_BUILD_EXTRAS="apm sentry" docker compose build app
```

You can inspect the full configuration (with defaults) via the CLI from the repository root:

```bash
uv run python simple_snowplow/cli.py settings
```

Set `SNOWPLOW_ENV` to label the running environment (e.g. `production`) — the value is propagated to logging integrations such as Sentry but does not change how configuration is loaded.

### Ingest Modes

`ingest.mode=direct`:
- API writes directly to ClickHouse on every request.
- No additional infrastructure is required.

`ingest.mode=rabbitmq`:
- API publishes events to RabbitMQ.
- A separate worker consumes the queue, batches rows by `table_group`, and writes them to ClickHouse.
- This is the mode to use when you want a durable buffer between request handling and ClickHouse availability.
- Startup wait is configurable with `SNOWPLOW_INGEST__RABBITMQ__STARTUP_TIMEOUT_SECONDS` and `SNOWPLOW_INGEST__RABBITMQ__STARTUP_RETRY_INTERVAL_MS`.

## Usage

### Database Initialization

Table creation has been moved out of the FastAPI startup sequence and is now handled explicitly via the CLI. This gives you predictable, repeatable migrations and avoids race conditions on multi-instance deployments.

You only need to run the init command when:

* First installation (fresh ClickHouse instance)
* You changed table-related configuration (e.g. engine, partitioning, cluster_name)
* Upgrading to a version that adds new tables / columns (future migrations)

Run in Docker Compose (after the image is built):
```bash
docker compose up -d clickhouse
docker compose run app uv run python cli.py db init
docker compose up -d app
```

### Queue-Backed Ingest

To enable queue-backed ingest, switch the API to RabbitMQ mode and run the worker:

```bash
SNOWPLOW_INGEST__MODE=rabbitmq docker compose --profile rabbitmq up -d rabbitmq worker app
```

Or locally from the repository root:

```bash
export SNOWPLOW_INGEST__MODE=rabbitmq
uv run python simple_snowplow/cli.py queue worker
```

In this mode the HTTP app only enqueues messages. Batch inserts into ClickHouse are performed exclusively by the worker.

The default RabbitMQ `prefetch_count` matches the default worker `batch_size`
so one-row tracking messages can fill a complete ClickHouse batch before the
timeout flush. If you tune `SNOWPLOW_INGEST__RABBITMQ__BATCH_SIZE`, tune
`SNOWPLOW_INGEST__RABBITMQ__PREFETCH_COUNT` with it unless you intentionally
prefer lower worker memory use and smaller timeout-driven inserts.

Idempotency: The command uses `CREATE DATABASE IF NOT EXISTS` and `CREATE TABLE IF NOT EXISTS`; re-running is safe. If you change schema definitions (e.g. `order_by`, `engine`) you must manually apply migrations (dropping/recreating or performing ALTER statements) – the CLI purposefully does not perform destructive changes.

Troubleshooting:
* Connection errors: ensure the hostname matches `SNOWPLOW_CLICKHOUSE__CONNECTION__HOST` (defaults to `clickhouse` inside Docker network).
* Cluster setup: set `SNOWPLOW_CLICKHOUSE__CONFIGURATION__CLUSTER_NAME` before running init so distributed tables are created.
* Permissions: use a ClickHouse user with `CREATE DATABASE` and `CREATE TABLE` privileges.

### Downloading Tracker Scripts via CLI

Instead of the shell script you can use the built-in command (run from the repository root):
```bash
uv run python simple_snowplow/cli.py scripts download
```
This will place `sp.js`, `sp.js.map`, plugin bundle, and `loader.js` copies in the repository-level `static/` directory and adjust the source map `file` field for the loader copy.

### Web Tracking

To track events from your website:

1. Include the Snowplow tracker in your HTML:
   ```html
   <script type="text/javascript">
   (function(p,l,o,w,i,n,g){if(!p[i]){p.GlobalSnowplowNamespace=p.GlobalSnowplowNamespace||[];
   p.GlobalSnowplowNamespace.push(i);p[i]=function(){(p[i].q=p[i].q||[]).push(arguments)
   };p[i].q=p[i].q||[];n=l.createElement(o);g=l.getElementsByTagName(o)[0];n.async=1;
   n.src=w;g.parentNode.insertBefore(n,g)}}(window,document,"script","//your-server.com/static/sp.js","snowplow"));

   snowplow('newTracker', 'sp', 'your-server.com', {
     appId: 'my-app',
     platform: 'web',
     post: true,
     forceSecureTracker: true
   });

   snowplow('trackPageView');
   </script>
   ```

2. Replace `your-server.com` with your Simple Snowplow server address

By default the collector allows cross-origin requests from any origin,
including credentialed browser tracker requests.

If you want to restrict that in production, configure CORS explicitly for the
sites you trust. For example, for `https://example.com`:

```bash
export SNOWPLOW_SECURITY__CORS_ALLOW_CREDENTIALS=true
export SNOWPLOW_SECURITY__CORS_ALLOWED_ORIGINS='["https://example.com"]'
```

`cors_allowed_origins` entries should be bare origins such as
`https://example.com` without a path.

### Demo Mode

To test Simple Snowplow with the built-in demo:

1. Set `common.demo = true` in your configuration
2. Access the demo page at `http://your-server.com/demo/`
3. Events will be tracked and stored in your ClickHouse database

### Querying Data

To query the collected data, connect to your ClickHouse instance:

```bash
docker exec -it simple-snowplow-ch clickhouse-client
```

Example queries:

```sql
-- Get page views from the last 24 hours
SELECT time, page, refr, device_id, session_id
FROM snowplow.local
WHERE event_type = 'page_view'
  AND time > now() - INTERVAL 1 DAY
ORDER BY time DESC;

-- Count events by type
SELECT event_type, count() as events
FROM snowplow.local
GROUP BY event_type
ORDER BY events DESC;
```

## Troubleshooting

### Common Issues

1. **Connection refused to ClickHouse**
   - Check that ClickHouse is running and accessible
   - Verify the host and port in your configuration
   - Ensure firewall rules allow connections

2. **No data being collected**
   - Check browser console for JavaScript errors
   - Verify tracking endpoint is correctly configured in your tracker
   - Check server logs for any errors

3. **Missing data in queries**
   - Verify the table name (it may be different if you configured a custom name)
   - Check if data partitioning is working as expected

### Logs

To view application logs:

```bash
docker logs -f simple-snowplow
```

For more verbose logging, set `logging.level = "DEBUG"` in your configuration.

## Development

### Setting Up the Development Environment

1. Create a virtual environment and install uv (if not already installed):
   ```bash
   # Install uv (if not already installed)
   curl -sSf https://astral.sh/uv/install.sh | sh
   # Or on macOS with Homebrew
   # brew install uv

   # Create a virtual environment with uv
   uv venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Install development tools:
   ```bash
   uv pip install -G dev
   pre-commit install
   ```

4. Run the application locally:
   ```bash
   cd simple_snowplow
   uv run uvicorn main:app --reload
   ```

### Running Tests

```bash
uv run pytest
```

### Using Docker Compose with Development Mode

```bash
docker compose up --watch
```

This activates the development mode which automatically:
- Syncs your local code changes to the container without rebuilding
- Rebuilds the container only when dependencies change (when uv.lock is modified)

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file.
