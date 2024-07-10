from datetime import datetime
from typing import List
from typing import Optional

import elasticapm
from aiochclient import ChClient
from orjson import dumps
from routers.tracker.db.clickhouse.convert import table_fields


class ClickHouseConnector:
    def __init__(
        self,
        conn: ChClient,
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

        if params.get("chbulk_enabled", False):
            self.async_settings = ""
        else:
            self.async_settings = "SETTINGS async_insert=1, wait_for_async_insert=0"

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
            await self.conn.execute(
                f"""
                CREATE DATABASE IF NOT EXISTS {db} {self.cluster_condition}
            """,
            )

    async def create_local_table(self):
        await self.conn.execute(
            f"""
        CREATE TABLE IF NOT EXISTS {self.tables["local"]} {self.cluster_condition}
        (
            `app_id` LowCardinality(String),
            `platform` Enum8(
                'web' = 1,
                'mob' = 2,
                'pc' = 3,
                'srv' = 4,
                'app' = 5,
                'tv' = 6,
                'cnsl' = 7,
                'iot' = 8
            ),
            `app` Tuple(
                version String,
                build String
            ),
            `page` String DEFAULT '',
            `referer` Nullable(String) DEFAULT NULL,
            `event_type` Enum8(
                'pv' = 1, 'pp' = 2, 'ue' = 3, 'se' = 4, 'tr' = 5, 'ti' = 6, 's' = 7
            ),
            `event_id` UUID,
            `view_id` UUID,
            `session_id` UUID,
            `visit_count` Nullable(UInt64),
            `session` Tuple(
                event_index Nullable(UInt64),
                previous_session_id Nullable(UUID),
                first_event_id Nullable(UUID),
                first_event_time Nullable(DateTime64(3, 'UTC')),
                storage_mechanism LowCardinality(String),
                unstructured String
            ),

            `amp` Tuple(
                device_id String,
                client_id String,
                session_id UInt64,
                visit_count UInt64,
                session_engaged UInt8,
                first_event_time Nullable(DateTime64(3, 'UTC')),
                previous_session_time Nullable(DateTime64(3, 'UTC')),
                view_id String
            ),
            `device_id` UUID,
            `user_id` Nullable(String) DEFAULT NULL,
            `time` DateTime64(3, 'UTC'),
            `timezone` Nullable(String) DEFAULT NULL,
            `time_extra` Tuple(
                `time_user` DateTime64(3, 'UTC'),
                `time_sent` DateTime64(3, 'UTC')
            ),
            `title` Nullable(String) DEFAULT NULL,
            `screen` Tuple(
                type String,
                view_controller String,
                top_view_controller String,
                activity String,
                fragment String,
                unstructured String),
            `page_data` String,
            `user_data` String,
            `user_ip` IPv4,
            `geolocation` String,
            `user_agent` String DEFAULT '',
            `browser` Tuple(
                family LowCardinality(String),
                version String,
                cookie UInt8,
                charset LowCardinality(String),
                color_depth UInt8,
                unstructured String),
            `os` Tuple(
                family LowCardinality(String),
                version String,
                language LowCardinality(String)
            ),
            `device` Tuple(
                brand LowCardinality(String),
                model LowCardinality(String)
            ),
            `device_is` Tuple(mobile Int8, tablet Int8, touch Int8, pc Int8, bot Int8),
            `device_extra` Tuple(
                carrier LowCardinality(String),
                network_type Enum8('' = 1, 'mobile' = 2, 'wifi' = 3, 'offline' = 4),
                network_technology LowCardinality(String),
                open_idfa String,
                apple_idfa String,
                apple_idfv String,
                android_idfa String,
                battery_level UInt8,
                battery_state Enum8(
                    '' = 1, 'unplugged' = 2, 'charging' = 3, 'full' = 4
                ),
                low_power_mode Int8
            ),
            `resolution` Tuple(browser String, viewport String, page String),
            `event` Tuple(
                action LowCardinality(String),
                category LowCardinality(String),
                label String,
                property String,
                value Float32,
                unstructured String
            ),
            `extra` String,
            `tracker` Tuple(
                version LowCardinality(String),
                namespace LowCardinality(String)
            )
        )
        ENGINE = {self.params["tables"]["local"]["engine"]}
        PARTITION BY (toYYYYMM(time), event_type)
        ORDER BY ({self.params["tables"]["local"]["order_by"]})
        SAMPLE BY cityHash64(device_id)
        SETTINGS index_granularity = 8192;
        """,
        )

    async def create_buffer_table(self):
        source_db, source_table = self.tables["local"].split(".")

        await self.conn.execute(
            f"""
        CREATE TABLE IF NOT EXISTS {self.tables["buffer"]}  {self.cluster_condition}
        AS {self.tables["local"]} ENGINE = Buffer(
            '{source_db}',
            '{source_table}',
            16, 10, 100, 10000, 1000000, 10000000, 100000000
        );
        """,
        )

    async def create_distributed_table(self):
        if "buffer" in self.tables:
            source_db, source_table = self.tables["buffer"].split(".")
        else:
            source_db, source_table = self.tables["local"].split(".")

        await self.conn.execute(
            f"""
        CREATE TABLE IF NOT EXISTS {self.tables["distributed"]} {self.cluster_condition}
        AS {self.tables["local"]} ENGINE = Distributed(
            '{self.cluster}', '{source_db}', '{source_table}', cityHash64(device_id)
        );
        """,
        )

    async def create_all(self):
        await self.create_db()
        await self.create_local_table()
        if "buffer" in self.tables:
            await self.create_buffer_table()

        if self.cluster:
            await self.create_distributed_table()

    @staticmethod
    async def _convert_types(value):
        if isinstance(value, dict):
            value = str(dumps(value), "utf-8")
        elif isinstance(value, datetime):
            # clickhouse driver doesn't support Datetime64 insert from datetime type
            value = value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return value

    @elasticapm.async_capture_span()
    async def insert(self, rows: List[dict]):
        for r in rows:
            columns_names = []

            row = []

            for field in table_fields:
                payload_name = field["payload_name"]
                if isinstance(payload_name, tuple):
                    value = tuple(
                        [await self._convert_types(r.get(v)) for v in payload_name],
                    )
                else:
                    value = await self._convert_types(r.get(payload_name))

                if value is None or value == "":
                    continue

                columns_names.append(field["column_name"])
                row.append(value)

            columns_names = f"({','.join(columns_names)})"

            async with elasticapm.async_capture_span("clickhouse_query"):
                await self.conn.execute(
                    f"INSERT INTO {self.table} {columns_names} "
                    f"{self.async_settings} VALUES ",
                    tuple(row),
                )

    def get_table_name(self):
        if self.cluster:
            return self.tables["distributed"]
        else:
            return self.tables["local"]
