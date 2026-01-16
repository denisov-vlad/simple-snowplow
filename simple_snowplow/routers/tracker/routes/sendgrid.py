"""
Route handlers for SendGrid webhook events.

This module provides handlers for receiving and processing
SendGrid email event webhooks.
"""

from core.dependencies import DbConnector
from elasticapm.contrib.asyncio.traces import async_capture_span
from fastapi import Response
from routers.tracker.models.sendgrid import SendgridElementBaseModel
from starlette.status import HTTP_204_NO_CONTENT


@async_capture_span()
async def sendgrid_event(
    connector: DbConnector,
    body: list[SendgridElementBaseModel],
) -> Response:
    """
    Handle webhook events from SendGrid.

    Args:
        connector: Database connector (injected)
        body: Request body containing SendGrid events

    Returns:
        Empty response with 204 status code
    """
    data = [event.model_dump() for event in body]

    await connector.insert_rows(data, table_group="sendgrid")
    return Response(status_code=HTTP_204_NO_CONTENT)
