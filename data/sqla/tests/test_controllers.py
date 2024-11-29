import pytest
from greyhorse.app.abc.resources import Lifetime
from greyhorse.app.contexts import AsyncContext, SyncContext
from greyhorse.app.resources import make_container
from greyhorse_sqla.config import EngineConf, SqlEngineType
from greyhorse_sqla.contexts import SqlaAsyncConnCtx, SqlaSyncConnCtx
from greyhorse_sqla.controllers import AsyncSqlaController, SyncSqlaController
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

    container = make_container(lifetime=Lifetime.COMPONENT())
    svc = SyncSqlaService(configs)
    ctrl = SyncSqlaController('test')

    engine_selector = svc.create_engine_selector()
    ctrl.create_engine_operator().accept(engine_selector.borrow().unwrap())

    assert svc.setup().unwrap()
    assert ctrl.setup(container).unwrap()
    assert len(container.registry) > 0

    conn_ctx = container.get(SqlaSyncConnCtx)
    assert conn_ctx.is_just()
    conn_ctx = conn_ctx.unwrap()
    assert isinstance(conn_ctx, SyncContext)

    with conn_ctx as conn:
        res = conn.execute(text('select 10 * 10;'))
        assert res.fetchone()[0] == 100

    assert ctrl.teardown(container).unwrap()
    assert svc.teardown().unwrap()

    assert len(container.registry) == 0


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

    container = make_container(lifetime=Lifetime.COMPONENT())
    svc = AsyncSqlaService(configs)
    ctrl = AsyncSqlaController('test')

    engine_selector = svc.create_engine_selector()
    ctrl.create_engine_operator().accept(engine_selector.borrow().unwrap())

    assert (await svc.setup()).unwrap()
    assert (await ctrl.setup(container)).unwrap()
    assert len(container.registry) > 0

    conn_ctx = container.get(SqlaAsyncConnCtx)
    assert conn_ctx.is_just()
    conn_ctx = conn_ctx.unwrap()
    assert isinstance(conn_ctx, AsyncContext)

    async with conn_ctx as conn:
        res = await conn.execute(text('select 10 * 10;'))
        assert res.fetchone()[0] == 100

    assert (await ctrl.teardown(container)).unwrap()
    assert (await svc.teardown()).unwrap()

    assert len(container.registry) == 0
