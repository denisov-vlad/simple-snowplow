import asyncio
from contextlib import asynccontextmanager
from clickhouse_connect import get_async_client
from config import settings
from routers.tracker.db.clickhouse import ClickHouseConnector

# Configuration constants for performance tuning
MAX_CONCURRENT_CONNECTIONS = settings.get('performance.max_concurrent_connections', 100)
DB_POOL_SIZE = settings.get('performance.db_pool_size', 5)
DB_POOL_OVERFLOW = settings.get('performance.db_pool_overflow', 10)

@asynccontextmanager
async def lifespan(application):
    # Create database connection pool with improved parameters
    ch_clients = []
    for _ in range(DB_POOL_SIZE):
        client = await get_async_client(
            **settings.clickhouse.connection,
            query_limit=0,  # No query size limit
        )
        ch_clients.append(client)
    
    # Store the connection pool in app state
    application.state.ch_pool = ch_clients
    application.state.ch_client = ch_clients[0]  # Default client for backward compatibility
    application.state.pool_in_use = [False] * DB_POOL_SIZE
    application.state.pool_lock = asyncio.Lock()
    
    # Initialize connector with the primary client
    application.state.connector = ClickHouseConnector(
        application.state.ch_client,
        pool=ch_clients,
        pool_in_use=application.state.pool_in_use,
        pool_lock=application.state.pool_lock,
        **settings.clickhouse.configuration,
    )
    
    await application.state.connector.create_all()

    yield

    # Close all connections in the pool
    for client in ch_clients:
        client.close() 