import asyncio
from abc import ABC, abstractmethod
from asyncio import Task
from typing import Any, Mapping

import aio_pika

from greyhorse.i18n import tr
from greyhorse.logging import logger
from greyhorse.utils.invoke import get_asyncio_loop


class AsyncRmqServer(ABC):
    def __init__(
        self, queue: aio_pika.abc.AbstractRobustQueue,
        exchange: aio_pika.RobustExchange, app_id: str | None = None,
    ):
        self._exchange = exchange
        self._queue = queue
        self._app_id = app_id
        self._task: Task | None = None

    @property
    def active(self) -> bool:
        return self._task is not None

    @abstractmethod
    async def __call__(self, body: bytes, info: Mapping[str, Any]) -> bytes | None:
        ...

    async def _run(self):
        async with self._queue.iterator() as queue_iter:
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

    async def start(self):
        if self._task is not None:
            return

        self._task = get_asyncio_loop().create_task(self._run())

    async def stop(self):
        if self._task is None:
            return

        self._task.cancel()

        try:
            await self._task
        except asyncio.CancelledError:
            pass

        self._task = None
