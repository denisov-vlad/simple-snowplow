"""RabbitMQ-backed ingest pipeline."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypeVar

import structlog
from aio_pika import DeliveryMode, Message, connect_robust
from aio_pika.abc import (
    AbstractChannel,
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustConnection,
)
from aio_pika.exceptions import AuthenticationError, ProbableAuthenticationError
from clickhouse_connect.driver.exceptions import DataError
from core.config import RabbitMQConfig
from core.protocols import RowSink
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)
T = TypeVar("T")


async def _declare_ingest_queues(
    channel: AbstractChannel,
    config: RabbitMQConfig,
) -> None:
    """Ensure the main and failed queues both exist."""

    await channel.declare_queue(config.queue_name, durable=True)
    await channel.declare_queue(config.resolved_failed_queue_name, durable=True)


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
    """Create a single robust RabbitMQ connection attempt."""

    return await connect_robust(
        host=config.host,
        port=config.port,
        login=config.username,
        password=config.password,
        virtualhost=config.virtualhost,
        timeout=config.connect_timeout_seconds,
    )


async def retry_rabbitmq_startup(
    config: RabbitMQConfig,
    operation: str,
    callback: Callable[[], Awaitable[T]],
) -> T:
    """Retry RabbitMQ startup operations until the configured wait expires."""

    loop = asyncio.get_running_loop()
    deadline = loop.time() + config.startup_timeout_seconds
    attempt = 0

    while True:
        attempt += 1
        try:
            return await callback()
        except AuthenticationError, ProbableAuthenticationError:
            raise
        except Exception as exc:
            remaining_seconds = deadline - loop.time()
            if remaining_seconds <= 0:
                logger.error(
                    "RabbitMQ startup wait expired",
                    operation=operation,
                    attempt=attempt,
                    host=config.host,
                    port=config.port,
                    startup_timeout_seconds=config.startup_timeout_seconds,
                    error=str(exc),
                )
                raise

            retry_in_seconds = min(
                config.startup_retry_interval_ms / 1000,
                remaining_seconds,
            )
            logger.warning(
                "RabbitMQ is not ready yet, retrying",
                operation=operation,
                attempt=attempt,
                host=config.host,
                port=config.port,
                retry_in_seconds=retry_in_seconds,
                remaining_seconds=remaining_seconds,
                error=str(exc),
            )
            await asyncio.sleep(retry_in_seconds)


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

        async def _create() -> RabbitMQPublisher:
            connection = await connect_rabbitmq(config)
            try:
                channel = await connection.channel(publisher_confirms=True)
                await _declare_ingest_queues(channel, config)
            except Exception:
                await connection.close()
                raise

            return cls(connection, channel, config, tables, database, cluster_name)

        return await retry_rabbitmq_startup(config, "publisher_create", _create)

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

    def __init__(self, channel: AbstractChannel, *queue_names: str) -> None:
        self.channel = channel
        self.queue_names = queue_names

    async def check(self) -> dict[str, bool]:
        """Check that the queue is reachable."""

        healthy = True
        try:
            for queue_name in self.queue_names:
                await self.channel.declare_queue(
                    queue_name,
                    durable=True,
                    passive=True,
                )
        except Exception as exc:
            logger.warning(
                "RabbitMQ health check failed",
                error=str(exc),
                queue_names=self.queue_names,
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
        self.failed_queue_name = config.resolved_failed_queue_name
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

        async def _create() -> RabbitMQBatchWorker:
            connection = await connect_rabbitmq(config)
            try:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=config.prefetch_count)
                await _declare_ingest_queues(channel, config)
                queue = await channel.declare_queue(config.queue_name, durable=True)
            except Exception:
                await connection.close()
                raise

            return cls(connection, channel, queue, sink, config)

        return await retry_rabbitmq_startup(config, "worker_create", _create)

    async def run(self) -> None:
        """Start consuming and flushing batches."""

        logger.info(
            "Starting RabbitMQ batch worker",
            queue_name=self.config.queue_name,
            batch_size=self.config.batch_size,
            batch_timeout_ms=self.config.batch_timeout_ms,
        )

        iterator = self.queue.iterator()
        next_message_task: asyncio.Task[AbstractIncomingMessage] | None = None
        try:
            async with iterator:
                while True:
                    if next_message_task is None:
                        next_message_task = asyncio.create_task(iterator.__anext__())
                    try:
                        message = await asyncio.wait_for(
                            asyncio.shield(next_message_task),
                            timeout=self.flush_interval,
                        )
                    except asyncio.TimeoutError:
                        await self.flush_all()
                        continue
                    except StopAsyncIteration:
                        break

                    next_message_task = None
                    await self.add_message(message)
        finally:
            if next_message_task is not None and not next_message_task.done():
                next_message_task.cancel()
                with suppress(asyncio.CancelledError):
                    await next_message_task
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

    async def _insert_rows(
        self,
        rows: list[dict[str, Any]],
        table_group: str,
    ) -> None:
        insert_batch = getattr(self.sink, "insert_batch", None)
        if callable(insert_batch):
            await insert_batch(rows, table_group=table_group)
            return
        await self.sink.insert_rows(rows, table_group=table_group)

    async def _publish_failed_message(
        self,
        item: PendingMessage,
        table_group: str,
        error: Exception,
    ) -> None:
        """Move an isolated invalid message out of the main ingest queue."""

        headers = dict(getattr(item.message, "headers", {}) or {})
        headers["x-simple-snowplow-source-queue"] = self.config.queue_name
        headers["x-simple-snowplow-error"] = str(error)
        headers["x-simple-snowplow-table-group"] = table_group

        await self.channel.default_exchange.publish(
            Message(
                body=item.message.body,
                headers=headers,
                content_type=getattr(item.message, "content_type", None)
                or "application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
                type=getattr(item.message, "type", None)
                or "simple_snowplow.insert.failed",
            ),
            routing_key=self.failed_queue_name,
            mandatory=True,
        )

    async def _flush_pending_messages(
        self,
        table_group: str,
        pending: list[PendingMessage],
    ) -> None:
        if not pending:
            return

        rows = [row for item in pending for row in item.payload.rows]
        rows_count = len(rows)
        try:
            await self._insert_rows(rows, table_group)
        except DataError as exc:
            if len(pending) == 1:
                logger.warning(
                    "Isolated queue message failed ClickHouse validation, "
                    "moving to failed queue",
                    error=str(exc),
                    table_group=table_group,
                    rows_count=rows_count,
                    messages_count=1,
                    failed_queue_name=self.failed_queue_name,
                )
                try:
                    await self._publish_failed_message(pending[0], table_group, exc)
                except Exception as publish_exc:
                    logger.error(
                        "Failed to move invalid queue message to failed queue,"
                        " requeueing",
                        error=str(publish_exc),
                        table_group=table_group,
                        rows_count=rows_count,
                        messages_count=1,
                        failed_queue_name=self.failed_queue_name,
                    )
                    await pending[0].message.nack(requeue=True)
                    await asyncio.sleep(self.retry_delay)
                    return
                await pending[0].message.ack()
                return

            midpoint = max(1, len(pending) // 2)
            logger.warning(
                "Batch insert failed with ClickHouse data error, splitting batch",
                error=str(exc),
                table_group=table_group,
                rows_count=rows_count,
                messages_count=len(pending),
            )
            await self._flush_pending_messages(table_group, pending[:midpoint])
            await self._flush_pending_messages(table_group, pending[midpoint:])
            return
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

    async def flush_table_group(self, table_group: str) -> None:
        """Flush a single table group and ack or requeue source messages."""

        pending = self.pending_batches.pop(table_group, [])
        self.pending_row_counts.pop(table_group, 0)
        if not pending:
            return
        await self._flush_pending_messages(table_group, pending)

    async def close(self) -> None:
        """Close RabbitMQ resources."""

        await self.channel.close()
        await self.connection.close()
