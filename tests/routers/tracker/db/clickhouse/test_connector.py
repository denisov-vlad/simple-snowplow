import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "simple_snowplow"))

from routers.tracker.db.clickhouse.connector import ClickHouseConnector  # noqa: E402
from routers.tracker.db.clickhouse.schemas import register_fields  # noqa: E402
from routers.tracker.db.clickhouse.schemas.snowplow import ColumnDef, STRING  # noqa: E402


class _FakeClient:
    def __init__(self):
        self.calls = []

    async def insert(
        self,
        table_name,
        data,
        column_names,
        column_types,
        settings,
    ):
        self.calls.append(
            {
                "table_name": table_name,
                "data": data,
                "column_names": column_names,
                "column_types": column_types,
                "settings": settings,
            },
        )


def _tables():
    return {
        "test_events": {
            "local": {"name": "events_local"},
            "distributed": {"name": "events_distributed"},
        },
    }


register_fields(
    "test_events",
    [
        ColumnDef(payload_name="foo", name="foo", type=STRING),
        ColumnDef(payload_name="bar", name="bar", type=STRING),
    ],
)


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], indirect=True)
async def test_insert_rows_keeps_direct_mode_row_by_row(anyio_backend):
    client = _FakeClient()
    connector = ClickHouseConnector(
        client,
        database="snowplow",
        tables=_tables(),
    )

    await connector.insert_rows(
        [{"foo": "a", "bar": "1"}, {"foo": "b", "bar": "2"}],
        table_group="test_events",
    )

    assert len(client.calls) == 2
    assert client.calls[0]["data"] == [["a", "1"]]
    assert client.calls[1]["data"] == [["b", "2"]]


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], indirect=True)
async def test_insert_batch_sends_single_clickhouse_insert(anyio_backend):
    client = _FakeClient()
    connector = ClickHouseConnector(
        client,
        database="snowplow",
        tables=_tables(),
    )

    await connector.insert_batch(
        [{"foo": "a", "bar": "1"}, {"foo": "b", "bar": "2"}],
        table_group="test_events",
    )

    assert len(client.calls) == 1
    assert client.calls[0]["table_name"] == "snowplow.events_local"
    assert client.calls[0]["data"] == [["a", "1"], ["b", "2"]]
