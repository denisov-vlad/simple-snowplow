from datetime import datetime
from typing import List

import elasticapm
from orjson import dumps
from routers.tracker.db.clickhouse.convert import table_fields


async def convert_types(value):
    if isinstance(value, dict):
        # insert empty dict `{}` as empty string
        if not value:
            value = ""
        else:
            value = str(dumps(value), "utf-8")
    elif isinstance(value, datetime):
        # clickhouse driver doesn't support Datetime64 insert from datetime type
        value = value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    return value


@elasticapm.async_capture_span()
async def insert(conn, rows: List[dict]):

    for r in rows:

        columns_names = []

        row = []

        for field in table_fields:
            payload_name = field["payload_name"]
            if isinstance(payload_name, tuple):
                value = tuple([await convert_types(r.get(v)) for v in payload_name])
            else:
                value = await convert_types(r.get(payload_name))

            if value is None or value == "":
                continue

            columns_names.append(field["column_name"])
            row.append(value)

        columns_names = f"({','.join(columns_names)})"

        async with elasticapm.async_capture_span("clickhouse_query"):
            await conn.execute(
                f"INSERT INTO analytics.snowstream {columns_names} VALUES ", tuple(row)
            )
