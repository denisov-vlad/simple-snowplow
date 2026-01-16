"""
Health check endpoint for Simple Snowplow.

Provides a health probe that checks database connectivity
and returns the current application status.
"""

import structlog
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.status import HTTP_200_OK, HTTP_502_BAD_GATEWAY

logger = structlog.get_logger(__name__)


async def probe(request: Request) -> JSONResponse:
    """
    Health check probe endpoint.

    Checks ClickHouse connectivity and returns status information.

    Args:
        request: The incoming request

    Returns:
        JSON response with health status and table information
    """
    try:
        query = await request.app.state.ch_client.query("SELECT 1")
        ch_healthy = query.first_row[0] == 1
    except Exception as e:
        logger.warning("ClickHouse health check failed", error=str(e))
        ch_healthy = False

    status = {"clickhouse": ch_healthy}

    # Determine overall health
    is_healthy = all(status.values())
    status_code = HTTP_200_OK if is_healthy else HTTP_502_BAD_GATEWAY

    # Build response
    response_data = {
        "status": jsonable_encoder(status),
        "healthy": is_healthy,
    }

    # Add table info if healthy
    if ch_healthy:
        try:
            response_data["table"] = await request.app.state.connector.get_table_name()
        except Exception as e:
            logger.warning("Failed to get table name", error=str(e))

    return JSONResponse(content=response_data, status_code=status_code)
