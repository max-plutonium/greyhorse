from typing import Any

import pytest
from greyhorse.app.contexts import AsyncContext, SyncContext
from greyhorse.app.registries import MutNamedDictRegistry
from greyhorse_sqla.config import EngineConf, SqlEngineType
from greyhorse_sqla.contexts import SqlaAsyncConnCtx, SqlaSyncConnCtx
from greyhorse_sqla.controllers import AsyncSqlaController, SyncSqlaController
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
def test_sync_ctrl(param) -> None:  # noqa: ANN001
    config = EngineConf(
        dsn=param[0],
        type=param[1],
        pool_min_size=1,
        pool_max_size=2,
        pool_expire_seconds=15,
        pool_timeout_seconds=15,
    )

    configs = {'test': config}
    ctrl = SyncSqlaController(configs)

    registry = MutNamedDictRegistry[type, Any]()
    assert ctrl.setup(registry).unwrap()
    assert len(registry) > 0

    conn_ctx = registry.get(SqlaSyncConnCtx)
    assert conn_ctx.is_just()
    conn_ctx = conn_ctx.unwrap()
    assert isinstance(conn_ctx, SyncContext)

    with conn_ctx as conn:
        res = conn.execute(text('select 10 * 10;'))
        assert res.fetchone()[0] == 100

    assert ctrl.teardown(registry).unwrap()

    assert len(registry) == 0


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
async def test_async_ctrl(param) -> None:  # noqa: ANN001
    config = EngineConf(
        dsn=param[0],
        type=param[1],
        pool_min_size=1,
        pool_max_size=2,
        pool_expire_seconds=15,
        pool_timeout_seconds=15,
    )

    configs = {'test': config}
    ctrl = AsyncSqlaController(configs)

    registry = MutNamedDictRegistry[type, Any]()
    assert (await ctrl.setup(registry)).unwrap()
    assert len(registry) > 0

    conn_ctx = registry.get(SqlaAsyncConnCtx)
    assert conn_ctx.is_just()
    conn_ctx = conn_ctx.unwrap()
    assert isinstance(conn_ctx, AsyncContext)

    async with conn_ctx as conn:
        res = await conn.execute(text('select 10 * 10;'))
        assert res.fetchone()[0] == 100

    assert (await ctrl.teardown(registry)).unwrap()

    assert len(registry) == 0
