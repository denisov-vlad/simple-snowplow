import importlib.util
import sys
from pathlib import Path
from types import ModuleType

PROJECT_ROOT = Path(__file__).resolve().parents[4]

if "elasticapm" not in sys.modules:
    elasticapm_module = ModuleType("elasticapm")
    contrib_module = ModuleType("elasticapm.contrib")
    asyncio_module = ModuleType("elasticapm.contrib.asyncio")
    traces_module = ModuleType("elasticapm.contrib.asyncio.traces")

    def _capture_span(*args, **kwargs):  # pragma: no cover - stub
        def decorator(func):
            return func

        return decorator

    traces_module.capture_span = _capture_span
    asyncio_module.traces = traces_module
    contrib_module.asyncio = asyncio_module
    elasticapm_module.contrib = contrib_module

    sys.modules["elasticapm"] = elasticapm_module
    sys.modules["elasticapm.contrib"] = contrib_module
    sys.modules["elasticapm.contrib.asyncio"] = asyncio_module
    sys.modules["elasticapm.contrib.asyncio.traces"] = traces_module

module_path = PROJECT_ROOT / "evnt" / "routers" / "tracker" / "parsers" / "utils.py"
spec = importlib.util.spec_from_file_location("utils_module", module_path)
utils_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(utils_module)

find_available = utils_module.find_available


def test_find_available_returns_existing_dict_without_json_decoding():
    result = find_available({"data": []}, None)

    assert result == {"data": []}


def test_find_available_returns_none_for_invalid_json():
    result = find_available("not-json", None)

    assert result is None
