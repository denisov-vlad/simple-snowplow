"""
Application lifespan management for Simple Snowplow.

Handles startup and shutdown events, including database connection
pooling and resource cleanup.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from clickhouse_connect import get_async_client
from clickhouse_connect.driver.httputil import get_pool_manager
from fastapi import FastAPI

from .config import settings
from .exceptions import ConnectionError

logger = structlog.get_logger(__name__)

PERFORMANCE_CONFIG = settings.performance
CLICKHOUSE_CONFIG = settings.clickhouse


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifecycle.

    Initializes database connections on startup and cleans up on shutdown.

    Args:
        application: The FastAPI application instance

    Yields:
        None during application runtime

    Raises:
        ConnectionError: If database connection fails
    """
    # Import here to avoid circular imports
    from routers.tracker.db.clickhouse import ClickHouseConnector

    logger.info(
        "Starting application",
        db_host=CLICKHOUSE_CONFIG.connection.host,
        db_pool_size=PERFORMANCE_CONFIG.db_pool_size,
    )

    try:
        # Create connection pool
        pool_mgr = get_pool_manager(maxsize=PERFORMANCE_CONFIG.db_pool_size)

        # Create async ClickHouse client
        application.state.ch_client = await get_async_client(
            **CLICKHOUSE_CONFIG.connection.model_dump(),
            query_limit=0,  # No query size limit
            pool_mgr=pool_mgr,
        )

        # Initialize connector with the primary client
        application.state.connector = ClickHouseConnector(
            application.state.ch_client,
            **CLICKHOUSE_CONFIG.configuration.model_dump(),
        )

        logger.info("Database connection established")

    except Exception as e:
        logger.error("Failed to connect to database", error=str(e))
        raise ConnectionError(
            "Failed to establish database connection",
            {"host": CLICKHOUSE_CONFIG.connection.host, "error": str(e)},
        ) from e

    yield

    # Cleanup on shutdown
    logger.info("Shutting down application")

    try:
        await application.state.ch_client.close()
        logger.info("Database connection closed")
    except Exception as e:
        logger.warning("Error closing database connection", error=str(e))
