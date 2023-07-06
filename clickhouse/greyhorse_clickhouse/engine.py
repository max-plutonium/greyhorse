import asyncio
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import asynch
from asynch.cursors import DictCursor
from asynch.pool import Pool

from greyhorse_clickhouse.config import EngineConfig
from greyhorse_core.engines.base import AsyncEngine
from greyhorse_core.i18n import tr
from greyhorse_core.logging import logger

AsyncChannel = asynch.connection.Cursor


class CHAsyncEngine(AsyncEngine[AsyncChannel]):
    def __init__(self, name: str, config: EngineConfig):
        super().__init__(name)
        self._config = config
        self._counter = 0
        self._lock = asyncio.Lock()
        self._pool: Pool | None = None

    @property
    def connection_class(self):
        return AsyncChannel

    @asynccontextmanager
    async def session(self, *args, **kwargs) -> AbstractAsyncContextManager[AsyncChannel]:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                yield cursor

    async def start(self):
        async with self._lock:
            if 0 == self._counter:
                assert not self._pool

                loop = asyncio.get_event_loop()
                self._pool = Pool(
                    dsn=self._config.dsn, echo=self._config.echo,
                    minsize=self._config.pool_min_size,
                    maxsize=self._config.pool_max_size,
                    loop=loop, cursor_cls=DictCursor,
                )
                logger.info(tr('greyhorse.engines.ch.engine.started').format(name=self.name))

            self._counter += 1

    async def stop(self):
        async with self._lock:
            if 1 == self._counter:
                assert self._pool

                self._pool.close()
                await self._pool.wait_closed()

                self._pool = None
                logger.info(tr('greyhorse.engines.ch.engine.stopped').format(name=self.name))

            self._counter = max(self._counter - 1, 0)
