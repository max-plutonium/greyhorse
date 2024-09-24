import pytest
from greyhorse.app.contexts import AsyncContext, SyncContext
from greyhorse.data.storage import (
    ConnectionProviderRegistry,
    ProviderRegistry,
    SessionProviderRegistry,
)
from greyhorse.maybe import Just
from greyhorse_sqla.config import EngineConf, SqlEngineType
from greyhorse_sqla.providers import SqlaAsyncConnProvider, SqlaSyncConnProvider
from greyhorse_sqla.services import AsyncSqlaService, SyncSqlaService
from sqlalchemy import text

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
def test_sync_service(param) -> None:
    config = EngineConf(
        dsn=param[0],
        type=param[1],
        pool_min_size=1,
        pool_max_size=2,
        pool_expire_seconds=15,
        pool_timeout_seconds=15,
    )

    configs = {'test': config}

    conn_registry = ConnectionProviderRegistry(ProviderRegistry())
    session_registry = SessionProviderRegistry(ProviderRegistry())

    srv = SyncSqlaService(configs)
    res = srv.setup(Just(conn_registry), Just(session_registry))
    assert res.is_ok()

    assert len(conn_registry) == 0
    assert len(session_registry) == 0

    srv.start()

    assert len(conn_registry) == 1
    assert len(session_registry) == 1

    provider = conn_registry.get(SqlaSyncConnProvider)
    assert provider.is_just()
    provider = provider.unwrap()
    assert isinstance(provider, SqlaSyncConnProvider)

    conn_ctx = provider.acquire()
    assert conn_ctx.is_ok()
    conn_ctx = conn_ctx.unwrap()
    assert isinstance(conn_ctx, SyncContext)

    with conn_ctx as conn:
        res = conn.execute(text('select 10 * 10;'))
        assert res.fetchone()[0] == 100

    assert len(conn_registry) == 1
    assert len(session_registry) == 1

    srv.stop()

    assert len(conn_registry) == 0
    assert len(session_registry) == 0

    res = srv.teardown()
    assert res.is_ok()

    assert len(conn_registry) == 0
    assert len(session_registry) == 0


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
async def test_async_service(param) -> None:
    config = EngineConf(
        dsn=param[0],
        type=param[1],
        pool_min_size=1,
        pool_max_size=2,
        pool_expire_seconds=15,
        pool_timeout_seconds=15,
    )

    configs = {'test': config}

    conn_registry = ConnectionProviderRegistry(ProviderRegistry())
    session_registry = SessionProviderRegistry(ProviderRegistry())

    srv = AsyncSqlaService(configs)
    res = await srv.setup(Just(conn_registry), Just(session_registry))
    assert res.is_ok()

    assert len(conn_registry) == 0
    assert len(session_registry) == 0

    await srv.start()

    assert len(conn_registry) == 1
    assert len(session_registry) == 1

    provider = conn_registry.get(SqlaAsyncConnProvider)
    assert provider.is_just()
    provider = provider.unwrap()
    assert isinstance(provider, SqlaAsyncConnProvider)

    conn_ctx = provider.acquire()
    assert conn_ctx.is_ok()
    conn_ctx = conn_ctx.unwrap()
    assert isinstance(conn_ctx, AsyncContext)

    async with conn_ctx as conn:
        res = await conn.execute(text('select 10 * 10;'))
        assert res.fetchone()[0] == 100

    assert len(conn_registry) == 1
    assert len(session_registry) == 1

    await srv.stop()

    assert len(conn_registry) == 0
    assert len(session_registry) == 0

    res = await srv.teardown()
    assert res.is_ok()

    assert len(conn_registry) == 0
    assert len(session_registry) == 0
