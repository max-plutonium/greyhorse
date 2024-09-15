import pytest

from greyhorse.app.contexts import AsyncContext
from greyhorse_elasticsearch.config import EngineConf
from greyhorse_elasticsearch.contexts import ElasticSearchContextProvider
from greyhorse_elasticsearch.service import ElasticSearchService
from .conf import ES_URI


@pytest.mark.asyncio
async def test_service():
    config = EngineConf(dsn=ES_URI)
    configs = {'test': config}

    srv = ElasticSearchService('test', configs)
    res = srv.create()
    assert res.success

    await srv.start()

    factory = srv.provider_factories.get(ElasticSearchContextProvider)
    assert factory
    provider = factory()
    assert provider
    assert isinstance(provider, ElasticSearchContextProvider)

    ctx = provider.get()
    assert ctx
    assert isinstance(ctx, AsyncContext)

    async with ctx as conn:
        assert await conn.connection.ping()
        info = await conn.connection.info()
        print(info)

    await srv.stop()

    res = srv.destroy()
    assert res.success
