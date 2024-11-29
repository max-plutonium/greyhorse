from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from greyhorse.data.repositories import EntityError
from greyhorse.result import Err
from greyhorse_sqla.config import EngineConf, SqlEngineType
from greyhorse_sqla.contexts import SqlaAsyncConnCtx, SqlaAsyncSessionCtx
from greyhorse_sqla.engine_async import AsyncSqlaEngine
from greyhorse_sqla.factory import AsyncSqlaEngineFactory
from greyhorse_sqla.query import SqlaQuery as Q  # noqa: N814
from greyhorse_sqla.repositories import AsyncSqlaRepository
from sqlalchemy import DateTime, String, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.orm import mapped_column as C  # noqa: N812

from .conf import MYSQL_URI, POSTGRES_URI, SQLITE_URI


class Base(DeclarativeBase):
    pass


class TestModel(Base):
    __tablename__ = 'test_model_repo'

    id: Mapped[int] = C(primary_key=True)
    data: Mapped[str] = C(String(128))
    create_date: Mapped[datetime] = C(DateTime(timezone=False), server_default=func.now())


@pytest_asyncio.fixture(
    scope='module',
    loop_scope='module',
    params=(
        (SQLITE_URI, SqlEngineType.SQLITE),
        (POSTGRES_URI, SqlEngineType.POSTGRES),
        (MYSQL_URI, SqlEngineType.MYSQL),
    ),
    ids=('SQLite', 'Postgres', 'MySQL'),
)
async def sqla_engine(request) -> AsyncSqlaEngine:  # noqa: ANN001
    dsn, engine_type = request.param

    config = EngineConf(
        dsn=dsn,
        type=engine_type,
        echo=True,
        pool_min_size=1,
        pool_max_size=2,
        pool_expire_seconds=15,
        pool_timeout_seconds=15,
        force_rollback=True,
    )

    factory = AsyncSqlaEngineFactory()
    engine = factory.create_engine('test', config)
    await engine.start()

    conn_ctx = engine.get_context(SqlaAsyncConnCtx).unwrap()

    async with conn_ctx as conn:
        await conn.run_sync(Base.metadata.drop_all, tables=[TestModel.__table__])
        await conn.run_sync(Base.metadata.create_all, tables=[TestModel.__table__])
        await conn.commit()

    yield engine

    async with conn_ctx as conn:
        await conn.run_sync(Base.metadata.drop_all, tables=[TestModel.__table__])
        await conn.commit()

    await engine.stop()


@pytest_asyncio.fixture(scope='function', loop_scope='module')
async def session_ctx(sqla_engine: AsyncSqlaEngine) -> SqlaAsyncSessionCtx:
    session_ctx = sqla_engine.get_context(SqlaAsyncSessionCtx).unwrap()

    async with session_ctx:
        yield session_ctx


TestModelAsyncRepo = AsyncSqlaRepository[TestModel, int]


@pytest.mark.asyncio
async def test_create(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    instance = (await repo.create({'id': 1, 'data': '123'})).unwrap()
    assert instance.id > 0
    assert instance.data == '123'
    now = datetime.now(UTC).replace(microsecond=0, tzinfo=None)
    assert now - instance.create_date.replace(microsecond=0, tzinfo=None) < timedelta(seconds=2)


@pytest.mark.asyncio
async def test_get_or_create(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    res, created = await repo.get_or_create(999, dict(id=999, data='123'))
    assert created is True
    assert res.is_ok()

    obj1 = res.unwrap()
    assert obj1.id == 999
    assert obj1.data == '123'

    res, created = await repo.get_or_create(999, dict(id=999, data='123'))
    assert created is False
    assert res.is_ok()

    obj2 = res.unwrap()
    assert obj2.id == 999
    assert obj2.data == '123'


@pytest.mark.asyncio
async def test_update_by_id(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    obj1 = (await repo.create(dict(data='123'))).unwrap()

    assert await repo.update_by_id(obj1.id, dict(data='234'))
    assert Err(EntityError.Empty()) == await repo.update_by_id(-1, dict(data='234'))


@pytest.mark.asyncio
async def test_get(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    obj1 = (await repo.create(dict(data='123'))).unwrap()

    obj2 = (await repo.get(obj1.id)).unwrap()
    assert obj1.id == obj2.id
    assert obj1.data == obj2.data
    assert obj1 == obj2

    assert not await repo.get(-1)


@pytest.mark.asyncio
async def test_get_any(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    obj1 = (await repo.create(dict(data='1'))).unwrap()
    obj2 = (await repo.create(dict(data='2'))).unwrap()
    obj3 = (await repo.create(dict(data='3'))).unwrap()

    objects = list(await repo.get_any([]))
    assert len(objects) == 0

    objects = list(await repo.get_any([obj1.id, obj2.id, obj3.id]))
    assert len(objects) == 3
    assert objects[0].unwrap() == obj1
    assert objects[1].unwrap() == obj2
    assert objects[2].unwrap() == obj3

    objects = list(await repo.get_any([obj1.id, obj3.id]))
    assert len(objects) == 2
    assert objects[0].unwrap() == obj1
    assert objects[1].unwrap() == obj3

    objects = list(await repo.get_any([-1, obj1.id, 999999, obj3.id, 0]))
    assert len(objects) == 5
    assert objects[0].is_nothing()
    assert objects[1].unwrap() == obj1
    assert objects[2].is_nothing()
    assert objects[3].unwrap() == obj3
    assert objects[4].is_nothing()


@pytest.mark.asyncio
async def test_exists(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    obj1 = (await repo.create(dict(data='1'))).unwrap()
    await repo.create(dict(data='2'))
    await repo.create(dict(data='3'))

    res = await repo.exists(obj1.id)
    assert res is True

    res = await repo.exists(-1)
    assert res is False

    res = await repo.exists_by(Q([]))
    assert res is True

    res = await repo.exists_by(Q([TestModel.data == '-1']))
    assert res is False

    res = await repo.exists_by(Q([TestModel.data == '1']))
    assert res is True

    res = await repo.exists_by(Q([TestModel.data == '1', TestModel.data == '2']))
    assert res is False

    res = await repo.exists_by(Q([(TestModel.data == '1') | (TestModel.data == '2')]))
    assert res is True

    res = await repo.exists_by(Q([(TestModel.data == '1') & (TestModel.id == obj1.id)]))
    assert res is True

    res = await repo.exists_by(Q([text('data > :data')], data='1'))
    assert res is True

    res = await repo.exists_by(Q([text('data > :data')], data='3'))
    assert res is False


@pytest.mark.asyncio
async def test_load(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    instance = (await repo.create(dict(id=1, data='1'))).unwrap()

    assert not await repo.load(TestModel(id=1))

    assert instance.id == 1
    assert instance.data == '1'
    assert isinstance(instance.create_date, datetime)

    assert await repo.update_by_id(1, dict(data='2'))
    instance.data = '1'
    instance.create_date = None
    assert await repo.load(instance)

    assert instance.id == 1
    assert instance.data == '2'
    assert isinstance(instance.create_date, datetime)

    assert await repo.update_by_id(
        1, dict(data='3', create_date=datetime.now().replace(microsecond=0))
    )
    instance.data = '1'
    instance.create_date = None
    assert await repo.load(instance, only=['data'])

    assert instance.id == 1
    assert instance.data == '3'
    assert instance.create_date is None


@pytest.mark.asyncio
async def test_list(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    obj1 = (await repo.create(dict(data='1'))).unwrap()
    obj2 = (await repo.create(dict(data='2'))).unwrap()
    obj3 = (await repo.create(dict(data='3'))).unwrap()

    objects = [obj async for obj in repo.list()]
    assert len(objects) == 3
    assert objects[0] == obj1
    assert objects[1] == obj2
    assert objects[2] == obj3

    objects = [obj async for obj in repo.list(skip=1)]
    assert len(objects) == 2
    assert objects[0] == obj2
    assert objects[1] == obj3

    objects = [obj async for obj in repo.list(skip=2)]
    assert len(objects) == 1
    assert objects[0] == obj3

    objects = [obj async for obj in repo.list(skip=3)]
    assert len(objects) == 0

    objects = [obj async for obj in repo.list(limit=1)]
    assert len(objects) == 1
    assert objects[0] == obj1

    objects = [obj async for obj in repo.list(limit=2)]
    assert len(objects) == 2
    assert objects[0] == obj1
    assert objects[1] == obj2

    objects = [obj async for obj in repo.list(limit=3)]
    assert len(objects) == 3
    assert objects[0] == obj1
    assert objects[1] == obj2
    assert objects[2] == obj3

    objects = [obj async for obj in repo.list(skip=1, limit=3)]
    assert len(objects) == 2
    assert objects[0] == obj2
    assert objects[1] == obj3

    objects = [obj async for obj in repo.list(skip=2, limit=1)]
    assert len(objects) == 1
    assert objects[0] == obj3

    objects = [obj async for obj in repo.list(skip=3, limit=3)]
    assert len(objects) == 0

    objects = [obj async for obj in repo.list(skip=2, limit=0)]
    assert len(objects) == 1
    assert objects[0] == obj3


@pytest.mark.asyncio
async def test_list_filters(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    obj1 = (await repo.create(dict(data='1'))).unwrap()
    obj2 = (await repo.create(dict(data='2'))).unwrap()
    obj3 = (await repo.create(dict(data='3'))).unwrap()

    objects = [obj async for obj in repo.list()]
    assert len(objects) == 3
    assert objects[0] == obj1
    assert objects[1] == obj2
    assert objects[2] == obj3

    objects = [obj async for obj in repo.list()]
    assert len(objects) == 3
    assert objects[0] == obj1
    assert objects[1] == obj2
    assert objects[2] == obj3

    objects = [obj async for obj in repo.list(Q([TestModel.data == '-1']))]
    assert len(objects) == 0

    objects = [obj async for obj in repo.list(Q([TestModel.data == '1']))]
    assert len(objects) == 1
    assert objects[0] == obj1

    objects = [
        obj async for obj in repo.list(Q([TestModel.data == '1', TestModel.data == '2']))
    ]
    assert len(objects) == 0

    objects = [
        obj async for obj in repo.list(Q([(TestModel.data == '1') | (TestModel.data == '2')]))
    ]
    assert len(objects) == 2
    assert objects[0] == obj1
    assert objects[1] == obj2

    objects = [
        obj async for obj in repo.list(Q([(TestModel.data == '1') & (TestModel.id == obj1.id)]))
    ]
    assert len(objects) == 1
    assert objects[0] == obj1

    objects = [obj async for obj in repo.list(Q([text('data > :data')], data='1'))]
    assert len(objects) == 2
    assert objects[0] == obj2
    assert objects[1] == obj3


@pytest.mark.asyncio
async def test_count(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    obj1 = (await repo.create(dict(data='1'))).unwrap()
    await repo.create(dict(data='2'))
    await repo.create(dict(data='3'))

    res = await repo.count()
    assert res == 3

    res = await repo.count(Q([]))
    assert res == 3

    res = await repo.count(Q([TestModel.data == '-1']))
    assert res == 0

    res = await repo.count(Q([TestModel.data == '1']))
    assert res == 1

    res = await repo.count(Q([TestModel.data == '1', TestModel.data == '2']))
    assert res == 0

    res = await repo.count(Q([(TestModel.data == '1') | (TestModel.data == '2')]))
    assert res == 2

    res = await repo.count(Q([(TestModel.data == '1') & (TestModel.id == obj1.id)]))
    assert res == 1

    res = await repo.count(Q([text('data > :data')], data='1'))
    assert res == 2


@pytest.mark.asyncio
async def test_save(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    instance = TestModel(id=1, data='1')

    assert not await repo.get(1)

    assert await repo.save(instance)
    assert instance.id == 1
    assert instance.data == '1'
    assert isinstance(instance.create_date, datetime)

    instance2 = (await repo.get(instance.id)).unwrap()
    assert instance2.id == instance.id
    assert instance2.data == instance.data
    assert isinstance(instance2.create_date, datetime)
    assert instance2.create_date == instance.create_date


@pytest.mark.asyncio
async def test_save_all(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    obj1 = TestModel(data='1')
    obj2 = TestModel(data='2')
    obj3 = TestModel(data='3')

    assert await repo.save_all([obj1, obj2, obj3]) == 3

    objects = list(await repo.get_any([obj1.id, obj2.id, obj3.id]))
    assert len(objects) == 3
    assert objects[0].unwrap() == obj1
    assert objects[1].unwrap() == obj2
    assert objects[2].unwrap() == obj3
    assert objects[0].unwrap().id == obj1.id
    assert objects[0].unwrap().data == obj1.data
    assert objects[1].unwrap().id == obj2.id
    assert objects[1].unwrap().data == obj2.data
    assert objects[2].unwrap().id == obj3.id
    assert objects[2].unwrap().data == obj3.data

    obj1.data = '4'
    obj2.data = '5'
    obj3.data = '6'

    assert await repo.save_all([obj1, obj2, obj3])

    objects = list(await repo.get_any([obj1.id, obj2.id, obj3.id]))
    assert len(objects) == 3
    assert objects[0].unwrap() == obj1
    assert objects[1].unwrap() == obj2
    assert objects[2].unwrap() == obj3
    assert objects[0].unwrap().id == obj1.id
    assert objects[0].unwrap().data == obj1.data
    assert objects[1].unwrap().id == obj2.id
    assert objects[1].unwrap().data == obj2.data
    assert objects[2].unwrap().id == obj3.id
    assert objects[2].unwrap().data == obj3.data


@pytest.mark.asyncio
async def test_delete(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    obj = (await repo.create(dict(data='123'))).unwrap()

    obj2 = (await repo.get(obj.id)).unwrap()
    assert obj == obj2

    assert await repo.delete(obj)

    assert (await repo.get(obj.id)).is_nothing()
    assert not await repo.delete(obj)


@pytest.mark.asyncio
async def test_delete_all(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    obj1 = (await repo.create(dict(data='1'))).unwrap()
    obj2 = (await repo.create(dict(data='2'))).unwrap()
    obj3 = (await repo.create(dict(data='3'))).unwrap()

    assert await repo.delete_all([obj1.id, obj2.id]) == 2
    assert await repo.delete_all([obj1.id, obj2.id]) == 0

    assert not await repo.load(obj1)
    assert not await repo.load(obj2)
    assert await repo.load(obj3)

    assert await repo.delete_all() == 1
    assert not await repo.load(obj3)


@pytest.mark.asyncio
async def test_delete_by_id(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    obj = (await repo.create(dict(data='123'))).unwrap()

    obj2 = (await repo.get(obj.id)).unwrap()
    assert obj == obj2

    assert await repo.delete_by_id(obj.id)

    assert (await repo.get(obj.id)).is_nothing()
    assert not await repo.delete_by_id(obj.id)

    assert not await repo.delete_by_id(-1)


@pytest.mark.asyncio
async def test_update_by(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    obj1 = (await repo.create(dict(data='1'))).unwrap()
    obj2 = (await repo.create(dict(data='2'))).unwrap()
    obj3 = (await repo.create(dict(data='3'))).unwrap()

    assert await repo.update_by(Q([TestModel.data != '1']), dict(data='0')) == 2

    assert obj1.data == '1'
    assert obj2.data == '0'
    assert obj3.data == '0'


@pytest.mark.asyncio
async def test_delete_by(session_ctx: SqlaAsyncSessionCtx) -> None:
    repo = TestModelAsyncRepo(session_ctx)
    obj1 = (await repo.create(dict(data='1'))).unwrap()
    obj2 = (await repo.create(dict(data='2'))).unwrap()
    obj3 = (await repo.create(dict(data='3'))).unwrap()

    assert await repo.delete_by(Q([TestModel.data != '1'])) == 2
    assert await repo.delete_by(Q([TestModel.data != '1'])) == 0

    assert await repo.load(obj1)
    assert not await repo.load(obj2)
    assert not await repo.load(obj3)
