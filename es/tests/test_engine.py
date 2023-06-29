import pytest

from greyhorse_es.config import EngineConfig
from greyhorse_es.engine import ESAsyncEngine
from greyhorse_es.factory import ESAsyncEngineFactory
from .conf import ES_URI


def test_async_factory():
    config = EngineConfig(dsn=ES_URI)

    factory = ESAsyncEngineFactory()

    assert [] == factory.get_engine_names()
    assert factory.get_engine('test') is None
    assert {} == factory.get_engines()

    engine = factory('test', config)

    assert engine
    assert isinstance(engine, ESAsyncEngine)
    assert ['test'] == factory.get_engine_names()
    assert factory.get_engine('test') is engine
    assert {'test': engine} == factory.get_engines()


@pytest.mark.asyncio
async def test_async_connection():
    config = EngineConfig(dsn=ES_URI)

    factory = ESAsyncEngineFactory()
    engine = factory('test', config)

    await engine.start()

    async with engine.session() as conn:
        assert await conn.ping()
        info = await conn.info()
        print(info)

    await engine.stop()
