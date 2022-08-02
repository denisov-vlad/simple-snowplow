from typing import Optional

from aiochclient import ChClient


class ClickHouseInit:
    def __init__(
        self,
        conn: ChClient,
        engine: str,
        cluster_name: Optional[str] = None,
        database: str = "snowplow",
        **params,
    ):
        self.conn = conn
        self.engine = engine
        self.cluster = cluster_name
        self.cluster_condition = self._make_on_cluster(cluster_name)
        self.database = database
        self.params = params

    @staticmethod
    def _make_on_cluster(cluster_name: Optional[str] = None) -> str:
        if cluster_name is None or not cluster_name:
            return ""
        return f"ON CLUSTER {cluster_name}"

    async def create_db(self):
        await self.conn.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")

    async def create_local_table(self):
        await self.conn.execute(
            f"""
        CREATE TABLE IF NOT EXISTS {self.database}.local {self.cluster_condition}
        (
            `app_id` LowCardinality(String),
            `platform` Enum8('web' = 1, 'mob' = 2, 'pc' = 3, 'srv' = 4, 'app' = 5, 'tv' = 6, 'cnsl' = 7, 'iot' = 8),
            `app_extra` String DEFAULT '',
            `page` String DEFAULT '',
            `referer` Nullable(String) DEFAULT NULL,
            `event_type` Enum8('pv' = 1, 'pp' = 2, 'ue' = 3, 'se' = 4, 'tr' = 5, 'ti' = 6, 's' = 7),
            `event_id` UUID,
            `view_id` String DEFAULT '',
            `session_id` UUID,
            `visit_count` Nullable(UInt32),
            `session_extra` String DEFAULT '',
            `device_id` UUID,
            `device_id_amp` Nullable(String) DEFAULT NULL,
            `user_id` Nullable(String) DEFAULT NULL,
            `time` DateTime64(3, 'UTC'),
            `timezone` Nullable(String) DEFAULT NULL,
            `time_extra` Tuple(`time_user` DateTime64(3, 'UTC'), `time_sent` DateTime64(3, 'UTC')),
            `title` Nullable(String) DEFAULT NULL,
            `screen_extra` String DEFAULT '',
            `page_data` String DEFAULT '',
            `user_data` String DEFAULT '',
            `user_ip` IPv4,
            `user_agent` String DEFAULT '',
            `browser` Tuple(
                family LowCardinality(String),
                version Array(String),
                version_string String,
                cookie UInt8,
                charset LowCardinality(String),
                color_depth UInt8),
            `os` Tuple(
                family LowCardinality(String),
                version Array(String),
                version_string String,
                language LowCardinality(String)
            ),
            `device` Tuple(
                family LowCardinality(String),
                brand LowCardinality(String),
                model LowCardinality(String)
            ),
            `device_is` Tuple(mobile Int8, tablet Int8, touch Int8, pc Int8, bot Int8),
            `device_extra` String DEFAULT '',
            `resolution` Tuple(browser String, viewport String, page String),
            `event` Tuple(
                action LowCardinality(String),
                category LowCardinality(String),
                label String,
                property String,
                value String,
                unstructured String
            ),
            `extra` String DEFAULT '',
            `tracker` Tuple(version LowCardinality(String), namespace LowCardinality(String))
        )
        ENGINE = {self.engine}
        PARTITION BY (toYYYYMM(time), event_type)
        ORDER BY (time, app_id, platform, event_type, device_id, cityHash64(device_id), session_id, view_id, page, event_id)
        SAMPLE BY cityHash64(device_id)
        SETTINGS index_granularity = 8192;
        """
        )

    async def create_buffer_table(self):
        await self.conn.execute(
            f"""
        CREATE TABLE IF NOT EXISTS {self.database}.buffer {self.cluster_condition}
        AS {self.database}.local ENGINE = Buffer(
            '{self.database}', 'local', 16, 10, 100, 10000, 1000000, 10000000, 100000000
        );
        """
        )

    async def create_distributed_table(self):
        await self.conn.execute(
            f"""
        CREATE TABLE IF NOT EXISTS {self.database}.clickstream {self.cluster_condition}
        AS {self.database}.local ENGINE = Distributed(
            '{self.cluster}', '{self.database}', 'buffer', cityHash64(device_id)
        );
        """
        )

    async def create_all(self):
        await self.create_db()
        await self.create_local_table()
        await self.create_buffer_table()

        table_to_insert = f"{self.database}.buffer"

        if self.params["cluster_name"]:
            await self.create_distributed_table()
            table_to_insert = f"{self.database}.clickstream"

        return table_to_insert
