import asyncio
import threading
from contextlib import AbstractAsyncContextManager, AbstractContextManager, asynccontextmanager, contextmanager
from typing import override

import redis

from greyhorse.app.context import AsyncContextBuilder, Context, SyncContextBuilder
from greyhorse.data.storage import DataStorageEngine
from greyhorse.i18n import tr
from greyhorse.logging import logger
from .config import EngineConf
from .contexts import RedisAsyncContext, RedisSyncContext

type SyncChannel = redis.Redis
type AsyncChannel = redis.asyncio.Redis


class RedisSyncEngine(DataStorageEngine):
    def __init__(self, name: str, config: EngineConf):
        super().__init__(name)
        self._config = config
        self._counter = 0
        self._lock = threading.Lock()
        self._pool: redis.ConnectionPool | None = None

    @property
    def active(self) -> bool:
        return self._counter > 0

    @override
    def start(self):
        with self._lock:
            if 0 == self._counter:
                assert not self._pool

                self._pool = redis.ConnectionPool.from_url(
                    url=str(self._config.dsn),
                    socket_timeout=self._config.timeout_seconds,
                    socket_connect_timeout=self._config.connect_timeout_seconds,
                    max_connections=self._config.pool_max_connections,
                    client_name=self._config.client_name,
                )
                logger.info(tr('greyhorse.engines.redis.engine.started').format(name=self.name))

            self._counter += 1

    @override
    def stop(self):
        with self._lock:
            if 1 == self._counter:
                assert self._pool

                self._pool.close()

                self._pool = None
                logger.info(tr('greyhorse.engines.redis.engine.stopped').format(name=self.name))

            self._counter = max(self._counter - 1, 0)

    @contextmanager
    def session(self) -> AbstractContextManager[SyncChannel]:
        with redis.Redis.from_pool(self._pool) as client:
            yield client

    @override
    def get_context[T: Context](self, kind: type[RedisSyncContext]) -> T | None:
        if kind is RedisSyncContext:
            builder = SyncContextBuilder[RedisSyncContext](kind)
            builder.add_param('name', self.name)
            builder.add_param('connection', self.session)
            return builder.build()
        else:
            return None


class RedisAsyncEngine(DataStorageEngine):
    def __init__(self, name: str, config: EngineConf):
        super().__init__(name)
        self._config = config
        self._counter = 0
        self._lock = asyncio.Lock()
        self._pool: redis.asyncio.ConnectionPool | None = None

    @property
    def active(self) -> bool:
        return self._counter > 0

    @override
    async def start(self):
        async with self._lock:
            if 0 == self._counter:
                assert not self._pool

                self._pool = redis.asyncio.ConnectionPool.from_url(
                    url=str(self._config.dsn),
                    socket_timeout=self._config.timeout_seconds,
                    socket_connect_timeout=self._config.connect_timeout_seconds,
                    max_connections=self._config.pool_max_connections,
                    client_name=self._config.client_name,
                )
                logger.info(tr('greyhorse.engines.redis.engine.started').format(name=self.name))

            self._counter += 1

    @override
    async def stop(self):
        async with self._lock:
            if 1 == self._counter:
                assert self._pool

                await self._pool.aclose()

                self._pool = None
                logger.info(tr('greyhorse.engines.redis.engine.stopped').format(name=self.name))

            self._counter = max(self._counter - 1, 0)

    @asynccontextmanager
    async def session(self) -> AbstractAsyncContextManager[AsyncChannel]:
        async with redis.asyncio.Redis.from_pool(self._pool) as client:
            yield client

    @override
    def get_context[T: Context](self, kind: type[RedisAsyncContext]) -> T | None:
        if kind is RedisAsyncContext:
            builder = AsyncContextBuilder[RedisAsyncContext](kind)
            builder.add_param('name', self.name)
            builder.add_param('connection', self.session)
            return builder.build()
        else:
            return None
