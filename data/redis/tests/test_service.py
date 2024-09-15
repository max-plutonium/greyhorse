import pytest

from greyhorse.app.contexts import AsyncContext, SyncContext
from greyhorse_redis.config import EngineConf
from greyhorse_redis.contexts import RedisAsyncContextProvider, RedisSyncContextProvider
from greyhorse_redis.service import AsyncRedisService, SyncRedisService
from .conf import REDIS_URI


def test_sync_service():
    config = EngineConf(dsn=REDIS_URI)
    configs = {'test': config}

    srv = SyncRedisService('test', configs)
    res = srv.create()
    assert res.success

    srv.start()

    factory = srv.provider_factories.get(RedisSyncContextProvider)
    assert factory
    provider = factory()
    assert provider
    assert isinstance(provider, RedisSyncContextProvider)

    ctx = provider.get()
    assert ctx
    assert isinstance(ctx, SyncContext)

    with ctx as conn:
        assert conn.connection.set('kkk', 'vvv') is True
        assert b'vvv' == conn.connection.get('kkk')
        assert conn.connection.delete('kkk')

    srv.stop()

    res = srv.destroy()
    assert res.success


@pytest.mark.asyncio
async def test_async_service():
    config = EngineConf(dsn=REDIS_URI)
    configs = {'test': config}

    srv = AsyncRedisService('test', configs)
    res = srv.create()
    assert res.success

    await srv.start()

    factory = srv.provider_factories.get(RedisAsyncContextProvider)
    assert factory
    provider = factory()
    assert provider
    assert isinstance(provider, RedisAsyncContextProvider)

    ctx = provider.get()
    assert ctx
    assert isinstance(ctx, AsyncContext)

    async with ctx as conn:
        assert await conn.connection.set('kkk', 'vvv') is True
        assert b'vvv' == await conn.connection.get('kkk')
        assert await conn.connection.delete('kkk')

    await srv.stop()

    res = srv.destroy()
    assert res.success
