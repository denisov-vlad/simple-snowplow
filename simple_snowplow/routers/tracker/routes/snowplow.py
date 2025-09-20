"""
Route handlers for Snowplow events.
"""

import base64

from elasticapm.contrib.asyncio.traces import async_capture_span
from fastapi import Depends, Header, Request, Response
from pydantic import IPvAnyAddress
from routers.tracker.handlers import process_data
from routers.tracker.models.snowplow import (
    PayloadElementModel,
    PayloadModel,
)
from starlette.status import HTTP_204_NO_CONTENT

PIXEL = base64.b64decode(
    b"R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==",
)


@async_capture_span()
async def tracker_cors():
    """
    Handle CORS preflight requests.

    Returns:
        Empty response for OPTIONS requests
    """
    return


@async_capture_span()
async def tracker_post(
    request: Request,
    body: PayloadModel,
    user_agent: str | None = Header(None),
    x_forwarded_for: IPvAnyAddress | str | None = Header(None),
    cookie: str | None = Header(None),
):
    """
    Handle POST requests from Snowplow JS Tracker.

    Args:
        request: FastAPI request object
        body: Request body containing Snowplow payload
        user_agent: User agent header
        x_forwarded_for: IP address forwarded from proxy
        cookie: Browser cookies

    Returns:
        Empty response with 204 status code
    """
    data = await process_data(body, user_agent, x_forwarded_for, cookie)
    await request.app.state.connector.insert_rows(data)

    return Response(status_code=HTTP_204_NO_CONTENT)


@async_capture_span()
async def tracker_get(
    request: Request,
    params: PayloadElementModel = Depends(),
    user_agent: str | None = Header(None),
    x_forwarded_for: IPvAnyAddress | str | None = Header(None),
    cookie: str | None = Header(None),
):
    """
    Handle GET requests from Snowplow JS Tracker.

    Args:
        request: FastAPI request object
        params: Query parameters containing Snowplow payload
        user_agent: User agent header
        x_forwarded_for: IP address forwarded from proxy
        cookie: Browser cookies

    Returns:
        1x1 transparent GIF pixel response
    """
    data = await process_data(params, user_agent, x_forwarded_for, cookie)
    await request.app.state.connector.insert_rows(data)

    return Response(content=PIXEL, media_type="image/gif")
