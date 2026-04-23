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
    def __init__(self, event: asyncio.Event, requested_urls: list[str] | None = None):
        self._event = event
        self._requested_urls = requested_urls if requested_urls is not None else []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, timeout: float):
        self._requested_urls.append(str(url))
        await asyncio.sleep(0)
        self._event.set()
        return _DummyResponse()


def _encode(value: str) -> str:
    return proxy_module._encode_url_part(value)


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], indirect=True)
async def test_proxy_awaits_async_request(monkeypatch, anyio_backend):
    event = asyncio.Event()
    requested_urls: list[str] = []

    def _factory(*args, **kwargs):
        assert kwargs.get("follow_redirects") is True
        return _DummyAsyncClient(event, requested_urls)

    monkeypatch.setattr(proxy_module.PROXY_CONFIG, "domains", ["example.com"])
    monkeypatch.setattr(proxy_module.httpx, "AsyncClient", _factory)

    response = await proxy_module.proxy(
        "https",
        _encode("example.com"),
        _encode("tracker"),
    )

    assert event.is_set(), "Proxy did not await the HTTP request"
    assert requested_urls == ["https://example.com/tracker"]
    assert response.status_code == 200
    assert response.body == b"ok"


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], indirect=True)
async def test_proxy_allows_port_on_allowed_hostname(monkeypatch, anyio_backend):
    event = asyncio.Event()
    requested_urls: list[str] = []

    def _factory(*args, **kwargs):
        assert kwargs.get("follow_redirects") is True
        return _DummyAsyncClient(event, requested_urls)

    monkeypatch.setattr(proxy_module.PROXY_CONFIG, "domains", ["example.com"])
    monkeypatch.setattr(proxy_module.httpx, "AsyncClient", _factory)

    response = await proxy_module.proxy(
        "https",
        _encode("example.com:8443"),
        _encode("tracker"),
    )

    assert event.is_set(), "Proxy did not await the HTTP request"
    assert requested_urls == ["https://example.com:8443/tracker"]
    assert response.status_code == 200
    assert response.body == b"ok"


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], indirect=True)
async def test_proxy_rejects_authority_with_allowed_userinfo_but_disallowed_host(
    monkeypatch,
    anyio_backend,
):
    monkeypatch.setattr(proxy_module.PROXY_CONFIG, "domains", ["allowed.com"])
    monkeypatch.setattr(
        proxy_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: pytest.fail("Proxy request should not be attempted"),
    )

    with pytest.raises(proxy_module.HTTPException) as exc_info:
        await proxy_module.proxy(
            "http",
            _encode("allowed.com:80@169.254.169.254"),
            _encode("latest/meta-data"),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Proxy target not allowed"
