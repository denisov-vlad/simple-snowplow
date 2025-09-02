from contextlib import asynccontextmanager

from clickhouse_connect import get_async_client
from clickhouse_connect.driver.httputil import get_pool_manager
from routers.tracker.db.clickhouse import ClickHouseConnector, TableManager

from core.config import settings

PERFORMANCE_CONFIG = settings.performance
CLICKHOUSE_CONFIG = settings.clickhouse


@asynccontextmanager
async def lifespan(application):
    pool_mgr = get_pool_manager(maxsize=PERFORMANCE_CONFIG.db_pool_size)

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

    table_manager = TableManager(application.state.connector)

    await table_manager.create_all_tables()

    yield

    await application.state.ch_client.close()
