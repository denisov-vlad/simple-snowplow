import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "simple_snowplow"))

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

module_path = PROJECT_ROOT / "simple_snowplow" / "routers" / "tracker" / "parsers" / "ip.py"
spec = importlib.util.spec_from_file_location("ip_module", module_path)
ip_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ip_module)

convert_ip = ip_module.convert_ip
extract_ip_from_header = ip_module.extract_ip_from_header
DEFAULT_IPV4 = ip_module.DEFAULT_IPV4


def test_extract_ip_from_header_uses_first_ip_from_forward_chain():
    result = asyncio.run(
        extract_ip_from_header("203.0.113.1,198.51.100.101,198.51.100.102"),
    )

    assert str(result) == "203.0.113.1"


def test_extract_ip_from_header_skips_invalid_values():
    result = asyncio.run(extract_ip_from_header("unknown, not-an-ip, 198.51.100.44"))

    assert str(result) == "198.51.100.44"


def test_convert_ip_from_forward_chain():
    result = asyncio.run(convert_ip("203.0.113.1,198.51.100.101"))

    assert str(result) == "203.0.113.1"


def test_convert_ip_invalid_chain_returns_default_ipv4():
    result = asyncio.run(convert_ip("unknown,not-an-ip"))

    assert result == DEFAULT_IPV4
