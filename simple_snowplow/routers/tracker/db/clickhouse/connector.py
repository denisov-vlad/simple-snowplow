"""
ClickHouse database connector for Simple Snowplow.

This module provides a connection pool and retry mechanism for ClickHouse.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import elasticapm
import structlog
from clickhouse_connect.datatypes.registry import get_from_name
from clickhouse_connect.driver.asyncclient import AsyncClient
from clickhouse_connect.driver.exceptions import ClickHouseError

from routers.tracker.schemas.models import Model

T = TypeVar("T")

logger = structlog.get_logger(__name__)


class ClickHouseConnector:
    """
    ClickHouse database connector with connection pooling and retry mechanism.
    """

    def __init__(
        self,
        conn: AsyncClient,
        cluster_name: str | None = None,
        database: str = "snowplow",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        pool: list[AsyncClient] | None = None,
        pool_in_use: list[bool] | None = None,
        pool_lock: Any | None = None,
        **params,
    ):
        """
        Initialize the ClickHouse connector.

        Args:
            conn: The primary ClickHouse connection
            cluster_name: Optional cluster name for distributed tables
            database: Default database name
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retry attempts in seconds
            pool: Optional connection pool
            pool_in_use: Optional flags for connection pool usage
            pool_lock: Optional lock for connection pool
            **params: Additional parameters
        """
        self.conn = conn
        self.cluster = cluster_name
        self.cluster_condition = self._make_on_cluster(cluster_name)
        self.database = database
        self.params = params
        self.tables = self.params["tables"]
        self.async_settings = {"async_insert": 1, "wait_for_async_insert": 0}
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Connection pool support
        self.pool = pool or [conn]
        self.pool_in_use = pool_in_use or [False] * len(self.pool)
        self.pool_lock = pool_lock

    @staticmethod
    def _make_on_cluster(cluster_name: str | None = None) -> str:
        """
        Create the ON CLUSTER clause for ClickHouse queries.

        Args:
            cluster_name: The cluster name

        Returns:
            The ON CLUSTER clause or empty string
        """
        if cluster_name is None or not cluster_name:
            return ""
        return f"ON CLUSTER {cluster_name}"

    async def get_connection(self) -> tuple[AsyncClient, int]:
        """
        Get an available connection from the pool.

        Returns:
            Tuple of connection and index
        """
        if not self.pool_lock:
            return self.conn, -1

        async with self.pool_lock:
            for i, in_use in enumerate(self.pool_in_use):
                if not in_use:
                    self.pool_in_use[i] = True
                    return self.pool[i], i

            # All connections are in use, return the default one
            return self.conn, -1

    async def release_connection(self, connection_index: int) -> None:
        """
        Release a connection back to the pool.

        Args:
            connection_index: The index of the connection in the pool
        """
        if connection_index >= 0 and self.pool_lock:
            async with self.pool_lock:
                self.pool_in_use[connection_index] = False

    async def _execute_with_retry(
        self,
        operation_name: str,
        operation: Callable[[Any], Awaitable[T]] | Any,
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Execute database operation with retries on failure.

        Args:
            operation_name: Name of the operation
            operation: The operation to execute
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            The result of the operation

        Raises:
            ClickHouseError: If all retry attempts fail
        """
        connection, connection_index = await self.get_connection()

        try:
            for attempt in range(1, self.max_retries + 1):
                try:
                    if operation_name in ["insert_data", "command", "query"]:
                        # These operations can be executed directly on the connection
                        return await getattr(connection, operation_name.split("_")[0])(
                            *args,
                            **kwargs,
                        )
                    else:
                        # Other operations are methods
                        return await operation(*args, **kwargs)
                except ClickHouseError as e:
                    log = logger.bind(
                        operation=operation_name,
                        attempt=attempt,
                        max_attempts=self.max_retries,
                        error=str(e),
                    )

                    if attempt == self.max_retries:
                        log.error("Database operation failed after all retries")
                        raise

                    log.warning("Database operation failed, retrying...")
                    await asyncio.sleep(
                        self.retry_delay * attempt,
                    )  # Exponential backoff
        finally:
            await self.release_connection(connection_index)

    async def get_full_table_name(self, table_name: str) -> str:
        """
        Get the fully qualified table name.

        Args:
            table_name: The table name

        Returns:
            The fully qualified table name
        """
        if "." in table_name:
            return table_name
        return f"{self.database}.{table_name}"

    async def command(self, query: str) -> None:
        """
        Execute a ClickHouse command.

        Args:
            query: The query to execute
        """
        await self._execute_with_retry("command", self.conn.command, query)

    async def query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a ClickHouse query.

        Args:
            query: The query to execute
            parameters: Optional query parameters

        Returns:
            The query results
        """
        return await self._execute_with_retry(
            "query",
            self.conn.query,
            query,
            parameters=parameters,
        )

    async def get_table_name(self, table_group: str = "snowplow") -> str:
        """
        Get the table name for a specific group.

        Args:
            table_group: The table group

        Returns:
            The table name
        """
        table_name = self.tables[table_group]["local"]["name"]
        if self.cluster:
            table_name = self.tables[table_group]["distributed"]["name"]
        return table_name

    @elasticapm.async_capture_span()
    async def insert_rows(
        self,
        rows: list[dict[str, Any] | Model],
        table_group: str = "snowplow",
    ) -> None:
        """
        Insert rows into the specified table group.

        Args:
            rows: List of rows to insert
            table_group: The table group
        """
        from routers.tracker.db.clickhouse.schemas import get_fields_for_table_group

        if not rows:
            logger.debug("No rows to insert")
            return

        table_name = await self.get_table_name(table_group)
        full_table_name = await self.get_full_table_name(table_name)
        fields = get_fields_for_table_group(table_group)

        for row in rows:
            column_names = []
            column_types = []
            values = []

            for field in fields:
                payload_name = field["payload_name"]

                if payload_name is None:
                    continue

                if isinstance(payload_name, tuple):
                    value = tuple([row.get(v) for v in payload_name])
                else:
                    value = row.get(payload_name)

                column_names.append(field["column_name"])
                column_types.append(get_from_name(field["type"].name))
                values.append(value)

            async with elasticapm.async_capture_span("clickhouse_query"):
                await self._execute_with_retry(
                    "insert_data",
                    self.conn.insert,
                    full_table_name,
                    data=[values],
                    column_names=column_names,
                    column_types=column_types,
                    settings=self.async_settings,
                )
