# evnt

`evnt` is a lightweight, self-hosted event collector that **implements the Snowplow tracker wire protocol**. Point any official Snowplow tracker (JS, iOS/Swift, Android/Kotlin, Python, etc.) at `evnt` and it will accept the events, enrich them, and write them to ClickHouse — no hosted Snowplow infrastructure required.

> **Disclaimer.** "Snowplow" is a trademark of Snowplow Analytics Ltd. This is an independent open-source project that interoperates with the publicly documented Snowplow tracker protocol and bundles the official Snowplow JavaScript tracker (BSD-3-Clause) and Iglu Central schemas (Apache-2.0) **unmodified**. It is **not affiliated with, sponsored by, or endorsed by Snowplow Analytics Ltd.** See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for full attribution.

## Why evnt

- **Snowplow-protocol compatible** — receive events from any official tracker without rewriting your client code.
- **ClickHouse-native** — events land in a wide, partitioned `MergeTree` table ready for sub-second analytics.
- **Lean stack** — FastAPI on Python 3.14, async ClickHouse client, no JVM, no Kafka requirement.
- **Optional durable buffer** — flip a flag to switch from direct writes to RabbitMQ + batch worker for high-load or flaky downstreams.
- **Self-hosted, no telemetry** — your data, your infra, your retention policy.
- **Built-in demo UI** — a Vue 3 single-page app at `/demo/` that shows the raw payloads as they leave the browser **and** lets you browse the ClickHouse tables directly from the front-end.

## Quickstart

```bash
git clone https://github.com/denisov-vlad/evnt.git
cd evnt

# 1. Bring up ClickHouse first (the app waits for it).
docker compose up -d clickhouse

# 2. One-time: create the `evnt` database and tables (idempotent).
docker compose run --rm app uv run python cli.py db init

# 3. Start the collector (and worker, if you want RabbitMQ mode).
docker compose up -d
```

Open **<http://localhost:8000/demo/>**. The demo SPA has three tabs:

- **Live Events** — every payload sent to `/tracker` is intercepted and rendered as an expandable JSON tree, with timestamp and method.
- **ClickHouse Tables** — TanStack Table grid that queries ClickHouse over HTTP **directly from the browser** (CORS is preconfigured in `deploy/clickhouse/`). Pick a table, sort, paginate, expand JSON columns inline.
- **Settings** — change the ClickHouse URL / user / password if you’re pointing at a non-default cluster; values persist in `localStorage`.

To skip the SPA in your image, build with `BUILD_DEMO=false` (the `/demo/` mount falls back to a placeholder):

```bash
EVNT_BUILD_DEMO=false docker compose build app
# or
docker build --build-arg BUILD_DEMO=false -t evnt .
```

## Sending events from your applications

`evnt` speaks the Snowplow tracker protocol. Use the official trackers — point their collector URL at `https://your-evnt-host` and they’ll just work. Reference docs:

- **JavaScript** (web) — <https://docs.snowplow.io/docs/collecting-data/collecting-from-own-applications/javascript-trackers/>
- **Swift / iOS** — <https://docs.snowplow.io/docs/collecting-data/collecting-from-own-applications/mobile-trackers/>
- **Kotlin / Android** — <https://docs.snowplow.io/docs/collecting-data/collecting-from-own-applications/mobile-trackers/>
- **Python** — <https://docs.snowplow.io/docs/collecting-data/collecting-from-own-applications/python-tracker/>

The full tracker matrix (Java, Go, .NET, Roku, Unity, Lua, …) is at <https://docs.snowplow.io/docs/collecting-data/collecting-from-own-applications/>.

If you want to host the official Snowplow JS bundle from your own domain, run:

```bash
uv run python evnt/cli.py scripts download
```

That places `sp.js` (and plugins) into `evnt/static/`, served at `/static/sp.js`.

## Configuration

Settings are loaded from a single Pydantic `BaseSettings` model. Use the `EVNT_` prefix and `__` for nested keys:

```bash
EVNT_COMMON__DEMO=true                          # enable the /demo/ SPA at runtime
EVNT_CLICKHOUSE__CONNECTION__HOST=clickhouse    # CH host
EVNT_INGEST__MODE=rabbitmq                      # direct (default) | rabbitmq
EVNT_SECURITY__CORS_ALLOWED_ORIGINS='["https://example.com"]'
```

Inspect the full config tree (with defaults) any time:

```bash
uv run python evnt/cli.py settings
```

## License & Attribution

This project's own source code is licensed under BSD 3-Clause (see [LICENSE](LICENSE)).

It interoperates with, and optionally redistributes unmodified copies of, third-party components from Snowplow Analytics Ltd. and other authors:

- **Snowplow JavaScript tracker** (`sp.js`, plugins) — BSD 3-Clause, © 2022 Snowplow Analytics Ltd, © 2010 Anthon Pang. Fetched on demand by `cli.py scripts download`; not committed to this repo.
- **Iglu Central schemas** — Apache License 2.0, © Snowplow Analytics Ltd. Included as a git submodule at `evnt/vendor/iglu-central`, unmodified.

Full third-party copyright and license notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), which downstream packagers **must** redistribute alongside any Docker image or artifact that bundles the tracker scripts or Iglu schemas.

"Snowplow" is a trademark of Snowplow Analytics Ltd. This project is not affiliated with, sponsored by, or endorsed by Snowplow Analytics Ltd.
