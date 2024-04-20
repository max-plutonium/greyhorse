import pytest

from greyhorse.app.context import AsyncContext
from greyhorse_clickhouse.config import EngineConf
from greyhorse_clickhouse.contexts import ClickHouseContextProvider
from greyhorse_clickhouse.service import ClickHouseService
from .conf import CH_URI


@pytest.mark.asyncio
async def test_service():
    config = EngineConf(dsn=CH_URI)
    configs = {'test': config}

    srv = ClickHouseService('test', configs)
    res = srv.create()
    assert res.success

    await srv.start()

    factory = srv.provider_factories.get(ClickHouseContextProvider)
    assert factory
    provider = factory()
    assert provider
    assert isinstance(provider, ClickHouseContextProvider)

    ctx = provider.get()
    assert ctx
    assert isinstance(ctx, AsyncContext)

    async with ctx as conn:
        assert await conn.connection.execute('select 1 + 2 as res;')
        assert (await conn.connection.fetchone())['res'] == 3

    await srv.stop()

    res = srv.destroy()
    assert res.success
