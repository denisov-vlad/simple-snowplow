from typing import List
from typing import Optional

import elasticapm
from clickhouse_connect.datatypes.registry import get_from_name
from clickhouse_connect.driver.asyncclient import AsyncClient
from routers.tracker.db.clickhouse.convert import table_fields


class ClickHouseConnector:
    def __init__(
        self,
        conn: AsyncClient,
        cluster_name: Optional[str] = None,
        database: str = "snowplow",
        **params,
    ):
        self.conn = conn
        self.cluster = cluster_name
        self.cluster_condition = self._make_on_cluster(cluster_name)
        self.database = database
        self.params = params
        self.tables = self.get_tables()
        self.table = self.get_table_name()

        self.async_settings = {"async_insert": 1, "wait_for_async_insert": 0}

    def get_tables(self):
        tables_names = {}

        for table_type, table_info in self.params["tables"].items():
            table_name = table_info["name"]
            if not table_info.get("enabled", True):
                continue
            if table_name:
                if "." in table_name:
                    tables_names[table_type] = table_name
                else:
                    tables_names[table_type] = f"{self.database}.{table_name}"
            else:
                tables_names[table_type] = f"{self.database}.{table_type}"

        return tables_names

    @staticmethod
    def _make_on_cluster(cluster_name: Optional[str] = None) -> str:
        if cluster_name is None or not cluster_name:
            return ""
        return f"ON CLUSTER {cluster_name}"

    async def create_db(self):
        for table_name in self.tables.values():
            db, table = table_name.split(".")
            await self.conn.command(
                f"CREATE DATABASE IF NOT EXISTS {db} {self.cluster_condition}",
            )

    async def create_local_table(self):

        columns = []
        for c in table_fields:
            col = f"`{c['column_name']}` {c['type'].name}"
            if c.get("default_type") is not None:
                col += f" {c['default_type']} {c['default_expression']}"
            columns.append(col)

        await self.conn.command(
            f"CREATE TABLE IF NOT EXISTS {self.tables["local"]} {self.cluster_condition} "
            f"({', '.join(columns)}) "
            f"ENGINE = {self.params['tables']['local']['engine']} "
            "PARTITION BY (toYYYYMM(time), event_type) "
            f"ORDER BY ({self.params['tables']['local']['order_by']}) "
            "SAMPLE BY cityHash64(device_id) "
            "SETTINGS index_granularity = 8192;",
        )

    async def create_buffer_table(self):
        source_db, source_table = self.tables["local"].split(".")

        await self.conn.command(
            f"CREATE TABLE IF NOT EXISTS {self.tables["buffer"]}  {self.cluster_condition} "
            f"AS {self.tables["local"]} ENGINE = Buffer("
            f"'{source_db}', '{source_table}', 16, 10, 100, 10000, 1000000, 10000000, 100000000);",
        )

    async def create_distributed_table(self):
        if "buffer" in self.tables:
            source_db, source_table = self.tables["buffer"].split(".")
        else:
            source_db, source_table = self.tables["local"].split(".")

        await self.conn.command(
            f"CREATE TABLE IF NOT EXISTS {self.tables["distributed"]} {self.cluster_condition} "
            f"AS {self.tables["local"]} ENGINE = Distributed("
            f"'{self.cluster}', '{source_db}', '{source_table}', cityHash64(device_id));",
        )

    async def create_all(self):
        await self.create_db()
        await self.create_local_table()
        if "buffer" in self.tables:
            await self.create_buffer_table()

        if self.cluster:
            await self.create_distributed_table()

    @elasticapm.async_capture_span()
    async def insert(self, rows: List[dict]):
        for r in rows:
            column_names = []
            column_types = []

            row = []

            for field in table_fields:
                payload_name = field["payload_name"]
                value = r.get(payload_name)

                if value is None or value == "":
                    continue

                column_names.append(field["column_name"])
                column_types.append(get_from_name(field["type"].name))
                row.append(value)

            async with elasticapm.async_capture_span("clickhouse_query"):
                await self.conn.insert(
                    self.table,
                    data=[row],
                    column_names=column_names,
                    column_types=column_types,
                    settings=self.async_settings,
                )

    def get_table_name(self):
        if self.cluster:
            return self.tables["distributed"]
        else:
            return self.tables["local"]
