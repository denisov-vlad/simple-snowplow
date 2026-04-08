"""RabbitMQ-backed ingest pipeline."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import structlog
from aio_pika import DeliveryMode, Message, connect_robust
from aio_pika.abc import (
    AbstractChannel,
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustConnection,
)
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from core.config import RabbitMQConfig
from core.protocols import RowSink

logger = structlog.get_logger(__name__)


def _resolve_table_name(
    tables: dict[str, Any],
    cluster_name: str | None,
    table_group: str,
) -> str:
    table_config = tables[table_group]
    if cluster_name:
        return table_config["distributed"]["name"]
    return table_config["local"]["name"]


class QueuedInsertPayload(BaseModel):
    """Serialized payload stored in RabbitMQ."""

    table_group: str = "snowplow"
    rows: list[dict[str, Any]] = Field(default_factory=list)


@dataclass(slots=True)
class PendingMessage:
    """Pending RabbitMQ message awaiting a batch flush."""

    message: AbstractIncomingMessage
    payload: QueuedInsertPayload


async def connect_rabbitmq(config: RabbitMQConfig) -> AbstractRobustConnection:
    """Create a robust RabbitMQ connection."""

    return await connect_robust(
        host=config.host,
        port=config.port,
        login=config.username,
        password=config.password,
        virtualhost=config.virtualhost,
    )


class RabbitMQPublisher:
    """Queues rows in RabbitMQ instead of writing directly to ClickHouse."""

    def __init__(
        self,
        connection: AbstractRobustConnection,
        channel: AbstractChannel,
        config: RabbitMQConfig,
        tables: dict[str, Any],
        database: str,
        cluster_name: str | None = None,
    ) -> None:
        self.connection = connection
        self.channel = channel
        self.config = config
        self.tables = tables
        self.database = database
        self.cluster_name = cluster_name

    @classmethod
    async def create(
        cls,
        config: RabbitMQConfig,
        tables: dict[str, Any],
        database: str,
        cluster_name: str | None = None,
    ) -> RabbitMQPublisher:
        """Create a publisher and ensure the queue exists."""

        connection = await connect_rabbitmq(config)
        channel = await connection.channel(publisher_confirms=True)
        await channel.declare_queue(config.queue_name, durable=True)
        return cls(connection, channel, config, tables, database, cluster_name)

    async def insert_rows(
        self,
        rows: list[dict[str, Any]],
        table_group: str = "snowplow",
    ) -> None:
        """Publish rows to RabbitMQ as a persistent message."""

        if not rows:
            logger.debug("No rows to enqueue", table_group=table_group)
            return

        payload = QueuedInsertPayload(
            table_group=table_group,
            rows=jsonable_encoder(rows),
        )
        message = Message(
            body=payload.model_dump_json().encode("utf-8"),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            type="simple_snowplow.insert",
        )

        await self.channel.default_exchange.publish(
            message,
            routing_key=self.config.queue_name,
            mandatory=True,
        )
        logger.debug(
            "Queued rows for ingestion",
            table_group=table_group,
            rows_count=len(rows),
            queue_name=self.config.queue_name,
        )

    async def get_table_name(self, table_group: str = "snowplow") -> str:
        """Return the eventual ClickHouse table name for the table group."""

        return _resolve_table_name(self.tables, self.cluster_name, table_group)

    async def close(self) -> None:
        """Close RabbitMQ resources."""

        await self.channel.close()
        await self.connection.close()


class RabbitMQHealthChecker:
    """Health checker for RabbitMQ-backed ingest."""

    def __init__(self, channel: AbstractChannel, queue_name: str) -> None:
        self.channel = channel
        self.queue_name = queue_name

    async def check(self) -> dict[str, bool]:
        """Check that the queue is reachable."""

        healthy = True
        try:
            await self.channel.declare_queue(
                self.queue_name,
                durable=True,
                passive=True,
            )
        except Exception as exc:
            logger.warning(
                "RabbitMQ health check failed",
                error=str(exc),
                queue_name=self.queue_name,
            )
            healthy = False

        return {"rabbitmq": healthy}


class RabbitMQBatchWorker:
    """Consumes RabbitMQ messages and writes batched rows to ClickHouse."""

    def __init__(
        self,
        connection: AbstractRobustConnection,
        channel: AbstractChannel,
        queue: AbstractQueue,
        sink: RowSink,
        config: RabbitMQConfig,
    ) -> None:
        self.connection = connection
        self.channel = channel
        self.queue = queue
        self.sink = sink
        self.config = config
        self.flush_interval = config.batch_timeout_ms / 1000
        self.retry_delay = config.retry_delay_ms / 1000
        self.pending_batches: dict[str, list[PendingMessage]] = defaultdict(list)
        self.pending_row_counts: dict[str, int] = defaultdict(int)

    @classmethod
    async def create(
        cls,
        sink: RowSink,
        config: RabbitMQConfig,
    ) -> RabbitMQBatchWorker:
        """Create a worker bound to the configured queue."""

        connection = await connect_rabbitmq(config)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=config.prefetch_count)
        queue = await channel.declare_queue(config.queue_name, durable=True)
        return cls(connection, channel, queue, sink, config)

    async def run(self) -> None:
        """Start consuming and flushing batches."""

        logger.info(
            "Starting RabbitMQ batch worker",
            queue_name=self.config.queue_name,
            batch_size=self.config.batch_size,
            batch_timeout_ms=self.config.batch_timeout_ms,
        )

        iterator = self.queue.iterator()
        try:
            async with iterator:
                while True:
                    try:
                        message = await asyncio.wait_for(
                            iterator.__anext__(),
                            timeout=self.flush_interval,
                        )
                    except asyncio.TimeoutError:
                        await self.flush_all()
                        continue
                    except StopAsyncIteration:
                        break

                    await self.add_message(message)
        finally:
            await self.flush_all()

    async def add_message(self, message: AbstractIncomingMessage) -> None:
        """Decode and buffer a message."""

        try:
            payload = QueuedInsertPayload.model_validate_json(message.body)
        except Exception as exc:
            logger.error("Dropping invalid queue payload", error=str(exc))
            await message.reject(requeue=False)
            return

        if not payload.rows:
            await message.ack()
            return

        self.pending_batches[payload.table_group].append(
            PendingMessage(message=message, payload=payload),
        )
        self.pending_row_counts[payload.table_group] += len(payload.rows)

        if self.pending_row_counts[payload.table_group] >= self.config.batch_size:
            await self.flush_table_group(payload.table_group)

    async def flush_all(self) -> None:
        """Flush all pending batches."""

        for table_group in list(self.pending_batches):
            await self.flush_table_group(table_group)

    async def flush_table_group(self, table_group: str) -> None:
        """Flush a single table group and ack or requeue source messages."""

        pending = self.pending_batches.pop(table_group, [])
        rows_count = self.pending_row_counts.pop(table_group, 0)
        if not pending:
            return

        rows = [row for item in pending for row in item.payload.rows]
        try:
            insert_batch = getattr(self.sink, "insert_batch", None)
            if callable(insert_batch):
                await insert_batch(rows, table_group=table_group)
            else:
                await self.sink.insert_rows(rows, table_group=table_group)
        except Exception as exc:
            logger.error(
                "Batch insert failed, requeueing messages",
                error=str(exc),
                table_group=table_group,
                rows_count=rows_count,
                messages_count=len(pending),
            )
            for item in pending:
                await item.message.nack(requeue=True)
            await asyncio.sleep(self.retry_delay)
            return

        for item in pending:
            await item.message.ack()

        logger.debug(
            "Flushed queued rows",
            table_group=table_group,
            rows_count=rows_count,
            messages_count=len(pending),
        )

    async def close(self) -> None:
        """Close RabbitMQ resources."""

        await self.channel.close()
        await self.connection.close()
