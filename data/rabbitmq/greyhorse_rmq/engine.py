import asyncio
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import override

import aio_pika
from aio_pika.pool import Pool

from greyhorse.app.context import AsyncContextBuilder, Context
from greyhorse.data.storage import DataStorageEngine
from greyhorse.i18n import tr
from greyhorse.logging import logger
from .config import EngineConf
from .contexts import RmqAsyncContext

AsyncChannel = aio_pika.RobustChannel


class RmqAsyncEngine(DataStorageEngine):
    def __init__(self, name: str, config: EngineConf):
        super().__init__(name)
        self._config = config
        self._counter = 0
        self._lock = asyncio.Lock()
        self._conn_pool: Pool | None = None
        self._chan_pool: Pool | None = None

    @property
    def active(self) -> bool:
        return self._counter > 0

    @override
    async def start(self):
        async with self._lock:
            if 0 == self._counter:
                assert not self._conn_pool
                assert not self._chan_pool

                loop = asyncio.get_event_loop()
                self._conn_pool = Pool(
                    self._get_connection, loop=loop,
                    max_size=self._config.pool_max_connections,
                )
                self._chan_pool = Pool(
                    self._get_channel, loop=loop,
                    max_size=self._config.pool_max_channels_per_connection,
                )
                logger.info(tr('greyhorse.engines.rmq.engine.started').format(name=self.name))

            self._counter += 1

    @override
    async def stop(self):
        async with self._lock:
            if 1 == self._counter:
                assert self._conn_pool
                assert self._chan_pool

                await self._chan_pool.close()
                await self._conn_pool.close()

                self._conn_pool = self._chan_pool = None
                logger.info(tr('greyhorse.engines.rmq.engine.stopped').format(name=self.name))

            self._counter = max(self._counter - 1, 0)

    async def _get_connection(self) -> aio_pika.abc.AbstractRobustConnection:
        return await aio_pika.connect_robust(
            str(self._config.dsn), virtualhost=self._config.virtualhost,
            timeout=self._config.timeout_seconds,
        )

    async def _get_channel(self) -> aio_pika.Channel:
        async with self._conn_pool.acquire() as connection:
            return await connection.channel()

    @asynccontextmanager
    async def session(self) -> AbstractAsyncContextManager[AsyncChannel]:
        async with self._chan_pool.acquire() as conn:
            yield conn

    @override
    def get_context[T: Context](self, kind: type[RmqAsyncContext]) -> T | None:
        if kind is RmqAsyncContext:
            builder = AsyncContextBuilder[RmqAsyncContext](kind)
            builder.add_param('name', self.name)
            builder.add_param('connection', self.session)
            return builder.build()
        else:
            return None
