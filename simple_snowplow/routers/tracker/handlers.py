"""
Core data processing handlers for Snowplow events.
"""

from typing import Any

import structlog
from elasticapm.contrib.asyncio.traces import async_capture_span

from routers.tracker.models.snowplow import (
    PayloadElementModel,
    PayloadModel,
)
from routers.tracker.parsers.ip import convert_ip
from routers.tracker.parsers.payload import parse_payload
from routers.tracker.parsers.useragent import parse_agent

logger = structlog.get_logger(__name__)


@async_capture_span()
async def process_data(
    body: PayloadElementModel | PayloadModel,
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
    ua_data = await parse_agent(user_agent)
    base.update(ua_data)

    # Extract payload data
    if isinstance(body, PayloadModel):
        data = body.data
    else:
        data = [body]

    # Process each payload element
    result = []
    for item in data:
        payload_data = await parse_payload(item, cookies)
        item_data = {**base, **payload_data.model_dump()}
        logger.info("Processed item", item_data=payload_data)
        result.append(item_data)

    return result
