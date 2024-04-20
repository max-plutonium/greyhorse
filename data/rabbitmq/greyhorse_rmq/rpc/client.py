import asyncio
import uuid
from typing import MutableMapping

import aio_pika

from greyhorse.i18n import tr
from greyhorse.logging import logger
from ..engine import AsyncChannel


class AsyncRmqClient:
    def __init__(
        self, channel: AsyncChannel, routing_key: str,
        exchange: aio_pika.RobustExchange | None = None,
        app_id: str | None = None, queue_name: str | None = None,
    ):
        self._channel = channel
        self._exchange = exchange or channel.default_exchange
        self._routing_key = routing_key
        self._app_id = app_id
        self._queue_name = queue_name
        self._queue: aio_pika.abc.AbstractRobustQueue | None = None
        self._consumer_tag: aio_pika.abc.ConsumerTag | None = None
        self._futures: MutableMapping[str, asyncio.Future] = dict()
        self._loop = asyncio.get_running_loop()

    async def connect(self):
        if not self._queue:
            self._queue = await self._channel.declare_queue(
                name=self._queue_name, exclusive=True, auto_delete=True,
            )
        if not self._consumer_tag:
            self._consumer_tag = await self._queue.consume(self._on_response)
        return self

    async def disconnect(self):
        if self._consumer_tag:
            await self._queue.cancel(self._consumer_tag)
            self._queue = self._consumer_tag = None

    def _on_response(self, message: aio_pika.IncomingMessage) -> None:
        if message.correlation_id is None:
            logger.error(tr('greyhorse.engines.rmq.rpc.bad-message').format(message=message))
            return

        logger.debug(tr('greyhorse.engines.rmq.rpc.received').format(info=message.info()))

        if future := self._futures.pop(message.correlation_id, None):
            future.set_result(message.body)
        else:
            logger.error(tr('greyhorse.engines.rmq.rpc.correlation-not-found').format(id=message.correlation_id))

    async def send(
        self, body: bytes, content_type: str | None = None,
        headers: aio_pika.abc.HeadersType | None = None,
        delivery_mode: aio_pika.abc.DeliveryMode | int | None = None,
        expiration: aio_pika.abc.DateType | None = None,
        type: str | None = None, user_id: str | None = None,
    ) -> bytes:
        correlation_id = str(uuid.uuid4())
        future = self._loop.create_future()
        self._futures[correlation_id] = future

        await self._exchange.publish(
            aio_pika.Message(
                body,
                content_type=content_type,
                correlation_id=correlation_id,
                reply_to=self._queue.name,
                headers=headers,
                delivery_mode=delivery_mode,
                expiration=expiration,
                type=type, user_id=user_id, app_id=self._app_id,
            ),
            routing_key=self._routing_key,
        )

        return bytes(await future)
