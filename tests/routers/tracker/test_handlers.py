# ruff: noqa: E402

import importlib
import json
import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "simple_snowplow"))

from simple_snowplow.routers.tracker.handlers import process_data
from simple_snowplow.routers.tracker.models.snowplow import (
    PayloadElementModel,
)


class _RecordingLogger:
    def __init__(self):
        self.debugs = []
        self.warnings = []

    def debug(self, *args, **kwargs):
        self.debugs.append((args, kwargs))

    def warning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))

    def error(self, *args, **kwargs):  # pragma: no cover - not used in this test
        raise AssertionError(f"Unexpected error log: {args!r} {kwargs!r}")


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], indirect=True)
async def test_process_data_logs_iglu_warning_but_returns_row(
    monkeypatch,
    anyio_backend,
):
    logger = _RecordingLogger()
    runtime_payload_module = importlib.import_module("routers.tracker.parsers.payload")
    monkeypatch.setattr(runtime_payload_module, "logger", logger)

    body = PayloadElementModel.model_validate(
        {
            "aid": "example-app",
            "e": "pv",
            "p": "web",
            "tv": "js-1.0.0",
            "res": "1920x1080",
            "co": json.dumps(
                {
                    "data": [
                        {
                            "schema": (
                                "iglu:com.snowplowanalytics.snowplow/"
                                "browser_context/jsonschema/2-0-0"
                            ),
                            "data": {
                                "resolution": 123,
                            },
                        },
                    ],
                },
            ),
        },
    )

    rows = await process_data(
        body=body,
        user_agent="",
        user_ip=None,
        cookies=None,
    )

    assert len(rows) == 1
    assert rows[0]["aid"] == "example-app"
    assert any(
        args[0] == "Iglu validation warning"
        and kwargs["validation_stage"] == "contexts"
        for args, kwargs in logger.warnings
    )
