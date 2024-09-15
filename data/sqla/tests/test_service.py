import pytest
from sqlalchemy import text

from greyhorse.app.contexts import AsyncContext, SyncContext
from greyhorse_sqla.config import EngineConf, SqlEngineType
from greyhorse_sqla.contexts import SqlaAsyncConnProvider, SqlaSyncConnProvider
from greyhorse_sqla.service import AsyncSqlaService, SyncSqlaService
from .conf import MYSQL_URI, POSTGRES_URI, SQLITE_URI


@pytest.mark.parametrize(
    'param',
    (
        (SQLITE_URI, SqlEngineType.SQLITE),
        (POSTGRES_URI, SqlEngineType.POSTGRES),
        (MYSQL_URI, SqlEngineType.MYSQL),
    ),
    ids=('SQLite', 'PostgreSQL', 'MySQL'),
)
def test_sync_service(param):
    config = EngineConf(
        dsn=param[0], type=param[1],
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    configs = {'test': config}

    srv = SyncSqlaService('test', configs)
    res = srv.create()
    assert res.success

    srv.start()

    factory = srv.provider_factories.get(SqlaSyncConnProvider)
    assert factory
    provider = factory()
    assert provider
    assert isinstance(provider, SqlaSyncConnProvider)

    conn_ctx = provider.get()
    assert conn_ctx
    assert isinstance(conn_ctx, SyncContext)

    with conn_ctx as conn:
        res = conn.connection.execute(text('select 10 * 10;'))
        assert res.fetchone()[0] == 100

    srv.stop()

    res = srv.destroy()
    assert res.success


@pytest.mark.parametrize(
    'param',
    (
        (SQLITE_URI, SqlEngineType.SQLITE),
        (POSTGRES_URI, SqlEngineType.POSTGRES),
        (MYSQL_URI, SqlEngineType.MYSQL),
    ),
    ids=('SQLite', 'PostgreSQL', 'MySQL'),
)
@pytest.mark.asyncio
async def test_async_service(param):
    config = EngineConf(
        dsn=param[0], type=param[1],
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    configs = {'test': config}

    srv = AsyncSqlaService('test', configs)
    res = srv.create()
    assert res.success

    await srv.start()

    factory = srv.provider_factories.get(SqlaAsyncConnProvider)
    assert factory
    provider = factory()
    assert provider
    assert isinstance(provider, SqlaAsyncConnProvider)

    conn_ctx = provider.get()
    assert conn_ctx
    assert isinstance(conn_ctx, AsyncContext)

    async with conn_ctx as conn:
        res = await conn.connection.execute(text('select 10 * 10;'))
        assert res.fetchone()[0] == 100

    await srv.stop()

    res = srv.destroy()
    assert res.success
