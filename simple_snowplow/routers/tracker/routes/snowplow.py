"""
Route handlers for Snowplow events.

This module provides handlers for collecting tracking data using the
Snowplow tracking protocol via both GET and POST methods.
"""

from core.constants import CONTENT_TYPE_GIF, TRACKING_PIXEL
from core.dependencies import DbConnector
from elasticapm.contrib.asyncio.traces import async_capture_span
from fastapi import Depends, Header, Response
from pydantic import IPvAnyAddress
from routers.tracker.handlers import process_data
from routers.tracker.models.snowplow import (
    PayloadElementModel,
    PayloadModel,
)
from starlette.status import HTTP_204_NO_CONTENT


@async_capture_span()
async def tracker_cors() -> None:
    """
    Handle CORS preflight requests.

    Returns:
        Empty response for OPTIONS requests
    """
    return


@async_capture_span()
async def tracker_post(
    connector: DbConnector,
    body: PayloadModel,
    user_agent: str | None = Header(None),
    x_forwarded_for: IPvAnyAddress | str | None = Header(None),
    cookie: str | None = Header(None),
) -> Response:
    """
    Handle POST requests from Snowplow JS Tracker.

    Args:
        connector: Database connector (injected)
        body: Request body containing Snowplow payload
        user_agent: User agent header
        x_forwarded_for: IP address forwarded from proxy
        cookie: Browser cookies

    Returns:
        Empty response with 204 status code
    """
    data = await process_data(body, user_agent, x_forwarded_for, cookie)
    await connector.insert_rows(data)

    return Response(status_code=HTTP_204_NO_CONTENT)


@async_capture_span()
async def tracker_get(
    connector: DbConnector,
    params: PayloadElementModel = Depends(),
    user_agent: str | None = Header(None),
    x_forwarded_for: IPvAnyAddress | str | None = Header(None),
    cookie: str | None = Header(None),
) -> Response:
    """
    Handle GET requests from Snowplow JS Tracker.

    Args:
        connector: Database connector (injected)
        params: Query parameters containing Snowplow payload
        user_agent: User agent header
        x_forwarded_for: IP address forwarded from proxy
        cookie: Browser cookies

    Returns:
        1x1 transparent GIF pixel response
    """
    data = await process_data(params, user_agent, x_forwarded_for, cookie)
    await connector.insert_rows(data)

    return Response(content=TRACKING_PIXEL, media_type=CONTENT_TYPE_GIF)
