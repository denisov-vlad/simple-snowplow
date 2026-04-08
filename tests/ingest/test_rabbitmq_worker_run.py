import asyncio
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

    async def ack(self):
        self.acked = True

    async def nack(self, requeue=True):
        raise AssertionError("nack should not be called")

    async def reject(self, requeue=False):
        raise AssertionError("reject should not be called")


class _Iterator:
    def __init__(self, message):
        self._message = message
        self._event = asyncio.Event()
        self.cancelled = False
        self._delivered = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def __anext__(self):
        try:
            await self._event.wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise

        if self._delivered:
            raise StopAsyncIteration

        self._delivered = True
        return self._message

    def release(self):
        self._event.set()


class _Queue:
    def __init__(self, iterator):
        self._iterator = iterator

    def iterator(self):
        return self._iterator


class _Sink:
    def __init__(self):
        self.calls = []

    async def insert_batch(self, rows, table_group="snowplow"):
        self.calls.append((table_group, rows))

    async def insert_rows(self, rows, table_group="snowplow"):
        raise AssertionError("worker should prefer insert_batch")


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], indirect=True)
async def test_run_does_not_cancel_queue_iterator_on_flush_timeout(anyio_backend):
    message = _FakeMessage(QueuedInsertPayload(rows=[{"id": 1}]))
    iterator = _Iterator(message)
    sink = _Sink()
    worker = RabbitMQBatchWorker(
        connection=object(),
        channel=object(),
        queue=_Queue(iterator),
        sink=sink,
        config=RabbitMQConfig(
            batch_size=10,
            batch_timeout_ms=10,
            retry_delay_ms=1,
        ),
    )

    task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.05)
    iterator.release()
    await task

    assert iterator.cancelled is False
    assert sink.calls == [("snowplow", [{"id": 1}])]
    assert message.acked is True
