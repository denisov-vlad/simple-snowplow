import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "simple_snowplow"))

_created_stub_modules: list[str] = []


def _register_stub_module(name: str, module: ModuleType) -> None:
    sys.modules[name] = module
    _created_stub_modules.append(name)


if "core" not in sys.modules:
    core_module = ModuleType("core")
    config_module = ModuleType("core.config")
    config_module.settings = SimpleNamespace(
        common=SimpleNamespace(
            snowplow=SimpleNamespace(
                schemas=SimpleNamespace(
                    page_data="dev.snowplow.simple/page_data",
                    screen_data="dev.snowplow.simple/screen_data",
                    user_data="dev.snowplow.simple/user_data",
                    ad_data="dev.snowplow.simple/ad_data",
                    u2s_data="dev.snowplow.simple/u2s_data",
                ),
            ),
        ),
    )
    core_module.config = config_module
    _register_stub_module("core", core_module)
    _register_stub_module("core.config", config_module)

if "structlog" not in sys.modules:
    structlog_module = ModuleType("structlog")
    stdlib_module = ModuleType("structlog.stdlib")

    class _DummyLogger:
        def debug(self, *args, **kwargs):
            return None

        def warning(self, *args, **kwargs):
            return None

        def error(self, *args, **kwargs):
            return None

    def _get_logger():
        return _DummyLogger()

    stdlib_module.get_logger = _get_logger
    structlog_module.stdlib = stdlib_module
    _register_stub_module("structlog", structlog_module)
    _register_stub_module("structlog.stdlib", stdlib_module)

if "orjson" not in sys.modules:
    orjson_module = ModuleType("orjson")

    class _JSONDecodeError(Exception):
        pass

    def _loads(_: str):  # pragma: no cover - stub
        raise _JSONDecodeError

    orjson_module.JSONDecodeError = _JSONDecodeError
    orjson_module.loads = _loads
    _register_stub_module("orjson", orjson_module)

if "elasticapm" not in sys.modules:
    elasticapm_module = ModuleType("elasticapm")
    contrib_module = ModuleType("elasticapm.contrib")
    asyncio_module = ModuleType("elasticapm.contrib.asyncio")
    traces_module = ModuleType("elasticapm.contrib.asyncio.traces")

    def _async_capture_span(*args, **kwargs):  # pragma: no cover - stub
        def decorator(func):
            return func

        return decorator

    traces_module.async_capture_span = _async_capture_span
    asyncio_module.traces = traces_module
    contrib_module.asyncio = asyncio_module
    elasticapm_module.contrib = contrib_module

    _register_stub_module("elasticapm", elasticapm_module)
    _register_stub_module("elasticapm.contrib", contrib_module)
    _register_stub_module("elasticapm.contrib.asyncio", asyncio_module)
    _register_stub_module("elasticapm.contrib.asyncio.traces", traces_module)

if "routers" not in sys.modules:
    routers_module = ModuleType("routers")
    tracker_module = ModuleType("routers.tracker")
    parsers_module = ModuleType("routers.tracker.parsers")
    iglu_module = ModuleType("routers.tracker.parsers.iglu")
    utils_module = ModuleType("routers.tracker.parsers.utils")
    models_module = ModuleType("routers.tracker.models")
    snowplow_module = ModuleType("routers.tracker.models.snowplow")

    def _parse_base64(value: str):  # pragma: no cover - stub
        return value

    class _InsertModel:  # pragma: no cover - stub
        pass

    class _PayloadElementModel:  # pragma: no cover - stub
        pass

    class _StructuredEvent:  # pragma: no cover - stub
        pass

    class _UserAgentModel:  # pragma: no cover - stub
        pass

    class _ValidationResult:  # pragma: no cover - stub
        def __init__(self, status, schema_path=None, error=None):
            self.status = status
            self.schema_path = schema_path
            self.error = error

    def _validate_iglu_payload(schema_uri, data):  # pragma: no cover - stub
        return _ValidationResult("skipped")

    iglu_module.ValidationResult = _ValidationResult
    iglu_module.validate_iglu_payload = _validate_iglu_payload
    utils_module.parse_base64 = _parse_base64
    snowplow_module.InsertModel = _InsertModel
    snowplow_module.PayloadElementModel = _PayloadElementModel
    snowplow_module.StructuredEvent = _StructuredEvent
    snowplow_module.UserAgentModel = _UserAgentModel

    routers_module.tracker = tracker_module
    tracker_module.parsers = parsers_module
    tracker_module.models = models_module
    parsers_module.iglu = iglu_module
    parsers_module.utils = utils_module
    models_module.snowplow = snowplow_module

    _register_stub_module("routers", routers_module)
    _register_stub_module("routers.tracker", tracker_module)
    _register_stub_module("routers.tracker.parsers", parsers_module)
    _register_stub_module("routers.tracker.parsers.iglu", iglu_module)
    _register_stub_module("routers.tracker.parsers.utils", utils_module)
    _register_stub_module("routers.tracker.models", models_module)
    _register_stub_module("routers.tracker.models.snowplow", snowplow_module)

module_path = (
    PROJECT_ROOT / "simple_snowplow" / "routers" / "tracker" / "parsers" / "payload.py"
)
spec = importlib.util.spec_from_file_location("payload_module", module_path)
payload_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(payload_module)

for module_name in reversed(_created_stub_modules):
    sys.modules.pop(module_name, None)

parse_cookies = payload_module.parse_cookies
parse_contexts = payload_module.parse_contexts
parse_event = payload_module.parse_event


class _RecordingLogger:
    def __init__(self):
        self.debugs = []
        self.warnings = []
        self.errors = []

    def debug(self, *args, **kwargs):
        self.debugs.append((args, kwargs))

    def warning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))

    def error(self, *args, **kwargs):
        self.errors.append((args, kwargs))


def test_parse_cookies_truncated_sp_id_cookie_returns_empty_dict():
    cookies_str = "_sp_id.123=abc.def"

    result = asyncio.run(parse_cookies(cookies_str))

    assert result == {}


def test_parse_contexts_keeps_existing_resolution_when_browser_context_has_nulls():
    model = SimpleNamespace(
        res="1920x1080",
        vp="1280x720",
        ds="1280x720",
        browser_extra={},
    )
    contexts = {
        "data": [
            {
                "schema": "iglu:com.snowplowanalytics.snowplow/browser_context/jsonschema/2-0-0",
                "data": {
                    "resolution": None,
                    "viewport": None,
                    "documentSize": "",
                },
            },
        ],
    }

    result = asyncio.run(parse_contexts(contexts, model))

    assert result.res == "1920x1080"
    assert result.vp == "1280x720"
    assert result.ds == "1280x720"


def test_parse_contexts_logs_validation_warning_but_keeps_processing(monkeypatch):
    logger = _RecordingLogger()
    monkeypatch.setattr(payload_module, "logger", logger)
    monkeypatch.setattr(
        payload_module,
        "validate_iglu_payload",
        lambda schema_uri, data: payload_module.ValidationResult(
            status="warning",
            error="invalid payload",
        ),
    )

    model = SimpleNamespace(
        res="1920x1080",
        vp="1280x720",
        ds="1280x720",
        browser_extra={},
    )
    contexts = {
        "data": [
            {
                "schema": "iglu:com.snowplowanalytics.snowplow/browser_context/jsonschema/2-0-0",
                "data": {
                    "resolution": None,
                    "viewport": None,
                    "documentSize": "",
                },
            },
        ],
    }

    result = asyncio.run(parse_contexts(contexts, model))

    assert result.res == "1920x1080"
    assert any(
        args[0] == "Iglu validation warning"
        and kwargs["validation_stage"] == "contexts"
        and kwargs["schema"]
        == "iglu:com.snowplowanalytics.snowplow/browser_context/jsonschema/2-0-0"
        for args, kwargs in logger.warnings
    )


def test_parse_contexts_logs_validation_debug_when_validation_passes(monkeypatch):
    logger = _RecordingLogger()
    monkeypatch.setattr(payload_module, "logger", logger)
    monkeypatch.setattr(
        payload_module,
        "validate_iglu_payload",
        lambda schema_uri, data: payload_module.ValidationResult(
            status="ok",
            schema_path=Path("/tmp/browser_context.json"),
        ),
    )

    model = SimpleNamespace(
        res="1920x1080",
        vp="1280x720",
        ds="1280x720",
        browser_extra={},
    )
    contexts = {
        "data": [
            {
                "schema": "iglu:com.snowplowanalytics.snowplow/browser_context/jsonschema/2-0-0",
                "data": {
                    "resolution": None,
                    "viewport": None,
                    "documentSize": "",
                },
            },
        ],
    }

    asyncio.run(parse_contexts(contexts, model))

    assert any(
        args[0] == "Iglu validation passed"
        and kwargs["validation_stage"] == "contexts"
        and kwargs["schema"]
        == "iglu:com.snowplowanalytics.snowplow/browser_context/jsonschema/2-0-0"
        and kwargs["schema_path"] == "/tmp/browser_context.json"
        for args, kwargs in logger.debugs
    )


def test_parse_event_logs_validation_warning_but_keeps_processing(monkeypatch):
    logger = _RecordingLogger()
    monkeypatch.setattr(payload_module, "logger", logger)
    monkeypatch.setattr(
        payload_module,
        "schemas",
        SimpleNamespace(u2s_data="dev.snowplow.simple/u2s_data"),
    )
    monkeypatch.setattr(
        payload_module,
        "validate_iglu_payload",
        lambda schema_uri, data: payload_module.ValidationResult(
            status="warning",
            error="invalid event payload",
        ),
    )

    model = SimpleNamespace(ue={})
    event = {
        "data": {
            "schema": "iglu:com.acme/example_event/jsonschema/1-0-0",
            "data": {"foo": "bar"},
        },
    }

    result = asyncio.run(parse_event(event, model))

    assert result.ue["example_event"] == {"foo": "bar"}
    assert any(
        args[0] == "Iglu validation warning"
        and kwargs["validation_stage"] == "event"
        and kwargs["schema"] == "iglu:com.acme/example_event/jsonschema/1-0-0"
        for args, kwargs in logger.warnings
    )


def test_parse_event_logs_validation_debug_when_validation_passes(monkeypatch):
    logger = _RecordingLogger()
    monkeypatch.setattr(payload_module, "logger", logger)
    monkeypatch.setattr(
        payload_module,
        "schemas",
        SimpleNamespace(u2s_data="dev.snowplow.simple/u2s_data"),
    )
    monkeypatch.setattr(
        payload_module,
        "validate_iglu_payload",
        lambda schema_uri, data: payload_module.ValidationResult(
            status="ok",
            schema_path=Path("/tmp/example_event.json"),
        ),
    )

    model = SimpleNamespace(ue={})
    event = {
        "data": {
            "schema": "iglu:com.acme/example_event/jsonschema/1-0-0",
            "data": {"foo": "bar"},
        },
    }

    asyncio.run(parse_event(event, model))

    assert any(
        args[0] == "Iglu validation passed"
        and kwargs["validation_stage"] == "event"
        and kwargs["schema"] == "iglu:com.acme/example_event/jsonschema/1-0-0"
        and kwargs["schema_path"] == "/tmp/example_event.json"
        for args, kwargs in logger.debugs
    )
