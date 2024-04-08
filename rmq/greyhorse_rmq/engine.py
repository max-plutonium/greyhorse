import asyncio
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import aio_pika
from aio_pika.pool import Pool

from greyhorse.engines.base import AsyncEngine
from greyhorse.i18n import tr
from greyhorse.logging import logger
from greyhorse_rmq.config import EngineConfig

AsyncChannel = aio_pika.RobustChannel


class RmqAsyncEngine(AsyncEngine[AsyncChannel]):
    def __init__(self, name: str, config: EngineConfig):
        super().__init__(name)
        self._config = config
        self._counter = 0
        self._lock = asyncio.Lock()
        self._conn_pool: Pool | None = None
        self._chan_pool: Pool | None = None

    @property
    def connection_class(self):
        return AsyncChannel

    @asynccontextmanager
    async def session(self, *args, **kwargs) -> AbstractAsyncContextManager[AsyncChannel]:
        async with self._chan_pool.acquire() as conn:
            yield conn

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
            self._config.dsn, virtualhost=self._config.virtualhost,
            timeout=self._config.timeout_seconds,
        )

    async def _get_channel(self) -> aio_pika.Channel:
        async with self._conn_pool.acquire() as connection:
            return await connection.channel()
