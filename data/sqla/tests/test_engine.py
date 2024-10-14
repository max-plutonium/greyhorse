import pytest
from greyhorse.app.contexts import AsyncContext, SyncContext
from greyhorse_sqla.config import EngineConf, SqlEngineType
from greyhorse_sqla.contexts import (
    SqlaAsyncConnCtx,
    SqlaAsyncSessionCtx,
    SqlaSyncConnCtx,
    SqlaSyncSessionCtx,
)
from greyhorse_sqla.engine_async import AsyncSqlaEngine
from greyhorse_sqla.engine_sync import SyncSqlaEngine
from greyhorse_sqla.factory import AsyncSqlaEngineFactory, SyncSqlaEngineFactory
from sqlalchemy import text

from .conf import MYSQL_URI, POSTGRES_URI, SQLITE_URI


def test_sync_factory() -> None:
    config = EngineConf(
        dsn=SQLITE_URI,
        type=SqlEngineType.SQLITE,
        pool_min_size=1,
        pool_max_size=2,
        pool_expire_seconds=15,
        pool_timeout_seconds=15,
    )

    factory = SyncSqlaEngineFactory()

    assert factory.get_engine_names() == []
    assert factory.get_engine('test').is_nothing()
    assert factory.get_engines() == {}

    engine = factory.create_engine('test', config)

    assert engine
    assert engine.name == 'test'
    assert isinstance(engine, SyncSqlaEngine)
    assert factory.get_engine_names() == ['test']
    assert factory.get_engine('test').unwrap() is engine
    assert factory.get_engines() == {'test': engine}


def test_async_factory() -> None:
    config = EngineConf(
        dsn=SQLITE_URI,
        type=SqlEngineType.SQLITE,
        pool_min_size=1,
        pool_max_size=2,
        pool_expire_seconds=15,
        pool_timeout_seconds=15,
    )

    factory = AsyncSqlaEngineFactory()

    assert factory.get_engine_names() == []
    assert factory.get_engine('test').is_nothing()
    assert factory.get_engines() == {}

    engine = factory.create_engine('test', config)

    assert engine
    assert engine.name == 'test'
    assert isinstance(engine, AsyncSqlaEngine)
    assert factory.get_engine_names() == ['test']
    assert factory.get_engine('test').unwrap() is engine
    assert factory.get_engines() == {'test': engine}


@pytest.mark.parametrize(
    'param',
    (
        (SQLITE_URI, SqlEngineType.SQLITE, 'sqlite_version'),
        (POSTGRES_URI, SqlEngineType.POSTGRES, 'version'),
        (MYSQL_URI, SqlEngineType.MYSQL, 'version'),
    ),
    ids=('SQLite', 'PostgreSQL', 'MySQL'),
)
def test_sync_connection(param) -> None:  # noqa: ANN001
    config = EngineConf(
        dsn=param[0],
        type=param[1],
        pool_min_size=1,
        pool_max_size=2,
        pool_expire_seconds=15,
        pool_timeout_seconds=15,
    )

    factory = SyncSqlaEngineFactory()
    engine = factory.create_engine('test', config)

    assert not engine.active
    engine.start()
    assert engine.active

    conn_ctx = engine.get_context(SqlaSyncConnCtx).unwrap()
    assert isinstance(conn_ctx, SyncContext)

    session_ctx = engine.get_context(SqlaSyncSessionCtx).unwrap()
    assert isinstance(session_ctx, SyncContext)

    with session_ctx as s1:
        res = s1.execute(text('select 1 * 2;'))
        assert res.fetchone()[0] == 2

    with conn_ctx as conn:
        res = conn.execute(text(f'select {param[2]}();'))
        print(res.fetchone()[0])

        with session_ctx as s1:
            res = s1.execute(text('select 1 + 2;'))
            assert res.fetchone()[0] == 3

        with session_ctx as s2:
            res = s2.execute(text('select 3 + 4;'))
            assert res.fetchone()[0] == 7

    assert engine.active
    engine.stop()
    assert not engine.active


@pytest.mark.parametrize(
    'param',
    (
        (SQLITE_URI, SqlEngineType.SQLITE, 'sqlite_version'),
        (POSTGRES_URI, SqlEngineType.POSTGRES, 'version'),
        (MYSQL_URI, SqlEngineType.MYSQL, 'version'),
    ),
    ids=('SQLite', 'PostgreSQL', 'MySQL'),
)
@pytest.mark.asyncio
async def test_async_connection(param) -> None:  # noqa: ANN001
    config = EngineConf(
        dsn=param[0],
        type=param[1],
        pool_min_size=1,
        pool_max_size=2,
        pool_expire_seconds=15,
        pool_timeout_seconds=15,
    )

    factory = AsyncSqlaEngineFactory()
    engine = factory.create_engine('test', config)

    assert not engine.active
    await engine.start()
    assert engine.active

    conn_ctx = engine.get_context(SqlaAsyncConnCtx).unwrap()
    assert isinstance(conn_ctx, AsyncContext)

    session_ctx = engine.get_context(SqlaAsyncSessionCtx).unwrap()
    assert isinstance(session_ctx, AsyncContext)

    async with session_ctx as s1:
        res = await s1.execute(text('select 1 * 2;'))
        assert res.fetchone()[0] == 2

    async with conn_ctx as conn:
        res = await conn.execute(text(f'select {param[2]}();'))
        print(res.fetchone()[0])

        async with session_ctx as s1:
            res = await s1.execute(text('select 1 + 2;'))
            assert res.fetchone()[0] == 3

        async with session_ctx as s2:
            res = await s2.execute(text('select 3 + 4;'))
            assert res.fetchone()[0] == 7

    assert engine.active
    await engine.stop()
    assert not engine.active
