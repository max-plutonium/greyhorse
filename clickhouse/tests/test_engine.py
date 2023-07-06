import pytest

from greyhorse_clickhouse.config import EngineConfig
from greyhorse_clickhouse.engine import CHAsyncEngine
from greyhorse_clickhouse.factory import CHAsyncEngineFactory
from .conf import CH_URI


def test_async_factory():
    config = EngineConfig(dsn=CH_URI)

    factory = CHAsyncEngineFactory()

    assert [] == factory.get_engine_names()
    assert factory.get_engine('test') is None
    assert {} == factory.get_engines()

    engine = factory('test', config)

    assert engine
    assert isinstance(engine, CHAsyncEngine)
    assert ['test'] == factory.get_engine_names()
    assert factory.get_engine('test') is engine
    assert {'test': engine} == factory.get_engines()


@pytest.mark.asyncio
async def test_async_connection():
    config = EngineConfig(dsn=CH_URI)

    factory = CHAsyncEngineFactory()
    engine = factory('test', config)

    await engine.start()

    async with engine.session() as conn:
        assert await conn.execute('select version() as v;')
        info = await conn.fetchone()
        print(info['v'])
        await conn.execute('select 1 + 2 as res;')
        assert (await conn.fetchone())['res'] == 3

    await engine.stop()
