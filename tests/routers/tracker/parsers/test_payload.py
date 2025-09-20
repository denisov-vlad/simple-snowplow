import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "simple_snowplow"))

if "core" not in sys.modules:
    core_module = ModuleType("core")
    config_module = ModuleType("core.config")
    config_module.settings = SimpleNamespace(
        common=SimpleNamespace(snowplow=SimpleNamespace(schemas={}))
    )
    core_module.config = config_module
    sys.modules["core"] = core_module
    sys.modules["core.config"] = config_module

if "structlog" not in sys.modules:
    structlog_module = ModuleType("structlog")
    stdlib_module = ModuleType("structlog.stdlib")

    class _DummyLogger:
        def warning(self, *args, **kwargs):
            return None

        def error(self, *args, **kwargs):
            return None

    stdlib_module.get_logger = lambda: _DummyLogger()
    structlog_module.stdlib = stdlib_module
    sys.modules["structlog"] = structlog_module
    sys.modules["structlog.stdlib"] = stdlib_module

if "orjson" not in sys.modules:
    orjson_module = ModuleType("orjson")

    class _JSONDecodeError(Exception):
        pass

    def _loads(_: str):  # pragma: no cover - stub
        raise _JSONDecodeError

    orjson_module.JSONDecodeError = _JSONDecodeError
    orjson_module.loads = _loads
    sys.modules["orjson"] = orjson_module

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

    sys.modules["elasticapm"] = elasticapm_module
    sys.modules["elasticapm.contrib"] = contrib_module
    sys.modules["elasticapm.contrib.asyncio"] = asyncio_module
    sys.modules["elasticapm.contrib.asyncio.traces"] = traces_module

if "routers" not in sys.modules:
    routers_module = ModuleType("routers")
    tracker_module = ModuleType("routers.tracker")
    parsers_module = ModuleType("routers.tracker.parsers")
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

    utils_module.parse_base64 = _parse_base64
    snowplow_module.InsertModel = _InsertModel
    snowplow_module.PayloadElementModel = _PayloadElementModel
    snowplow_module.StructuredEvent = _StructuredEvent
    snowplow_module.UserAgentModel = _UserAgentModel

    routers_module.tracker = tracker_module
    tracker_module.parsers = parsers_module
    tracker_module.models = models_module
    parsers_module.utils = utils_module
    models_module.snowplow = snowplow_module

    sys.modules["routers"] = routers_module
    sys.modules["routers.tracker"] = tracker_module
    sys.modules["routers.tracker.parsers"] = parsers_module
    sys.modules["routers.tracker.parsers.utils"] = utils_module
    sys.modules["routers.tracker.models"] = models_module
    sys.modules["routers.tracker.models.snowplow"] = snowplow_module

import asyncio
import importlib.util

module_path = PROJECT_ROOT / "simple_snowplow" / "routers" / "tracker" / "parsers" / "payload.py"
spec = importlib.util.spec_from_file_location("payload_module", module_path)
payload_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(payload_module)

parse_cookies = payload_module.parse_cookies


def test_parse_cookies_truncated_sp_id_cookie_returns_empty_dict():
    cookies_str = "_sp_id.123=abc.def"

    result = asyncio.run(parse_cookies(cookies_str))

    assert result == {}
