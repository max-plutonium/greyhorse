import pytest

from greyhorse.app.context import AsyncContext
from greyhorse_rmq.config import EngineConf
from greyhorse_rmq.contexts import RmqAsyncContextProvider
from greyhorse_rmq.service import RmqAsyncService
from .conf import RMQ_URI


@pytest.mark.asyncio
async def test_service():
    config = EngineConf(dsn=RMQ_URI)
    configs = {'test': config}

    srv = RmqAsyncService('test', configs)
    res = srv.create()
    assert res.success

    await srv.start()

    factory = srv.provider_factories.get(RmqAsyncContextProvider)
    assert factory
    provider = factory()
    assert provider
    assert isinstance(provider, RmqAsyncContextProvider)

    ctx = provider.get()
    assert ctx
    assert isinstance(ctx, AsyncContext)

    async with ctx as conn:
        queue = await conn.connection.declare_queue('test', auto_delete=True)
        assert queue

    await srv.stop()

    res = srv.destroy()
    assert res.success
