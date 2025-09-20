import asyncio
import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "simple_snowplow"))

from simple_snowplow.routers import proxy as proxy_module  # noqa: E402


class _DummyResponse:
    status_code = 200
    content = b"ok"
    headers = {"Content-Type": "text/plain"}


class _DummyAsyncClient:
    def __init__(self, event: asyncio.Event):
        self._event = event

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, timeout: float):
        await asyncio.sleep(0)
        self._event.set()
        return _DummyResponse()


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], indirect=True)
async def test_proxy_awaits_async_request(monkeypatch, anyio_backend):
    event = asyncio.Event()

    def _factory(*args, **kwargs):
        assert kwargs.get("follow_redirects") is True
        return _DummyAsyncClient(event)

    monkeypatch.setattr(proxy_module.httpx, "AsyncClient", _factory)

    response = await proxy_module.proxy(
        "https",
        proxy_module.encode("example.com"),
        proxy_module.encode("tracker"),
    )

    assert event.is_set(), "Proxy did not await the HTTP request"
    assert response.status_code == 200
    assert response.body == b"ok"
