import asyncio
from typing import Any
from typing import List
from typing import Optional

import elasticapm
import structlog
from clickhouse_connect.datatypes.registry import get_from_name
from clickhouse_connect.driver.asyncclient import AsyncClient
from clickhouse_connect.driver.exceptions import ClickHouseError
from routers.tracker.db.clickhouse.convert import fields
from routers.tracker.models import Model


logger = structlog.get_logger(__name__)


class ClickHouseConnector:
    def __init__(
        self,
        conn: AsyncClient,
        cluster_name: Optional[str] = None,
        database: str = "snowplow",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        pool: List[AsyncClient] = None,
        pool_in_use: List[bool] = None,
        pool_lock: Any = None,
        **params,
    ):
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
    def _make_on_cluster(cluster_name: Optional[str] = None) -> str:
        if cluster_name is None or not cluster_name:
            return ""
        return f"ON CLUSTER {cluster_name}"

    async def get_connection(self):
        """Get an available connection from the pool."""
        if not self.pool_lock:
            return self.conn

        async with self.pool_lock:
            for i, in_use in enumerate(self.pool_in_use):
                if not in_use:
                    self.pool_in_use[i] = True
                    return self.pool[i], i

            # All connections are in use, return the default one
            return self.conn, -1

    async def release_connection(self, connection_index):
        """Release a connection back to the pool."""
        if connection_index >= 0 and self.pool_lock:
            async with self.pool_lock:
                self.pool_in_use[connection_index] = False

    async def _execute_with_retry(self, operation_name, operation, *args, **kwargs):
        """Execute database operation with retries on failure."""
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

    async def create_db(self):
        databases = []

        for _group, tables in self.params["tables"].items():
            for _type, table_info in tables.items():
                if not isinstance(table_info, dict):
                    continue
                if table_info["name"] and "." in table_info["name"]:
                    db = table_info["name"].split(".")[0]
                    if db not in databases:
                        databases.append(db)

        for db in databases:
            await self._execute_with_retry(
                "create_database",
                self.conn.command,
                f"CREATE DATABASE IF NOT EXISTS {db} {self.cluster_condition}",
            )

    async def get_full_table_name(self, table_name):
        if "." in table_name:
            return table_name
        return f"{self.database}.{table_name}"

    async def create_local_table(self, table_group: str = "snowplow"):
        table_data = self.tables[table_group]["local"]

        columns = []
        for c in fields[table_group]:
            col = f"`{c['column_name']}` {c['type'].name}"
            if c.get("default_type") is not None:
                col += f" {c['default_type']} {c['default_expression']}"
            columns.append(col)

        query = (
            f"CREATE TABLE IF NOT EXISTS {await self.get_full_table_name(table_data['name'])} "
            f"{self.cluster_condition} ({', '.join(columns)}) "
            f"ENGINE = {table_data['engine']} "
            f"PARTITION BY {table_data['partition_by']} "
            f"ORDER BY ({table_data['order_by']}) "
            f"SAMPLE BY {table_data['sample_by']} "
            f"SETTINGS {table_data['settings']};"
        )

        await self._execute_with_retry(
            "create_local_table",
            self.conn.command,
            query,
        )

    async def create_distributed_table(self, table_group: str = "snowplow"):
        table_data = self.tables[table_group]["distributed"]

        if "." in self.tables[table_group]["local"]["name"]:
            source_db, source_table = self.tables[table_group]["local"]["name"].split(
                ".",
            )
        else:
            source_db = self.database
            source_table = self.tables[table_group]["local"]["name"]

        query = (
            f"CREATE TABLE IF NOT EXISTS {await self.get_full_table_name(table_data['name'])} "
            f"{self.cluster_condition} AS {source_db}.{source_table} ENGINE = Distributed("
            f"'{self.cluster}', '{source_db}', '{source_table}', {table_data['sample_by']});"
        )

        await self._execute_with_retry(
            "create_distributed_table",
            self.conn.command,
            query,
        )

    async def create_all(self):
        await self.create_db()

        table_group = "snowplow"
        await self.create_local_table(table_group)
        if self.cluster:
            await self.create_distributed_table(table_group)

        if self.tables.sendgrid.enabled:
            table_group = "sendgrid"
            await self.create_local_table(table_group)
            if self.cluster:
                await self.create_distributed_table(table_group)

    @elasticapm.async_capture_span()
    async def insert(self, rows: List[dict], table_group: str = "snowplow"):
        if not rows:
            logger.debug("No rows to insert")
            return

        table_name = await self.get_table_name(table_group)
        full_table_name = await self.get_full_table_name(table_name)

        # Process rows in batches for better performance
        batch_size = 100  # Adjust based on your data volume and memory constraints
        batches = [rows[i : i + batch_size] for i in range(0, len(rows), batch_size)]

        for batch in batches:
            # Process each batch with a connection from the pool
            connection, connection_index = await self.get_connection()

            try:
                column_names = []
                column_types = []
                batch_rows = []

                # Extract schema from the first row
                sample_row = batch[0]
                if isinstance(sample_row, Model):
                    sample_row = sample_row.model_dump()

                for field in fields[table_group]:
                    payload_name = field["payload_name"]

                    if payload_name is None:
                        continue

                    column_names.append(field["column_name"])
                    column_types.append(get_from_name(field["type"].name))

                # Process all rows in the batch
                for r in batch:
                    row = []

                    if isinstance(r, Model):
                        r = r.model_dump()

                    for field in fields[table_group]:
                        payload_name = field["payload_name"]

                        if payload_name is None:
                            continue

                        if isinstance(payload_name, tuple):
                            value = tuple([r.get(v) for v in payload_name])
                        else:
                            value = r.get(payload_name)

                        row.append(value)

                    batch_rows.append(row)

                async with elasticapm.async_capture_span("clickhouse_query"):
                    await connection.insert(
                        full_table_name,
                        data=batch_rows,
                        column_names=column_names,
                        column_types=column_types,
                        settings=self.async_settings,
                    )
            finally:
                await self.release_connection(connection_index)

    async def get_table_name(self, table_group: str = "snowplow"):
        if self.cluster:
            return self.tables[table_group]["distributed"]["name"]
        else:
            return self.tables[table_group]["local"]["name"]
