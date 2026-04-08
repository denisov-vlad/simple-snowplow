"""
Health check endpoint for Simple Snowplow.

Provides health probes for the active ingest backend.
"""

import structlog
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.status import HTTP_200_OK, HTTP_502_BAD_GATEWAY

logger = structlog.get_logger(__name__)


class ClickHouseHealthChecker:
    """Health checker for direct ClickHouse ingest."""

    def __init__(self, client) -> None:
        self.client = client

    async def check(self) -> dict[str, bool]:
        """Check ClickHouse connectivity."""

        healthy = True
        try:
            query = await self.client.query("SELECT 1")
            healthy = query.first_row[0] == 1
        except Exception as exc:
            logger.warning("ClickHouse health check failed", error=str(exc))
            healthy = False

        return {"clickhouse": healthy}


async def probe(request: Request) -> JSONResponse:
    """
    Health check probe endpoint.

    Checks the active ingest backend and returns status information.

    Args:
        request: The incoming request

    Returns:
        JSON response with health status and table information
    """
    health_checker = request.app.state.health_checker
    status = await health_checker.check()

    # Determine overall health
    is_healthy = all(status.values())
    status_code = HTTP_200_OK if is_healthy else HTTP_502_BAD_GATEWAY

    # Build response
    response_data = {
        "status": jsonable_encoder(status),
        "healthy": is_healthy,
        "ingest_mode": request.app.state.ingest_mode,
    }

    # Add table info if healthy
    if is_healthy:
        try:
            response_data["table"] = await request.app.state.connector.get_table_name()
        except Exception as exc:
            logger.warning("Failed to get table name", error=str(exc))

    return JSONResponse(content=response_data, status_code=status_code)
