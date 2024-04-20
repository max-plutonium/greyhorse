import pytest

from greyhorse.app.context import AsyncContext
from greyhorse_clickhouse.config import EngineConf
from greyhorse_clickhouse.contexts import ClickHouseContext
from greyhorse_clickhouse.engine import ClickHouseAsyncEngine
from greyhorse_clickhouse.factory import CHAsyncEngineFactory
from .conf import CH_URI


def test_async_factory():
    config = EngineConf(dsn=CH_URI)

    factory = CHAsyncEngineFactory()

    assert [] == factory.get_engine_names()
    assert factory.get_engine('test') is None
    assert {} == factory.get_engines()

    engine = factory.create_engine('test', config)

    assert engine
    assert engine.name == 'test'
    assert isinstance(engine, ClickHouseAsyncEngine)
    assert ['test'] == factory.get_engine_names()
    assert factory.get_engine('test') is engine
    assert {'test': engine} == factory.get_engines()


@pytest.mark.asyncio
async def test_async_connection():
    config = EngineConf(dsn=CH_URI)

    factory = CHAsyncEngineFactory()
    engine = factory.create_engine('test', config)

    assert not engine.active
    await engine.start()
    assert engine.active

    ctx = engine.get_context(ClickHouseContext)
    assert ctx
    assert isinstance(ctx, AsyncContext)

    async with ctx as conn:
        assert await conn.connection.execute('select version() as v;')
        info = await conn.connection.fetchone()
        print(info['v'])
        await conn.connection.execute('select 1 + 2 as res;')
        assert (await conn.connection.fetchone())['res'] == 3

    assert engine.active
    await engine.stop()
    assert not engine.active
