import pytest
from sqlalchemy import text

from greyhorse.app.context import AsyncContext, SyncContext
from greyhorse_sqla.config import EngineConf, SqlEngineType
from greyhorse_sqla.contexts import SqlaAsyncContext, SqlaAsyncSessionContext, SqlaSyncContext, SqlaSyncSessionContext
from greyhorse_sqla.engine import SqlaAsyncEngine, SqlaSyncEngine
from greyhorse_sqla.factory import SqlaAsyncEngineFactory, SqlaSyncEngineFactory
from .conf import MYSQL_URI, POSTGRES_URI, SQLITE_URI


def test_sync_factory():
    config = EngineConf(
        dsn=SQLITE_URI, type=SqlEngineType.SQLITE,
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    factory = SqlaSyncEngineFactory()

    assert [] == factory.get_engine_names()
    assert factory.get_engine('test') is None
    assert {} == factory.get_engines()

    engine = factory.create_engine('test', config)

    assert engine
    assert engine.name == 'test'
    assert isinstance(engine, SqlaSyncEngine)
    assert ['test'] == factory.get_engine_names()
    assert factory.get_engine('test') is engine
    assert {'test': engine} == factory.get_engines()


def test_async_factory():
    config = EngineConf(
        dsn=SQLITE_URI, type=SqlEngineType.SQLITE,
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    factory = SqlaAsyncEngineFactory()

    assert [] == factory.get_engine_names()
    assert factory.get_engine('test') is None
    assert {} == factory.get_engines()

    engine = factory.create_engine('test', config)

    assert engine
    assert engine.name == 'test'
    assert isinstance(engine, SqlaAsyncEngine)
    assert ['test'] == factory.get_engine_names()
    assert factory.get_engine('test') is engine
    assert {'test': engine} == factory.get_engines()


@pytest.mark.parametrize(
    'param',
    (
        (SQLITE_URI, SqlEngineType.SQLITE, 'sqlite_version',),
        (POSTGRES_URI, SqlEngineType.POSTGRES, 'version',),
        (MYSQL_URI, SqlEngineType.MYSQL, 'version',),
    ),
    ids=('SQLite', 'PostgreSQL', 'MySQL'),
)
def test_sync_connection(param):
    config = EngineConf(
        dsn=param[0], type=param[1],
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    factory = SqlaSyncEngineFactory()
    engine = factory.create_engine('test', config)

    assert not engine.active
    engine.start()
    assert engine.active

    conn_ctx = engine.get_context(SqlaSyncContext)
    assert conn_ctx
    assert isinstance(conn_ctx, SyncContext)

    session_ctx = engine.get_context(SqlaSyncSessionContext)
    assert session_ctx
    assert isinstance(session_ctx, SyncContext)

    with conn_ctx as conn:
        res = conn.connection.execute(text(f'select {param[2]}();'))
        print(res.fetchone()[0])

        with session_ctx as s1:
            res = s1.session.execute(text('select 1 + 2;'))
            assert res.fetchone()[0] == 3
        with session_ctx as s2:
            res = s2.session.execute(text('select 3 + 4;'))
            assert res.fetchone()[0] == 7

    assert engine.active
    engine.stop()
    assert not engine.active


@pytest.mark.parametrize(
    'param',
    (
        (SQLITE_URI, SqlEngineType.SQLITE, 'sqlite_version',),
        (POSTGRES_URI, SqlEngineType.POSTGRES, 'version',),
        (MYSQL_URI, SqlEngineType.MYSQL, 'version',),
    ),
    ids=('SQLite', 'PostgreSQL', 'MySQL'),
)
@pytest.mark.asyncio
async def test_sqlite_async_connection(param):
    config = EngineConf(
        dsn=param[0], type=param[1],
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    factory = SqlaAsyncEngineFactory()
    engine = factory.create_engine('test', config)

    assert not engine.active
    await engine.start()
    assert engine.active

    conn_ctx = engine.get_context(SqlaAsyncContext)
    assert conn_ctx
    assert isinstance(conn_ctx, AsyncContext)

    session_ctx = engine.get_context(SqlaAsyncSessionContext)
    assert session_ctx
    assert isinstance(session_ctx, AsyncContext)

    async with conn_ctx as conn:
        res = await conn.connection.execute(text(f'select {param[2]}();'))
        print(res.fetchone()[0])

        async with session_ctx as s1:
            res = await s1.session.execute(text('select 1 + 2;'))
            assert res.fetchone()[0] == 3
        async with session_ctx as s2:
            res = await s2.session.execute(text('select 3 + 4;'))
            assert res.fetchone()[0] == 7

    assert engine.active
    await engine.stop()
    assert not engine.active
