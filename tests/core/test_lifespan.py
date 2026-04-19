import pathlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "simple_snowplow"))

import core.lifespan as lifespan_module  # noqa: E402
from core.config import ClickHouseConfig  # noqa: E402
from routers.tracker.parsers.iglu import ValidationResult  # noqa: E402

READY_AFTER_ATTEMPTS = 3


class _FakeClickHouseClient:
    def __init__(self, *, fail: bool):
        self.fail = fail
        self.closed = False

    async def query(self, sql: str):
        assert sql == "SELECT 1"
        if self.fail:
            raise RuntimeError("clickhouse is starting")
        return SimpleNamespace(first_row=(1,))

    async def close(self):
        self.closed = True


class _RecordingLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []
        self.errors = []

    def info(self, *args, **kwargs):
        self.infos.append((args, kwargs))

    def warning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))

    def error(self, *args, **kwargs):
        self.errors.append((args, kwargs))


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], indirect=True)
async def test_retry_clickhouse_startup_waits_until_connection_is_ready(
    monkeypatch,
    anyio_backend,
):
    attempts = 0
    sleep_calls = []

    async def _fake_connect():
        nonlocal attempts
        attempts += 1
        if attempts < READY_AFTER_ATTEMPTS:
            raise OSError("clickhouse is starting")
        return "connected"

    async def _fake_sleep(delay):
        sleep_calls.append(delay)

    monkeypatch.setattr(lifespan_module.asyncio, "sleep", _fake_sleep)

    connection = await lifespan_module.retry_clickhouse_startup(
        ClickHouseConfig(
            startup_timeout_seconds=10,
            startup_retry_interval_ms=250,
        ),
        "connect",
        _fake_connect,
    )

    assert connection == "connected"
    assert attempts == READY_AFTER_ATTEMPTS
    assert sleep_calls == [0.25, 0.25]


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], indirect=True)
async def test_create_ready_clickhouse_client_closes_client_when_probe_fails(
    monkeypatch,
    anyio_backend,
):
    client = _FakeClickHouseClient(fail=True)

    async def _fake_create_clickhouse_client():
        return client

    monkeypatch.setattr(
        lifespan_module,
        "_create_clickhouse_client",
        _fake_create_clickhouse_client,
    )

    with pytest.raises(RuntimeError, match="clickhouse is starting"):
        await lifespan_module._create_ready_clickhouse_client()

    assert client.closed is True


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], indirect=True)
async def test_lifespan_warms_iglu_schema_cache(monkeypatch, anyio_backend):
    logger = _RecordingLogger()
    warm_calls = []

    async def _fake_configure_direct_ingest(application):
        application.state.connector = object()

    def _fake_warm_iglu_schema_cache():
        warm_calls.append(True)
        return {
            "iglu:com.acme/example/jsonschema/1-0-0": ValidationResult(
                status="ok",
                schema_path=Path("/tmp/example"),
            ),
            "iglu:com.acme/missing/jsonschema/1-0-0": ValidationResult(
                status="warning",
                schema_path=Path("/tmp/missing"),
                error="schema file not found",
            ),
        }

    monkeypatch.setattr(lifespan_module, "logger", logger)
    monkeypatch.setattr(
        lifespan_module,
        "_configure_direct_ingest",
        _fake_configure_direct_ingest,
    )
    monkeypatch.setattr(
        lifespan_module,
        "warm_iglu_schema_cache",
        _fake_warm_iglu_schema_cache,
    )
    monkeypatch.setattr(
        lifespan_module,
        "INGEST_CONFIG",
        SimpleNamespace(
            mode="direct",
            rabbitmq=SimpleNamespace(host="rabbitmq"),
        ),
    )
    monkeypatch.setattr(
        lifespan_module,
        "CLICKHOUSE_CONFIG",
        ClickHouseConfig(),
    )

    application = SimpleNamespace(state=SimpleNamespace())

    async with lifespan_module.lifespan(application):
        pass

    assert warm_calls == [True]
    assert any(
        args[0] == "Failed to warm Iglu schema cache"
        and kwargs["schema"] == "iglu:com.acme/missing/jsonschema/1-0-0"
        for args, kwargs in logger.warnings
    )
    assert any(
        args[0] == "Iglu schema cache warmed"
        and kwargs["loaded_count"] == 1
        and kwargs["warning_count"] == 1
        and kwargs["skipped_count"] == 0
        for args, kwargs in logger.infos
    )
