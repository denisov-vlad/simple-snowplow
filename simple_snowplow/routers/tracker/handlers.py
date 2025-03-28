"""
Core data processing handlers for Snowplow events.
"""

from typing import Any

import elasticapm
import structlog

from routers.tracker.parsers.ip import convert_ip
from routers.tracker.parsers.payload import parse_payload
from routers.tracker.parsers.useragent import parse_agent
from routers.tracker.schemas.models import (
    PayloadElementBaseModel,
    PayloadElementPostModel,
    PayloadModel,
)

logger = structlog.get_logger(__name__)

PayloadType = PayloadElementBaseModel | PayloadElementPostModel | PayloadModel


@elasticapm.async_capture_span()
async def process_data(
    body: PayloadType,
    user_agent: str | None,
    user_ip: Any,
    cookies: str | None,
) -> list[dict[str, Any]]:
    """
    Process incoming event data from various sources.

    This function:
    1. Processes the IP address
    2. Parses the user agent
    3. Extracts and processes payload data
    4. Combines all information into complete event records

    Args:
        body: The request body or parameters
        user_agent: User agent string from headers
        user_ip: IP address from headers
        cookies: Cookie string from headers

    Returns:
        List of processed event records ready for storage
    """
    # Create base record with IP address
    base = {"user_ip": await convert_ip(user_ip)}

    # Add user agent information if available
    if user_agent:
        ua_data = await parse_agent(user_agent)
        base.update(ua_data)

    # Extract payload data
    try:
        data = body.data
    except AttributeError:
        # If body is not a batch payload, treat as single element
        data = [body]

    # Process each payload element
    result = []
    for item in data:
        payload_data = await parse_payload(item, cookies)
        item_data = {**base, **payload_data}
        result.append(item_data)

    return result
