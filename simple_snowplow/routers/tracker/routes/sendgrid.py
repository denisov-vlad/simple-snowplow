"""
Route handlers for SendGrid webhook events.
"""
import elasticapm
from fastapi import Request
from fastapi import Response
from routers.tracker.schemas.models import SendgridElementBaseModel
from starlette.status import HTTP_204_NO_CONTENT


@elasticapm.async_capture_span()
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
    await request.app.state.connector.insert_rows(body, table_group="sendgrid")
    return Response(status_code=HTTP_204_NO_CONTENT)
