"""
Route handlers for SendGrid webhook events.
"""

from elasticapm.contrib.asyncio.traces import async_capture_span
from fastapi import Request, Response
from starlette.status import HTTP_204_NO_CONTENT

from routers.tracker.schemas.models import SendgridElementBaseModel


@async_capture_span()
async def sendgrid_event(
    request: Request,
    body: list[SendgridElementBaseModel],
):
    """
    Handle webhook events from SendGrid.

    Args:
        request: FastAPI request object
        body: Request body containing SendGrid events

    Returns:
        Empty response with 204 status code
    """

    data = [event.model_dump() for event in body]

    await request.app.state.connector.insert_rows(data, table_group="sendgrid")
    return Response(status_code=HTTP_204_NO_CONTENT)
