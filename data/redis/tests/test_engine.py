import pytest

from greyhorse.app.context import AsyncContext, SyncContext
from greyhorse_redis.config import EngineConf
from greyhorse_redis.contexts import RedisAsyncContext, RedisSyncContext
from greyhorse_redis.engine import RedisAsyncEngine, RedisSyncEngine
from greyhorse_redis.factory import RedisAsyncEngineFactory, RedisSyncEngineFactory
from .conf import REDIS_URI


def test_sync_factory():
    config = EngineConf(dsn=REDIS_URI)

    factory = RedisSyncEngineFactory()

    assert [] == factory.get_engine_names()
    assert factory.get_engine('test') is None
    assert {} == factory.get_engines()

    engine = factory.create_engine('test', config)

    assert engine
    assert engine.name == 'test'
    assert isinstance(engine, RedisSyncEngine)
    assert ['test'] == factory.get_engine_names()
    assert factory.get_engine('test') is engine
    assert {'test': engine} == factory.get_engines()


def test_sync_connection():
    config = EngineConf(dsn=REDIS_URI)

    factory = RedisSyncEngineFactory()
    engine = factory.create_engine('test', config)

    assert not engine.active
    engine.start()
    assert engine.active

    ctx = engine.get_context(RedisSyncContext)
    assert ctx
    assert isinstance(ctx, SyncContext)

    with ctx as conn:
        assert conn.connection.set('kkk', 'vvv') is True
        assert b'vvv' == conn.connection.get('kkk')
        assert conn.connection.delete('kkk')

    assert engine.active
    engine.stop()
    assert not engine.active


def test_async_factory():
    config = EngineConf(dsn=REDIS_URI)

    factory = RedisAsyncEngineFactory()

    assert [] == factory.get_engine_names()
    assert factory.get_engine('test') is None
    assert {} == factory.get_engines()

    engine = factory.create_engine('test', config)

    assert engine
    assert engine.name == 'test'
    assert isinstance(engine, RedisAsyncEngine)
    assert ['test'] == factory.get_engine_names()
    assert factory.get_engine('test') is engine
    assert {'test': engine} == factory.get_engines()


@pytest.mark.asyncio
async def test_async_connection():
    config = EngineConf(dsn=REDIS_URI)

    factory = RedisAsyncEngineFactory()
    engine = factory.create_engine('test', config)

    assert not engine.active
    await engine.start()
    assert engine.active

    ctx = engine.get_context(RedisAsyncContext)
    assert ctx
    assert isinstance(ctx, AsyncContext)

    async with ctx as conn:
        assert await conn.connection.set('kkk', 'vvv') is True
        assert b'vvv' == await conn.connection.get('kkk')
        assert await conn.connection.delete('kkk')

    assert engine.active
    await engine.stop()
    assert not engine.active
