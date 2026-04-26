# evnt

`evnt` is a lightweight, self-hosted event collector that **implements the Snowplow tracker wire protocol** so it can receive events from the upstream Snowplow open-source JavaScript and mobile trackers. It allows you to collect event data from websites and applications while maintaining full control over your data and infrastructure.

> **Disclaimer.** "Snowplow" is a trademark of Snowplow Analytics Ltd.
> This is an independent open-source project that interoperates with the
> publicly documented Snowplow tracker protocol and bundles the official
> Snowplow JavaScript tracker (BSD-3-Clause) and Iglu Central schemas
> (Apache-2.0) **unmodified**. It is **not affiliated with, sponsored by,
> or endorsed by Snowplow Analytics Ltd.** See
> [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for full attribution.

## Features

- Accepts events from the official Snowplow JavaScript tracker over the documented HTTP tracker protocol
- Collects web analytics data including page views, events, and user information
- Stores data in ClickHouse for high-performance analytics queries
- Optional RabbitMQ-backed ingest mode with batch worker
- Allowlisted proxy endpoint for serving third-party analytics scripts from your own domain
- Configurable data retention and storage settings
- Horizontal scaling capabilities with ClickHouse cluster support
- Built with FastAPI (Python 3.14) for high performance
- Optional demo mode for easy testing

## Architecture

`evnt` consists of the following components:

1. **FastAPI Backend**: Handles incoming tracking events
2. **ClickHouse Database**: Stores and processes analytics data
3. **RabbitMQ + Worker**: Optional durable buffer and batch writer for fault-tolerant ingest
4. **JavaScript Tracking Libraries**: The unmodified Snowplow JavaScript tracker and plugins (BSD-3-Clause), fetched from the official Snowplow GitHub Releases via `cli.py scripts download`

## Installation

### Local Development

To install `evnt` for local development:

1. Make sure you have Docker and Docker Compose installed
2. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/evnt.git
   cd evnt
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
   docker build -t evnt ./evnt
   ```
3. Set the configuration you need using environment variables (see [Configuration](#configuration))
4. Run the Docker container:
   ```bash
   docker run -d \
     -p 8000:80 \
     -e EVNT_ENV=production \
     -e EVNT_CLICKHOUSE__CONNECTION__HOST=my-clickhouse-host \
     evnt

You can supply additional configuration through more `-e` flags.

## Configuration

`evnt` is configured via a **single Pydantic `BaseSettings` model**. The application reads values from environment variables using the `EVNT_` prefix and double underscores (`__`) for nesting. For example:

```bash
EVNT_COMMON__SERVICE_NAME=my-evnt
EVNT_COMMON__DEMO=true
EVNT_CLICKHOUSE__CONNECTION__HOST=my-clickhouse-server
EVNT_COMMON__SNOWPLOW__USER_IP_HEADER=CF-Connecting-IP
EVNT_INGEST__MODE=rabbitmq
EVNT_INGEST__RABBITMQ__HOST=my-rabbitmq
```

`EVNT_COMMON__SNOWPLOW__USER_IP_HEADER` controls which request header is
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
  `brotli_excluded_paths='["/tracker", "/i"]'`. Frequent health probes reuse
  backend status for `healthcheck_cache_ttl_seconds` seconds; set it to `0` to
  probe ClickHouse or RabbitMQ on every request.
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
docker build -t evnt .

# With Elastic APM + Sentry bundled
docker build --build-arg EXTRAS="apm sentry" -t evnt .

# With Compose: export once, then build normally
EVNT_BUILD_EXTRAS="apm sentry" docker compose build app
```

You can inspect the full configuration (with defaults) via the CLI from the repository root:

```bash
uv run python evnt/cli.py settings
```

Set `EVNT_ENV` to label the running environment (e.g. `production`) — the value is propagated to logging integrations such as Sentry but does not change how configuration is loaded.

### Ingest Modes

`ingest.mode=direct`:
- API writes directly to ClickHouse on every request.
- No additional infrastructure is required.

`ingest.mode=rabbitmq`:
- API publishes events to RabbitMQ.
- A separate worker consumes the queue, batches rows by `table_group`, and writes them to ClickHouse.
- This is the mode to use when you want a durable buffer between request handling and ClickHouse availability.
- Startup wait is configurable with `EVNT_INGEST__RABBITMQ__STARTUP_TIMEOUT_SECONDS` and `EVNT_INGEST__RABBITMQ__STARTUP_RETRY_INTERVAL_MS`.

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
EVNT_INGEST__MODE=rabbitmq docker compose --profile rabbitmq up -d rabbitmq worker app
```

Or locally from the repository root:

```bash
export EVNT_INGEST__MODE=rabbitmq
uv run python evnt/cli.py queue worker
```

In this mode the HTTP app only enqueues messages. Batch inserts into ClickHouse are performed exclusively by the worker.

The default RabbitMQ `prefetch_count` matches the default worker `batch_size`
so one-row tracking messages can fill a complete ClickHouse batch before the
timeout flush. If you tune `EVNT_INGEST__RABBITMQ__BATCH_SIZE`, tune
`EVNT_INGEST__RABBITMQ__PREFETCH_COUNT` with it unless you intentionally
prefer lower worker memory use and smaller timeout-driven inserts.

Idempotency: The command uses `CREATE DATABASE IF NOT EXISTS` and `CREATE TABLE IF NOT EXISTS`; re-running is safe. If you change schema definitions (e.g. `order_by`, `engine`) you must manually apply migrations (dropping/recreating or performing ALTER statements) – the CLI purposefully does not perform destructive changes.

Troubleshooting:
* Connection errors: ensure the hostname matches `EVNT_CLICKHOUSE__CONNECTION__HOST` (defaults to `clickhouse` inside Docker network).
* Cluster setup: set `EVNT_CLICKHOUSE__CONFIGURATION__CLUSTER_NAME` before running init so distributed tables are created.
* Permissions: use a ClickHouse user with `CREATE DATABASE` and `CREATE TABLE` privileges.

### Downloading Tracker Scripts via CLI

Instead of the shell script you can use the built-in command (run from the repository root):
```bash
uv run python evnt/cli.py scripts download
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

2. Replace `your-server.com` with your `evnt` server address

By default the collector allows cross-origin requests from any origin,
including credentialed browser tracker requests.

If you want to restrict that in production, configure CORS explicitly for the
sites you trust. For example, for `https://example.com`:

```bash
export EVNT_SECURITY__CORS_ALLOW_CREDENTIALS=true
export EVNT_SECURITY__CORS_ALLOWED_ORIGINS='["https://example.com"]'
```

`cors_allowed_origins` entries should be bare origins such as
`https://example.com` without a path.

### Demo Mode

To test `evnt` with the built-in demo:

1. Set `common.demo = true` in your configuration
2. Access the demo page at `http://your-server.com/demo/`
3. Events will be tracked and stored in your ClickHouse database

### Querying Data

To query the collected data, connect to your ClickHouse instance:

```bash
docker exec -it evnt-ch clickhouse-client
```

Example queries:

```sql
-- Get page views from the last 24 hours
SELECT time, page, refr, device_id, session_id
FROM evnt.local
WHERE event_type = 'page_view'
  AND time > now() - INTERVAL 1 DAY
ORDER BY time DESC;

-- Count events by type
SELECT event_type, count() as events
FROM evnt.local
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
docker logs -f evnt
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
   cd evnt
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

## Migrating from `simple-snowplow`

If you are upgrading from the previous `simple-snowplow` branding, the following
**user-facing identifiers changed**:

- Environment variable prefix: `SNOWPLOW_*` → `EVNT_*`
  (e.g. `SNOWPLOW_CLICKHOUSE__CONNECTION__HOST` is now
  `EVNT_CLICKHOUSE__CONNECTION__HOST`). The nested namespace `__SNOWPLOW__`
  stays — it refers to the Snowplow-protocol settings group, not the brand.
- Build arg env: `SNOWPLOW_BUILD_EXTRAS` → `EVNT_BUILD_EXTRAS`.
- Environment label: `SNOWPLOW_ENV` → `EVNT_ENV`.
- Python package directory: `simple_snowplow/` → `evnt/`. Update any custom
  `WORKDIR`, `COPY`, or `sys.path` entries accordingly.
- Docker image tag: `vladenisov/simple-snowplow` → `vladenisov/evnt`.
- Compose container names: `simple-snowplow*` → `evnt*`.
- RabbitMQ message `type` and routing headers:
  `simple_snowplow.insert` → `evnt.insert`, `x-simple-snowplow-*` → `x-evnt-*`.
  In-flight messages from older publishers will still be consumed (the worker
  doesn't filter on `type`); only newly-published messages carry the new
  identifiers. Drain the queue before downgrading if you ever roll back.
- Default ClickHouse database name: `snowplow` → `evnt`.
- Default ClickHouse table group / config key: `snowplow` → `evnt`
  (env-var path `EVNT_CLICKHOUSE__CONFIGURATION__TABLES__EVNT__...`).
- Default RabbitMQ queue name: `snowplow.ingest` → `evnt.ingest`
  (failed queue: `evnt.ingest.failed`).
- OpenAPI tag for tracker endpoints: `snowplow` → `tracker`.

For existing production deployments, the DB / queue defaults are a
**hard-breaking change**. Two ways forward:

1. **Pin the old names via env vars** (zero data migration):
   ```bash
   EVNT_CLICKHOUSE__CONFIGURATION__DATABASE=snowplow
   EVNT_INGEST__RABBITMQ__QUEUE_NAME=snowplow.ingest
   EVNT_INGEST__RABBITMQ__FAILED_QUEUE_NAME=snowplow.ingest.failed
   ```
   You will also need to keep the table-group key as `snowplow` in
   `EVNT_CLICKHOUSE__CONFIGURATION__TABLES__SNOWPLOW__...`.
2. **Migrate data** to the new defaults. ClickHouse: `RENAME DATABASE
   snowplow TO evnt`. RabbitMQ: drain the old queue, declare the new one,
   then switch the publisher / worker.

The following are **unchanged**:

- HTTP tracker endpoints (`/tracker`, `/i`) and their request/response shape —
  the wire protocol is the Snowplow tracker protocol and stays compatible with
  unmodified Snowplow JS / mobile trackers.
- Iglu schema URIs (`dev.snowplow.simple/...`).
- The internal `SNOWPLOW` settings namespace (e.g.
  `EVNT_COMMON__SNOWPLOW__USER_IP_HEADER`) — that group holds
  Snowplow-protocol-specific options, not project-brand identifiers.

## License & Attribution

This project's own source code is licensed under BSD 3-Clause (see [LICENSE](LICENSE)).

It interoperates with, and optionally redistributes unmodified copies of,
third-party components from Snowplow Analytics Ltd. and other authors:

- **Snowplow JavaScript tracker** (`sp.js`, plugins) — BSD 3-Clause,
  © 2022 Snowplow Analytics Ltd, © 2010 Anthon Pang. Fetched on demand by
  `cli.py scripts download`; not committed to this repo.
- **Iglu Central schemas** — Apache License 2.0, © Snowplow Analytics Ltd.
  Included as a git submodule at `evnt/vendor/iglu-central`,
  unmodified.

Full third-party copyright and license notices are in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), which downstream packagers
**must** redistribute alongside any Docker image or artifact that bundles the
tracker scripts or Iglu schemas.

"Snowplow" is a trademark of Snowplow Analytics Ltd. This project is not
affiliated with, sponsored by, or endorsed by Snowplow Analytics Ltd.
