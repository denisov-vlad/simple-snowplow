from __future__ import annotations

import base64
from typing import Final

import httpx
from core.config import settings
from fastapi import HTTPException
from fastapi.responses import Response
from fastapi.routing import APIRouter

from routers.proxy import models

PROXY_CONFIG = settings.proxy
PROXY_ENDPOINT = settings.common.snowplow.endpoints.proxy_endpoint
HOSTNAME = settings.common.hostname
PROXY_TIMEOUT: Final[float] = 10.0


router = APIRouter(tags=["proxy"], prefix=PROXY_ENDPOINT)


def encode(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("utf-8")


def decode(s: str) -> str:
    return base64.urlsafe_b64decode(s).decode("utf-8")


@router.post("/hash")
async def proxy_hash(data: models.HashModel):
    return_encoded = False

    domain = data.url.host
    if domain in PROXY_CONFIG.domains:
        domain = encode(domain)
        return_encoded = True

    full_path = data.url.path[1:]
    if data.url.query is not None:
        full_path += f"?{data.url.query}"

    if data.url.path[1:] in PROXY_CONFIG.paths:
        full_path = encode(full_path)
        return_encoded = True

    if not return_encoded:
        return data.url

    result = (
        f"{HOSTNAME}{PROXY_ENDPOINT}/route/{data.url.scheme}/"
        f"{encode(data.url.host)}/{full_path}"
    )

    return result


@router.get("/route/{schema}/{host}/{path}")
async def proxy(schema: str, host: str, path: str = ""):
    url = f"{schema}://{decode(host)}/{decode(path)}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=PROXY_TIMEOUT)
    except httpx.TimeoutException as exc:
        msg = f"Proxy request to '{url}' timed out"
        raise HTTPException(status_code=504, detail=msg) from exc
    except httpx.RequestError as exc:  # pragma: no cover - specific network errors
        msg = f"Proxy request to '{url}' failed"
        raise HTTPException(status_code=502, detail=msg) from exc

    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=response.headers.get("Content-Type", "application/octet-stream"),
    )
