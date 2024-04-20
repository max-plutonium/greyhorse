from dataclasses import dataclass

import redis

from greyhorse.app.entities.providers import AsyncContextProvider, SyncContextProvider


@dataclass(slots=True, frozen=True)
class RedisSyncContext:
    name: str
    connection: redis.Redis


@dataclass(slots=True, frozen=True)
class RedisAsyncContext:
    name: str
    connection: redis.asyncio.Redis


class RedisSyncContextProvider(SyncContextProvider[RedisSyncContext]):
    pass


class RedisAsyncContextProvider(AsyncContextProvider[RedisAsyncContext]):
    pass
