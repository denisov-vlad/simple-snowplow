"""
ClickHouse database connector for Simple Snowplow.

This module provides a connection to ClickHouse.
"""

from typing import Any

import elasticapm
import structlog
from clickhouse_connect.driver.asyncclient import AsyncClient
from clickhouse_connect.driver.exceptions import ClickHouseError, DatabaseError

from routers.tracker.db.clickhouse.schemas.snowplow import TupleColumnDef

logger = structlog.get_logger(__name__)


class ClickHouseConnector:
    """
    ClickHouse database connector.
    """

    def __init__(
        self,
        conn: AsyncClient,
        cluster_name: str | None = None,
        database: str = "snowplow",
        **params,
    ):
        """
        Initialize the ClickHouse connector.

        Args:
            conn: The ClickHouse connection
            cluster_name: Optional cluster name for distributed tables
            database: Default database name
            **params: Additional parameters
        """
        self.conn = conn
        self.cluster = cluster_name
        self.cluster_condition = self._make_on_cluster(cluster_name)
        self.database = database
        self.params = params
        self.tables = self.params["tables"]
        self.async_settings = {"async_insert": 1, "wait_for_async_insert": 0}

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
        try:
            await self.conn.command(query)
        except (ClickHouseError, DatabaseError) as e:
            await logger.error("Database command failed", error=str(e), query=query)
            raise

    async def query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ):
        """
        Execute a ClickHouse query.

        Args:
            query: The query to execute
            parameters: Optional query parameters

        Returns:
            The query results
        """
        try:
            return await self.conn.query(query, parameters=parameters)
        except (ClickHouseError, DatabaseError) as e:
            await logger.error(
                "Database query failed",
                error=str(e),
                query=query,
                parameters=parameters,
            )
            raise

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
        rows: list[dict[str, Any]],
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
            await logger.debug("No rows to insert")
            return

        table_name = await self.get_table_name(table_group)
        full_table_name = await self.get_full_table_name(table_name)
        fields = get_fields_for_table_group(table_group)

        for row in rows:
            column_names = []
            column_types = []
            values = []

            for field in fields:
                if isinstance(field, TupleColumnDef):
                    value = tuple([
                        row.get(v.payload_name)
                        for v in field.elements
                        if v.payload_name is not None
                    ])
                else:
                    if field.payload_name is None:
                        continue
                    value = row.get(field.payload_name)

                column_names.append(field.name)
                column_types.append(field.type)
                values.append(value)

            async with elasticapm.async_capture_span("clickhouse_query"):
                try:
                    await self.conn.insert(
                        full_table_name,
                        data=[values],
                        column_names=column_names,
                        column_types=column_types,
                        settings=self.async_settings,
                    )
                except (ClickHouseError, DatabaseError) as e:
                    await logger.error(
                        "Insert operation failed",
                        error=str(e),
                        column_names=column_names,
                        column_types=column_types,
                        values=values,
                    )
                    raise
