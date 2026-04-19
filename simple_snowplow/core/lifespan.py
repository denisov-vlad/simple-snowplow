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
from .healthcheck import ClickHouseHealthChecker

logger = structlog.get_logger(__name__)

PERFORMANCE_CONFIG = settings.performance
CLICKHOUSE_CONFIG = settings.clickhouse
INGEST_CONFIG = settings.ingest


def _build_clickhouse_insert_settings() -> dict[str, int]:
    """Build ClickHouse insert settings for direct writes."""

    if not INGEST_CONFIG.direct.async_insert:
        return {}

    return {
        "async_insert": 1,
        "wait_for_async_insert": int(INGEST_CONFIG.direct.wait_for_async_insert),
    }


async def _create_clickhouse_client():
    """Create the shared ClickHouse client."""

    pool_mgr = get_pool_manager(maxsize=PERFORMANCE_CONFIG.db_pool_size)
    return await get_async_client(
        **CLICKHOUSE_CONFIG.connection.model_dump(),
        query_limit=0,
        pool_mgr=pool_mgr,
    )


async def _configure_direct_ingest(application: FastAPI) -> None:
    """Initialize direct ClickHouse ingest."""

    from routers.tracker.db.clickhouse import ClickHouseConnector

    application.state.ch_client = await _create_clickhouse_client()
    application.state.connector = ClickHouseConnector(
        application.state.ch_client,
        insert_settings=_build_clickhouse_insert_settings(),
        **CLICKHOUSE_CONFIG.configuration.model_dump(),
    )
    application.state.health_checker = ClickHouseHealthChecker(
        application.state.ch_client,
    )
    application.state._closeables.append(application.state.ch_client)


async def _configure_rabbitmq_ingest(application: FastAPI) -> None:
    """Initialize RabbitMQ-backed ingest."""

    from ingest import RabbitMQHealthChecker, RabbitMQPublisher

    rabbitmq_config = INGEST_CONFIG.rabbitmq
    clickhouse_config = CLICKHOUSE_CONFIG.configuration

    application.state.ch_client = None
    application.state.connector = await RabbitMQPublisher.create(
        config=rabbitmq_config,
        tables=clickhouse_config.tables,
        database=clickhouse_config.database,
        cluster_name=clickhouse_config.cluster_name,
    )
    application.state.health_checker = RabbitMQHealthChecker(
        application.state.connector.channel,
        rabbitmq_config.queue_name,
        rabbitmq_config.resolved_failed_queue_name,
    )
    application.state._closeables.append(application.state.connector)


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
    backend_host = (
        INGEST_CONFIG.rabbitmq.host
        if INGEST_CONFIG.mode == "rabbitmq"
        else CLICKHOUSE_CONFIG.connection.host
    )

    application.state._closeables = []
    application.state.ingest_mode = INGEST_CONFIG.mode

    logger.info(
        "Starting application",
        ingest_mode=INGEST_CONFIG.mode,
        backend_host=backend_host,
    )

    try:
        if INGEST_CONFIG.mode == "rabbitmq":
            await _configure_rabbitmq_ingest(application)
        else:
            await _configure_direct_ingest(application)

        logger.info("Ingest backend initialized")

    except Exception as e:
        logger.error("Failed to initialize ingest backend", error=str(e))
        raise ConnectionError(
            "Failed to initialize ingest backend",
            {
                "mode": INGEST_CONFIG.mode,
                "host": backend_host,
                "error": str(e),
            },
        ) from e

    yield

    # Cleanup on shutdown
    logger.info("Shutting down application")

    for resource in reversed(application.state._closeables):
        try:
            await resource.close()
        except Exception as e:
            logger.warning("Error closing resource", error=str(e))
