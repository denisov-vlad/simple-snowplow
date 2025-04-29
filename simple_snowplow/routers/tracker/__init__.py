"""
Tracker module for Snowplow event collection.

This module provides endpoints for collecting tracking data from web applications
and services using the Snowplow tracking protocol.
"""

from core.config import settings
from fastapi.responses import Response
from fastapi.routing import APIRouter

from .routes import sendgrid_event, tracker_cors, tracker_get, tracker_post

# Get endpoint configuration from settings
endpoints = settings.common.snowplow.endpoints


router = APIRouter(tags=["snowplow"])

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
