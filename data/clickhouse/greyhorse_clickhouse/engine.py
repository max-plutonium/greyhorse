import asyncio
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import override

import asynch
from asynch.cursors import DictCursor
from asynch.pool import Pool

from greyhorse.app.context import AsyncContextBuilder, Context
from greyhorse.data.storage import DataStorageEngine
from greyhorse.i18n import tr
from greyhorse.logging import logger
from .config import EngineConf
from .contexts import ClickHouseContext

type AsyncChannel = asynch.connection.Cursor


class ClickHouseAsyncEngine(DataStorageEngine):
    def __init__(self, name: str, config: EngineConf):
        super().__init__(name)
        self._config = config
        self._counter = 0
        self._lock = asyncio.Lock()
        self._pool: Pool | None = None

    @property
    def active(self) -> bool:
        return self._counter > 0

    @override
    async def start(self):
        async with self._lock:
            if 0 == self._counter:
                assert not self._pool

                loop = asyncio.get_event_loop()
                self._pool = Pool(
                    dsn=str(self._config.dsn), echo=self._config.echo,
                    minsize=self._config.pool_min_size,
                    maxsize=self._config.pool_max_size,
                    loop=loop, cursor_cls=DictCursor,
                )
                logger.info(tr('greyhorse.engines.ch.engine.started').format(name=self.name))

            self._counter += 1

    @override
    async def stop(self):
        async with self._lock:
            if 1 == self._counter:
                assert self._pool

                self._pool.close()
                await self._pool.wait_closed()

                self._pool = None
                logger.info(tr('greyhorse.engines.ch.engine.stopped').format(name=self.name))

            self._counter = max(self._counter - 1, 0)

    @asynccontextmanager
    async def session(self) -> AbstractAsyncContextManager[AsyncChannel]:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                yield cursor

    @override
    def get_context[T: Context](self, kind: type[ClickHouseContext]) -> T | None:
        if kind is ClickHouseContext:
            builder = AsyncContextBuilder[ClickHouseContext](kind)
            builder.add_param('name', self.name)
            builder.add_param('connection', self.session)
            return builder.build()
        else:
            return None
