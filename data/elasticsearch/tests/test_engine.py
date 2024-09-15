import pytest

from greyhorse.app.contexts import AsyncContext
from greyhorse_elasticsearch.config import EngineConf
from greyhorse_elasticsearch.contexts import ElasticSearchContext
from greyhorse_elasticsearch.engine import ElasticSearchAsyncEngine
from greyhorse_elasticsearch.factory import ESAsyncEngineFactory
from .conf import ES_URI


def test_async_factory():
    config = EngineConf(dsn=ES_URI)

    factory = ESAsyncEngineFactory()

    assert [] == factory.get_engine_names()
    assert factory.get_engine('test') is None
    assert {} == factory.get_engines()

    engine = factory.create_engine('test', config)

    assert engine
    assert engine.name == 'test'
    assert isinstance(engine, ElasticSearchAsyncEngine)
    assert ['test'] == factory.get_engine_names()
    assert factory.get_engine('test') is engine
    assert {'test': engine} == factory.get_engines()


@pytest.mark.asyncio
async def test_async_connection():
    config = EngineConf(dsn=ES_URI)

    factory = ESAsyncEngineFactory()
    engine = factory.create_engine('test', config)

    assert not engine.active
    await engine.start()
    assert engine.active

    ctx = engine.get_context(ElasticSearchContext)
    assert ctx
    assert isinstance(ctx, AsyncContext)

    async with ctx as conn:
        assert await conn.connection.ping()
        info = await conn.connection.info()
        print(info)

    assert engine.active
    await engine.stop()
    assert not engine.active
