import asyncio
from contextlib import asynccontextmanager

from clickhouse_connect import get_async_client
from routers.tracker.db.clickhouse import ClickHouseConnector, TableManager

from core.config import settings

PERFORMANCE_CONFIG = settings.performance
CLIKCHOUSE_CONFIG = settings.clickhouse


@asynccontextmanager
async def lifespan(application):
    # Create database connection pool with improved parameters
    ch_clients = []
    for _ in range(PERFORMANCE_CONFIG.db_pool_size):
        client = await get_async_client(
            **CLIKCHOUSE_CONFIG.connection.model_dump(),
            query_limit=0,  # No query size limit
        )
        ch_clients.append(client)

    # Store the connection pool in app state
    application.state.ch_pool = ch_clients
    application.state.ch_client = ch_clients[
        0
    ]  # Default client for backward compatibility
    application.state.pool_in_use = [False] * PERFORMANCE_CONFIG.db_pool_size
    application.state.pool_lock = asyncio.Lock()

    # Initialize connector with the primary client
    application.state.connector = ClickHouseConnector(
        application.state.ch_client,
        pool=ch_clients,
        pool_in_use=application.state.pool_in_use,
        pool_lock=application.state.pool_lock,
        **CLIKCHOUSE_CONFIG.configuration.model_dump(),
    )

    table_manager = TableManager(application.state.connector)

    await table_manager.create_all_tables()

    yield

    # Close all connections in the pool
    for client in ch_clients:
        await client.close()
