import base64
from typing import Optional

from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import Header
from fastapi import Request
from fastapi.responses import Response
from fastapi.routing import APIRouter
from routers.tracker import models
from routers.tracker.handlers import process_data
from starlette.status import HTTP_204_NO_CONTENT


router = APIRouter(tags=["snowplow"])


def pixel_gif():
    return base64.b64decode(
        b"R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
    )


pixel = pixel_gif()


@router.options("/tracker", include_in_schema=False)
async def tracker_cors():
    return


@router.post("/tracker", summary="Snowplow JS Tracker endpoint")
async def tracker(
    request: Request,
    body: models.PayloadModel,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    cookie: Optional[str] = Header(None),
):
    """
    Collects data from web with sp.js
    \f
    :param request: FastApi request instance
    :param body: Snowplow payload data
    :param user_agent: Browser User-Agent header
    :param x_forwarded_for: User IP
    :param cookie: Browser's cookies
    :return:
    """

    data = await process_data(body, user_agent, x_forwarded_for, cookie)
    await request.app.state.connector.insert(data)

    return Response(status_code=HTTP_204_NO_CONTENT)


@router.get("/i", summary="Snowplow JS Tracker GET endpoint", response_class=Response)
async def get_tracker(
    request: Request,
    params: models.PayloadElementBaseModel = Depends(),
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    cookie: Optional[str] = Header(None),
):

    data = await process_data(params, user_agent, x_forwarded_for, cookie)
    await request.app.state.connector.insert(data)

    return Response(content=pixel, media_type="image/gif")
