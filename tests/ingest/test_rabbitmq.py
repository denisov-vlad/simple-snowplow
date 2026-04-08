import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "simple_snowplow"))

from core.config import RabbitMQConfig  # noqa: E402
from ingest.rabbitmq import QueuedInsertPayload, RabbitMQBatchWorker  # noqa: E402


class _FakeMessage:
    def __init__(self, payload: QueuedInsertPayload):
        self.body = payload.model_dump_json().encode("utf-8")
        self.acked = False
        self.nacked = False
        self.rejected = False

    async def ack(self):
        self.acked = True

    async def nack(self, requeue=True):
        self.nacked = requeue

    async def reject(self, requeue=False):
        self.rejected = not requeue


class _BatchSink:
    def __init__(self, fail=False):
        self.fail = fail
        self.batch_calls = []

    async def insert_batch(self, rows, table_group="snowplow"):
        if self.fail:
            raise RuntimeError("boom")
        self.batch_calls.append((table_group, rows))

    async def insert_rows(self, rows, table_group="snowplow"):
        raise AssertionError("worker should prefer insert_batch when available")


def _worker(sink, **overrides):
    config = RabbitMQConfig(
        batch_size=3,
        batch_timeout_ms=1000,
        retry_delay_ms=1,
        **overrides,
    )
    return RabbitMQBatchWorker(
        connection=object(),
        channel=object(),
        queue=object(),
        sink=sink,
        config=config,
    )


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], indirect=True)
async def test_worker_batches_messages_before_insert(anyio_backend):
    sink = _BatchSink()
    worker = _worker(sink)
    messages = [
        _FakeMessage(QueuedInsertPayload(rows=[{"id": 1}])),
        _FakeMessage(QueuedInsertPayload(rows=[{"id": 2}])),
        _FakeMessage(QueuedInsertPayload(rows=[{"id": 3}])),
    ]

    for message in messages:
        await worker.add_message(message)

    assert sink.batch_calls == [
        ("snowplow", [{"id": 1}, {"id": 2}, {"id": 3}]),
    ]
    assert all(message.acked for message in messages)
    assert not any(message.nacked for message in messages)


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], indirect=True)
async def test_worker_requeues_messages_when_batch_insert_fails(anyio_backend):
    sink = _BatchSink(fail=True)
    worker = _worker(sink, batch_size=10)
    messages = [
        _FakeMessage(QueuedInsertPayload(rows=[{"id": 1}])),
        _FakeMessage(QueuedInsertPayload(rows=[{"id": 2}])),
    ]

    for message in messages:
        await worker.add_message(message)

    await worker.flush_all()

    assert sink.batch_calls == []
    assert all(message.nacked for message in messages)
    assert not any(message.acked for message in messages)
