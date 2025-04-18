import asyncio
import json
import logging
from typing import Dict, Optional

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from notifications.app.exceptions import MissingRMQConnection
from notifications.app.tasks.dispatchers import MessageDispatcherProtocol
from notifications.core.settings import RabbitMQConfig
from notifications.gateways.message_queues.protocols.consumer_protocol import (
    NotificationConsumerProtocol,
)


log = logging.getLogger("app")


class RMQConsumerImpl(NotificationConsumerProtocol):
    def __init__(
        self,
        config: RabbitMQConfig,
        dispatchers: Dict[str, MessageDispatcherProtocol],
    ):
        self._config = config
        self._dispatchers = dispatchers
        self._rmq_url = config.url

        self._connection: Optional[AbstractRobustConnection] = None
        self._channel: Optional[aio_pika.Channel] = None
        self._queues: Dict[str, aio_pika.Queue] = {}
        self._queue_arguments: Dict[str, str] = {
            "x-dead-letter-exchange": "dlx",
            "x-dead-letter-routing-key": "dlq",
        }

        self._shutdown_event = asyncio.Event()

        self._processing_tasks = []

    async def startup(self) -> None:
        """Initialize RMQ connection and channel."""
        try:
            self._connection = await aio_pika.connect_robust(url=self._rmq_url)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(self._config.PREFETCH_COUNT)

            for queue_name in self._dispatchers.keys():
                self._queues[queue_name] = await self._channel.declare_queue(
                    name=queue_name,
                    durable=True,
                    arguments=self._queue_arguments,
                )

            log.info("Successfully connected to RabbitMQ")
        except aio_pika.exceptions.AMQPConnectionError as e:
            log.error("Failed to connect to RabbitMQ.", exc_info=True)
            raise MissingRMQConnection() from e

    async def consume_notifications(self) -> None:
        """Process messages from all queues."""
        tasks = []
        for queue_name, queue in self._queues.items():
            tasks.append(self._consume_queue(queue_name, queue))
        await asyncio.gather(*tasks)

    async def _consume_queue(
        self,
        queue_name: str,
        queue: aio_pika.Queue,
    ) -> None:
        """
        Process messages from a specific queue.

        If _shutdown_event is set, the loop is interrupted and no new messages are fetched.
        """
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                if self._shutdown_event.is_set():
                    log.info(
                        "Graceful shutdown requested. Stop consuming new messages from %s",
                        queue_name,
                    )
                    break

                task = asyncio.create_task(
                    self._process_message_wrapper(queue_name, message)
                )
                self._processing_tasks.append(task)
                task.add_done_callback(
                    lambda t: self._processing_tasks.remove(t)
                )

    async def _process_message_wrapper(
        self, queue_name: str, message: aio_pika.IncomingMessage
    ) -> None:
        """Wrap the message processing so that we can correctly wait for completion."""
        try:
            async with message.process():
                await self._process_message(queue_name, message)
        except aio_pika.exceptions.DeliveryError:
            log.error("Error processing message", exc_info=True)
        except Exception as e:
            log.error("Message processing failed: %s", e, exc_info=True)
            raise

    async def _process_message(
        self,
        queue_name: str,
        message: aio_pika.IncomingMessage,
    ) -> None:
        """Process single message from specific queue."""
        try:
            body = message.body.decode("utf-8")
            data: dict = json.loads(body)
            dispatcher = self._dispatchers.get(queue_name)
            if dispatcher:
                await dispatcher.dispatch(data)
            else:
                log.error(f"No dispatcher found for queue: {queue_name}")
        except json.JSONDecodeError:
            log.error("Invalid JSON in message", exc_info=True)
        except Exception:
            log.error("Message processing failed", exc_info=True)
            raise

    async def shutdown(self) -> None:
        """
        Initiate graceful shutdown:
            - Fix that you no longer need to retrieve new messages.
            - Wait for the tasks that are already running to finish.
            - Close the channel and the connection.
        """
        log.info("Initiating graceful shutdown for RabbitMQ consumer.")
        self._shutdown_event.set()
        if self._processing_tasks:
            log.info(
                "Waiting for %d message processing tasks to finish...",
                len(self._processing_tasks),
            )
            await asyncio.gather(
                *self._processing_tasks, return_exceptions=True
            )

        try:
            if self._channel and not self._channel.is_closed:
                await self._channel.close()
                self._channel = None
                log.debug("RabbitMQ channel closed.")

            if self._connection and not self._connection.is_closed:
                await self._connection.close()
                self._connection = None
                log.debug("RabbitMQ connection closed.")

            self._queues.clear()

            log.info("RabbitMQ consumer shutdown completed.")
        except Exception:
            log.error("Error during shutdown.", exc_info=True)
            raise
