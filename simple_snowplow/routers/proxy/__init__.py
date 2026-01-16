"""
Proxy router for Simple Snowplow.

This module provides proxy functionality for external analytics scripts,
allowing them to be served through the same domain as the application.
"""

from __future__ import annotations

import base64
from typing import Final

import httpx
import structlog
from core.config import settings
from core.constants import CONTENT_TYPE_OCTET_STREAM, DEFAULT_PROXY_TIMEOUT
from fastapi import HTTPException
from fastapi.responses import Response
from fastapi.routing import APIRouter
from pydantic import AnyHttpUrl
from routers.proxy import models

logger = structlog.get_logger(__name__)

PROXY_CONFIG = settings.proxy
PROXY_ENDPOINT = settings.common.snowplow.endpoints.proxy_endpoint
HOSTNAME = settings.common.hostname
PROXY_TIMEOUT: Final[float] = DEFAULT_PROXY_TIMEOUT


router = APIRouter(tags=["proxy"], prefix=PROXY_ENDPOINT)


def _encode_url_part(s: str) -> str:
    """URL-safe base64 encode a string."""
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("utf-8")


def _decode_url_part(s: str) -> str:
    """URL-safe base64 decode a string."""
    return base64.urlsafe_b64decode(s).decode("utf-8")


def _should_encode_domain(domain: str | None) -> bool:
    """Check if the domain should be encoded."""
    return domain in PROXY_CONFIG.domains


def _should_encode_path(path: str) -> bool:
    """Check if the path should be encoded."""
    # Remove leading slash for comparison
    clean_path = path.lstrip("/")
    return clean_path in PROXY_CONFIG.paths


@router.post("/hash")
async def proxy_hash(data: models.HashModel) -> AnyHttpUrl:
    """
    Generate a proxied URL for an external resource.

    Args:
        data: The URL to proxy

    Returns:
        The proxied URL if applicable, otherwise the original URL
    """
    should_encode = False

    domain = data.url.host
    if _should_encode_domain(domain):
        domain = _encode_url_part(domain)
        should_encode = True

    full_path = data.url.path[1:]
    if data.url.query is not None:
        full_path += f"?{data.url.query}"

    if _should_encode_path(data.url.path):
        full_path = _encode_url_part(full_path)
        should_encode = True

    if not should_encode:
        return AnyHttpUrl(str(data.url))

    path = f"{PROXY_ENDPOINT}/route/{data.url.scheme}"
    path += f"/{_encode_url_part(data.url.host)}/{full_path}"

    if path.startswith("/"):
        path = path[1:]

    result = AnyHttpUrl.build(
        scheme=HOSTNAME.scheme,
        host=HOSTNAME.host,
        port=HOSTNAME.port,
        path=path,
    )

    return result


@router.get("/route/{schema}/{host}/{path}")
async def proxy(schema: str, host: str, path: str = "") -> Response:
    """
    Proxy a request to an external resource.

    Args:
        schema: The URL scheme (http/https)
        host: The base64-encoded host
        path: The base64-encoded path

    Returns:
        The proxied response

    Raises:
        HTTPException: If the proxy request fails
    """
    decoded_host = _decode_url_part(host)
    decoded_path = _decode_url_part(path)
    url = f"{schema}://{decoded_host}/{decoded_path}"

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=PROXY_TIMEOUT)
    except httpx.TimeoutException as exc:
        logger.warning("Proxy request timed out", url=url)
        raise HTTPException(
            status_code=504,
            detail=f"Proxy request to '{decoded_host}' timed out",
        ) from exc
    except httpx.RequestError as exc:
        logger.warning("Proxy request failed", url=url, error=str(exc))
        raise HTTPException(
            status_code=502,
            detail=f"Proxy request to '{decoded_host}' failed",
        ) from exc

    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=response.headers.get("Content-Type", CONTENT_TYPE_OCTET_STREAM),
    )
