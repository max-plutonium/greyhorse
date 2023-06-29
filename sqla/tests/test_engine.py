import pytest
from sqlalchemy import text

from greyhorse_sqla.config import EngineConfig, SqlEngineType
from greyhorse_sqla.engine import SqlaAsyncEngine, SqlaSyncEngine
from greyhorse_sqla.factory import SqlaAsyncEngineFactory, SqlaSyncEngineFactory
from .conf import MYSQL_URI, POSTGRES_URI, SQLITE_URI


def test_sync_factory():
    config = EngineConfig(
        dsn=SQLITE_URI,
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    factory = SqlaSyncEngineFactory()

    assert [] == factory.get_engine_names()
    assert factory.get_engine('test') is None
    assert {} == factory.get_engines()
    assert [] == factory.get_engines_for_type(SqlEngineType.SQLITE)

    engine = factory('test', config, SqlEngineType.SQLITE)

    assert engine
    assert isinstance(engine, SqlaSyncEngine)
    assert ['test'] == factory.get_engine_names()
    assert factory.get_engine('test') is engine
    assert {'test': engine} == factory.get_engines()
    assert [engine] == factory.get_engines_for_type(SqlEngineType.SQLITE)


def test_async_factory():
    config = EngineConfig(
        dsn=SQLITE_URI,
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    factory = SqlaAsyncEngineFactory()

    assert [] == factory.get_engine_names()
    assert factory.get_engine('test') is None
    assert {} == factory.get_engines()
    assert [] == factory.get_engines_for_type(SqlEngineType.SQLITE)

    engine = factory('test', config, SqlEngineType.SQLITE)

    assert engine
    assert isinstance(engine, SqlaAsyncEngine)
    assert ['test'] == factory.get_engine_names()
    assert factory.get_engine('test') is engine
    assert {'test': engine} == factory.get_engines()
    assert [engine] == factory.get_engines_for_type(SqlEngineType.SQLITE)


def test_sync_sqlite_engine():
    config = EngineConfig(
        dsn=SQLITE_URI,
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    factory = SqlaSyncEngineFactory()
    engine = factory('test', config, SqlEngineType.SQLITE)

    engine.start()

    with engine.session() as conn:
        res = conn.execute(text('select sqlite_version();'))
        print(res.fetchone()[0])
        res = conn.execute(text('select 1 + 2;'))
        assert res.fetchone()[0] == 3

    engine.stop()


@pytest.mark.asyncio
async def test_async_sqlite_engine():
    config = EngineConfig(
        dsn=SQLITE_URI,
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    factory = SqlaAsyncEngineFactory()
    engine = factory('test', config, SqlEngineType.SQLITE)

    await engine.start()

    async with engine.session() as conn:
        res = await conn.execute(text('select sqlite_version();'))
        print(res.fetchone()[0])
        res = await conn.execute(text('select 1 + 2;'))
        assert res.fetchone()[0] == 3

    await engine.stop()


def test_sync_postgres_engine():
    config = EngineConfig(
        dsn=POSTGRES_URI,
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    factory = SqlaSyncEngineFactory()
    engine = factory('test', config, SqlEngineType.POSTGRES)

    engine.start()

    with engine.session() as conn:
        res = conn.execute(text('select version();'))
        print(res.fetchone()[0])
        res = conn.execute(text('select 1 + 2;'))
        assert res.fetchone()[0] == 3

    engine.stop()


@pytest.mark.asyncio
async def test_async_postgres_engine():
    config = EngineConfig(
        dsn=POSTGRES_URI,
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    factory = SqlaAsyncEngineFactory()
    engine = factory('test', config, SqlEngineType.POSTGRES)

    await engine.start()

    async with engine.session() as conn:
        res = await conn.execute(text('select version();'))
        print(res.fetchone()[0])
        res = await conn.execute(text('select 1 + 2;'))
        assert res.fetchone()[0] == 3

    await engine.stop()


def test_sync_mysql_engine():
    config = EngineConfig(
        dsn=MYSQL_URI,
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    factory = SqlaSyncEngineFactory()
    engine = factory('test', config, SqlEngineType.MYSQL)

    engine.start()

    with engine.session() as conn:
        res = conn.execute(text('select version();'))
        print(res.fetchone()[0])
        res = conn.execute(text('select 1 + 2;'))
        assert res.fetchone()[0] == 3

    engine.stop()


@pytest.mark.asyncio
async def test_async_mysql_engine():
    config = EngineConfig(
        dsn=MYSQL_URI,
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    factory = SqlaAsyncEngineFactory()
    engine = factory('test', config, SqlEngineType.MYSQL)

    await engine.start()

    async with engine.session() as conn:
        res = await conn.execute(text('select version();'))
        print(res.fetchone()[0])
        res = await conn.execute(text('select 1 + 2;'))
        assert res.fetchone()[0] == 3

    await engine.stop()
