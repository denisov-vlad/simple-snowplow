"""
Tracker module for Snowplow event collection.

This module provides endpoints for collecting tracking data from web applications and services
using the Snowplow tracking protocol.
"""
from typing import Any
from typing import Callable
from typing import Coroutine

import orjson
from core.config import settings
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from fastapi.routing import APIRoute
from fastapi.routing import APIRouter
from json_repair import repair_json

from .routes import sendgrid_event
from .routes import tracker_cors
from .routes import tracker_get
from .routes import tracker_post

# Get endpoint configuration from settings
endpoints = settings.common.snowplow.endpoints


class CustomRoute(APIRoute):
    """
    Custom route class that handles JSON parsing with repair capability.

    This is used to automatically fix malformed JSON in request bodies
    before they are processed by the route handlers.
    """

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        """
        Get a custom route handler that pre-processes request body.

        Returns:
            Asynchronous route handler function
        """
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            """
            Custom route handler with JSON repair functionality.

            Args:
                request: FastAPI request object

            Returns:
                Response from the original route handler

            Raises:
                RequestValidationError: If JSON cannot be parsed after repair
            """
            if request.method == "POST":
                raw_body = await request.body()
                try:
                    # Try normal JSON parsing first
                    body = orjson.loads(raw_body)
                    request._json = body
                except orjson.JSONDecodeError:
                    try:
                        # If that fails, try repairing the JSON
                        body = orjson.loads(repair_json(raw_body.decode("utf-8")))
                        request._json = body
                    except Exception as e:
                        # If repair fails, raise validation error
                        raise RequestValidationError([e])

            # Continue with normal request processing
            return await original_route_handler(request)

        return custom_route_handler


# Create the router with custom route class
router = APIRouter(tags=["snowplow"], route_class=CustomRoute)

# Register the CORS options handlers
router.options(endpoints.post_endpoint, include_in_schema=False)(tracker_cors)
router.options(endpoints.get_endpoint, include_in_schema=False)(tracker_cors)

# Register the main Snowplow endpoints
router.post(
    endpoints.post_endpoint,
    summary="Snowplow JS Tracker endpoint",
)(tracker_post)

router.get(
    endpoints.get_endpoint,
    summary="Snowplow JS Tracker GET endpoint",
    response_class=Response,
)(tracker_get)

# Register the SendGrid webhook endpoint
router.post(
    endpoints.sendgrid_endpoint,
    summary="Sendgrid event endpoint",
)(sendgrid_event)
