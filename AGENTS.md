# AGENTS.md

## What This Repo Is

`evnt` is a lightweight self-hosted event collector that implements the Snowplow tracker wire protocol so it can receive events from the upstream Snowplow JavaScript and mobile trackers. It is an independent project, not affiliated with Snowplow Analytics Ltd.

Use it to:
- receive tracker requests over HTTP using the documented Snowplow protocol;
- write events into ClickHouse;
- run in direct-write mode or RabbitMQ-backed ingest mode;
- proxy selected analytics assets;
- serve a demo page when demo mode is enabled;
- download and manage tracker scripts through the CLI.

This file is the fast operational guide for agents working in the repo.

## Agent Workflow

If `agentmemory` MCP is available in the current session, use it for every task.
- if it is not started yet, start it with `npx @agentmemory/agentmemory`;
- recall relevant prior context before making assumptions;
- save durable decisions, implementation notes, and user preferences when they are likely to matter later.

Use `uv` for Python work by default.
- use `uv sync` to install dependencies;
- use `uv run ...` for tests, linters, scripts, and local app commands;
- prefer `uv run python evnt/cli.py ...` from the repo root;
- do not introduce ad-hoc `pip install`, bare `python`, or alternative env managers unless the user explicitly asks for them.

Before changing behavior, verify the actual ingest mode and startup path instead of assuming the app always talks to ClickHouse directly.

## Stack And Runtime

Core stack:
- Python `3.14`
- `uv`
- FastAPI
- Pydantic Settings
- ClickHouse via `clickhouse-connect`
- RabbitMQ via `aio-pika`
- `structlog`
- `httpx`

Compose services in [compose.yml](compose.yml):
- `app`
- `clickhouse`
- `rabbitmq` under the `rabbitmq` profile
- `worker` under the `rabbitmq` profile

Important runtime facts:
- healthcheck endpoint is `GET /`, not `/health`;
- default tracking endpoints are `/tracker` and `/i`;
- proxy endpoint is `/proxy`;
- SendGrid endpoint is `/sendgrid`;
- table creation is explicit via CLI `db init`; startup should not be assumed to create tables for you;
- the app warms the local Iglu schema cache during lifespan startup;
- demo routes exist only when `EVNT_COMMON__DEMO=true`;
- RabbitMQ ingest is optional, not the default.

## Commands That Matter

From the repo root:
- `uv sync`
- `uv run pytest`
- `uv run ruff check .`
- `uv run ruff format .`
- `uv run python evnt/cli.py settings`
- `uv run python evnt/cli.py db init`
- `uv run python evnt/cli.py queue worker`
- `uv run python evnt/cli.py queue healthcheck`
- `uv run python evnt/cli.py scripts download`

Local app run:
- `cd evnt && uv run uvicorn main:app --reload`

Compose:
- `docker compose up --watch`
- `docker compose run app uv run python cli.py db init`
- `EVNT_INGEST__MODE=rabbitmq docker compose --profile rabbitmq up -d rabbitmq worker app`

## Repo Layout

Top level:
- [README.md](README.md): user-facing setup and runtime notes.
- [compose.yml](compose.yml): local runtime topology.
- [pyproject.toml](pyproject.toml): Python metadata, dependencies, Ruff config.
- [tests](tests): pytest coverage.
- [evnt](evnt): application package.

Important entrypoints:
- [evnt/main.py](evnt/main.py): FastAPI app factory and router wiring.
- [evnt/cli.py](evnt/cli.py): operational CLI for settings, ClickHouse init, queue worker, and script download.
- [evnt/core/config.py](evnt/core/config.py): full env-driven settings model.
- [evnt/core/healthcheck.py](evnt/core/healthcheck.py): probe behavior.

Main package areas:
- `evnt/core`: config, lifespan, healthcheck, shared plumbing.
- `evnt/routers/tracker`: tracker routes, parsers, models, ClickHouse integration.
- `evnt/routers/proxy`: proxy functionality.
- `evnt/routers/demo`: demo assets and routes.
- `evnt/ingest`: RabbitMQ-backed worker path.
- `evnt/plugins`: logging and optional integrations.

## Project-Specific Guardrails

Do not casually "fix" the import style across the repo.
- this codebase intentionally supports both `evnt...` imports and app-root imports such as `from core...`;
- tests and tooling already compensate for that layout.

Do not assume all changes need Docker first.
- many checks can run locally with `uv`;
- use Compose when the task actually needs ClickHouse or RabbitMQ.

Do not assume infra-backed tests are cheap.
- most tests in `tests/` are unit-style and monkeypatched;
- if a task depends on real ClickHouse or RabbitMQ behavior, say so explicitly and verify with the right runtime.

When touching configuration:
- preserve the `EVNT_` env prefix and nested `__` structure;
- keep README examples, Compose defaults, and code defaults aligned.

When touching tracker behavior:
- verify both `/tracker` and `/i` expectations if the change affects request parsing;
- keep proxy and SendGrid routes out of scope unless the task actually requires them.
