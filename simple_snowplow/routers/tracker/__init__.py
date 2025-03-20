import base64
from typing import Any
from typing import Callable
from typing import Coroutine
from typing import Optional

import orjson
from config import settings
from fastapi import Depends
from fastapi import Header
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from fastapi.routing import APIRoute
from fastapi.routing import APIRouter
from json_repair import repair_json
from pydantic import IPvAnyAddress
from routers.tracker import models
from routers.tracker.handlers import process_data
from starlette.status import HTTP_204_NO_CONTENT


custom_route_response = Callable[[Request], Coroutine[Any, Any, Response]]


class CustomRoute(APIRoute):
    def get_route_handler(self) -> custom_route_response:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> custom_route_response:
            if request.method == "POST":
                raw_body = await request.body()
                try:
                    body = orjson.loads(raw_body)
                    request._json = body
                except orjson.JSONDecodeError:
                    try:
                        body = orjson.loads(repair_json(raw_body.decode("utf-8")))
                        request._json = body
                    except Exception as e:
                        raise RequestValidationError([e])
            return await original_route_handler(request)

        return custom_route_handler


router = APIRouter(tags=["snowplow"], route_class=CustomRoute)


def pixel_gif():
    img = b"R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
    return base64.b64decode(img)


pixel = pixel_gif()

endpoints = settings.common.snowplow.endpoints


@router.options(endpoints.post_endpoint, include_in_schema=False)
@router.options(endpoints.get_endpoint, include_in_schema=False)
async def tracker_cors():
    return


@router.post(endpoints.post_endpoint, summary="Snowplow JS Tracker endpoint")
async def tracker(
    request: Request,
    body: models.PayloadModel,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: IPvAnyAddress | str | None = Header(None),
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


@router.get(
    endpoints.get_endpoint,
    summary="Snowplow JS Tracker GET endpoint",
    response_class=Response,
)
async def get_tracker(
    request: Request,
    params: models.PayloadElementBaseModel = Depends(),
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: IPvAnyAddress | str | None = Header(None),
    cookie: Optional[str] = Header(None),
):
    data = await process_data(params, user_agent, x_forwarded_for, cookie)
    await request.app.state.connector.insert(data)

    return Response(content=pixel, media_type="image/gif")


@router.post(endpoints.sendgrid_endpoint, summary="Sendgrid event endpoint")
async def sendgrid_event(
    request: Request,
    body: list[models.SendgridElementBaseModel],
):
    """
    Collects data from Sendgrid events
    \f
    :param request: FastApi request instance
    :param body: Sendgrid payload data
    :param user_agent: Browser User-Agent header
    :param x_forwarded_for: User IP
    :param cookie: Browser's cookies
    :return:
    """

    await request.app.state.connector.insert(body, table_group="sendgrid")

    return Response(status_code=HTTP_204_NO_CONTENT)
