from abc import ABC, abstractmethod
from typing import Any, Mapping

import aio_pika

from greyhorse_core.i18n import tr
from greyhorse_core.logging import logger


class AsyncRmqServer(ABC):
    def __init__(
        self, queue: aio_pika.abc.AbstractRobustQueue,
        exchange: aio_pika.RobustExchange, app_id: str | None = None,
    ):
        self._exchange = exchange
        self._queue = queue
        self._app_id = app_id
        self._iter: aio_pika.abc.AbstractQueueIterator | None = None

    @abstractmethod
    async def __call__(self, body: bytes, info: Mapping[str, Any]) -> bytes | None:
        ...

    async def run(self):
        async with self._queue.iterator() as queue_iter:
            self._iter = queue_iter
            message: aio_pika.abc.AbstractIncomingMessage

            async for message in queue_iter:
                try:
                    async with message.process():
                        if response := await self(message.body, message.info()):
                            await self._exchange.publish(
                                aio_pika.Message(
                                    body=response,
                                    correlation_id=message.correlation_id,
                                    delivery_mode=message.delivery_mode,
                                    app_id=self._app_id,
                                ),
                                routing_key=message.reply_to,
                            )
                except Exception as e:
                    logger.exception(tr('greyhorse.engines.rmq.rpc.exception').format(exc=e))

    async def stop(self):
        if self._iter:
            await self._iter.close()
