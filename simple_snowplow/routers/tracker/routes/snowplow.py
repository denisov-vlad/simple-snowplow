"""
Route handlers for Snowplow events.
"""
import base64
from typing import Optional

import elasticapm
from fastapi import Depends
from fastapi import Header
from fastapi import Request
from fastapi import Response
from fastapi.responses import Response
from pydantic import IPvAnyAddress
from routers.tracker.handlers import process_data
from routers.tracker.schemas.models import PayloadElementBaseModel
from routers.tracker.schemas.models import PayloadModel
from starlette.status import HTTP_204_NO_CONTENT


def pixel_gif() -> bytes:
    """
    Generate a 1x1 transparent GIF pixel.

    Returns:
        Bytes representing a 1x1 transparent GIF
    """
    img = b"R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
    return base64.b64decode(img)


# Cached pixel for performance
pixel = pixel_gif()


@elasticapm.async_capture_span()
async def tracker_cors():
    """
    Handle CORS preflight requests.

    Returns:
        Empty response for OPTIONS requests
    """
    return


@elasticapm.async_capture_span()
async def tracker_post(
    request: Request,
    body: PayloadModel,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[IPvAnyAddress | str] = Header(None),
    cookie: Optional[str] = Header(None),
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
    await request.app.state.connector.insert(data)

    return Response(status_code=HTTP_204_NO_CONTENT)


@elasticapm.async_capture_span()
async def tracker_get(
    request: Request,
    params: PayloadElementBaseModel = Depends(),
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[IPvAnyAddress | str] = Header(None),
    cookie: Optional[str] = Header(None),
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
    await request.app.state.connector.insert(data)

    return Response(content=pixel, media_type="image/gif")
