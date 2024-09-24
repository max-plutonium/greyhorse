from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column as C

from greyhorse_sqla.config import EngineConfig, SqlEngineType
from greyhorse_sqla.factory import AsyncSqlaEngineFactory
from greyhorse_sqla.model import SqlaModel
from greyhorse_sqla.query import SqlaFiltersQuery as Q
from greyhorse_sqla.repository import SqlaModelRepository
from .conf import MYSQL_URI, POSTGRES_URI, SQLITE_URI


class TestModel(SqlaModel[int]):
    __tablename__ = 'test_model_repo'

    id: Mapped[int] = C(primary_key=True)
    data: Mapped[str] = C(String(128))
    create_date: Mapped[datetime] = C(
        DateTime(timezone=False), server_default=func.now()
    )

    __mapper_args__ = {'eager_defaults': True}


@pytest_asyncio.fixture(
    scope='module',
    params=(
        (SQLITE_URI, SqlEngineType.SQLITE),
        (POSTGRES_URI, SqlEngineType.POSTGRES),
        (MYSQL_URI, SqlEngineType.MYSQL),
    ),
    ids=(
        'SQLite',
        'Postgres',
        'MySQL',
    ),
)
async def sqla_engine(request):
    dsn, engine_type = request.param

    config = EngineConfig(
        dsn=dsn,
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    factory = AsyncSqlaEngineFactory()
    engine = factory('test-sqla', config, engine_type)
    await engine.start()

    async with engine.raw_engine.begin() as conn:
        await conn.run_sync(SqlaModel.metadata.drop_all, tables=[TestModel.__table__])
        await conn.run_sync(SqlaModel.metadata.create_all, tables=[TestModel.__table__])
        await conn.commit()

    yield engine

    async with engine.raw_engine.begin() as conn:
        await conn.run_sync(SqlaModel.metadata.drop_all, tables=[TestModel.__table__])
        await conn.commit()

    await engine.stop()


@pytest_asyncio.fixture(scope='function')
async def sqla_session(sqla_engine):
    async with sqla_engine.session(force_rollback=True) as session:

        @asynccontextmanager
        async def func():
            yield session

        yield func

    await sqla_engine.teardown_session()


@pytest.mark.asyncio
async def test_create(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    instance = await repo.create({'id': 1, 'data': '123'})
    assert instance.id > 0
    assert instance.data == '123'
    assert datetime.utcnow().replace(microsecond=0) - instance.create_date.replace(microsecond=0) \
           < timedelta(seconds=2)


@pytest.mark.asyncio
async def test_get_or_create(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    obj1, created = await repo.get_or_create(999, dict(id=999, data='123'))
    assert created is True
    assert obj1.id == 999
    assert obj1.data == '123'

    obj2, created = await repo.get_or_create(999, dict(id=999, data='123'))
    assert created is False
    assert obj2.id == 999
    assert obj2.data == '123'


@pytest.mark.asyncio
async def test_update_by_id(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    obj1 = await repo.create(dict(data='123'))

    assert await repo.update_by_id(obj1.id, dict(data='234'))
    assert not await repo.update_by_id(-1, dict(data='234'))


@pytest.mark.asyncio
async def test_update_by(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    obj1 = await repo.create(dict(data='1'))
    obj2 = await repo.create(dict(data='2'))
    obj3 = await repo.create(dict(data='3'))

    assert 2 == await repo.update_by(Q([TestModel.data != '1']), dict(data='0'))

    assert obj1.data == '1'
    assert obj2.data == '0'
    assert obj3.data == '0'


@pytest.mark.asyncio
async def test_get(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    obj1 = await repo.create(dict(data='123'))

    obj2 = await repo.get(obj1.id)
    assert obj1.id == obj2.id
    assert obj1.data == obj2.data
    assert obj1 == obj2

    assert not await repo.get(-1)


@pytest.mark.asyncio
async def test_get_any(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    obj1 = await repo.create(dict(data='1'))
    obj2 = await repo.create(dict(data='2'))
    obj3 = await repo.create(dict(data='3'))

    objects = await repo.get_any([])
    assert len(objects) == 0

    objects = await repo.get_any([obj1.id, obj2.id, obj3.id])
    assert len(objects) == 3
    assert objects[0] == obj1
    assert objects[1] == obj2
    assert objects[2] == obj3

    objects = await repo.get_any([obj1.id, obj3.id])
    assert len(objects) == 2
    assert objects[0] == obj1
    assert objects[1] == obj3

    objects = await repo.get_any([-1, obj1.id, 999999, obj3.id, 0])
    assert len(objects) == 5
    assert objects[0] is None
    assert objects[1] == obj1
    assert objects[2] is None
    assert objects[3] == obj3
    assert objects[4] is None


@pytest.mark.asyncio
async def test_list(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    obj1 = await repo.create(dict(data='1'))
    obj2 = await repo.create(dict(data='2'))
    obj3 = await repo.create(dict(data='3'))

    objects = await repo.list()
    assert len(objects) == 3
    assert objects[0] == obj1
    assert objects[1] == obj2
    assert objects[2] == obj3

    objects = await repo.list(skip=1)
    assert len(objects) == 2
    assert objects[0] == obj2
    assert objects[1] == obj3

    objects = await repo.list(skip=2)
    assert len(objects) == 1
    assert objects[0] == obj3

    objects = await repo.list(skip=3)
    assert len(objects) == 0

    objects = await repo.list(limit=1)
    assert len(objects) == 1
    assert objects[0] == obj1

    objects = await repo.list(limit=2)
    assert len(objects) == 2
    assert objects[0] == obj1
    assert objects[1] == obj2

    objects = await repo.list(limit=3)
    assert len(objects) == 3
    assert objects[0] == obj1
    assert objects[1] == obj2
    assert objects[2] == obj3

    objects = await repo.list(skip=1, limit=3)
    assert len(objects) == 2
    assert objects[0] == obj2
    assert objects[1] == obj3

    objects = await repo.list(skip=2, limit=1)
    assert len(objects) == 1
    assert objects[0] == obj3

    objects = await repo.list(skip=3, limit=3)
    assert len(objects) == 0

    objects = await repo.list(skip=2, limit=0)
    assert len(objects) == 1
    assert objects[0] == obj3


@pytest.mark.asyncio
async def test_list_filters(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    obj1 = await repo.create(dict(data='1'))
    obj2 = await repo.create(dict(data='2'))
    obj3 = await repo.create(dict(data='3'))

    objects = await repo.list()
    assert len(objects) == 3
    assert objects[0] == obj1
    assert objects[1] == obj2
    assert objects[2] == obj3

    objects = await repo.list(Q([]))
    assert len(objects) == 3
    assert objects[0] == obj1
    assert objects[1] == obj2
    assert objects[2] == obj3

    objects = await repo.list(Q([TestModel.data == '-1']))
    assert len(objects) == 0

    objects = await repo.list(Q([TestModel.data == '1']))
    assert len(objects) == 1
    assert objects[0] == obj1

    objects = await repo.list(Q([TestModel.data == '1', TestModel.data == '2']))
    assert len(objects) == 0

    objects = await repo.list(Q([(TestModel.data == '1') | (TestModel.data == '2')]))
    assert len(objects) == 2
    assert objects[0] == obj1
    assert objects[1] == obj2

    objects = await repo.list(Q([(TestModel.data == '1') & (TestModel.id == obj1.id)]))
    assert len(objects) == 1
    assert objects[0] == obj1

    objects = await repo.list(Q([text('data > :data')], params=dict(data='1')))
    assert len(objects) == 2
    assert objects[0] == obj2
    assert objects[1] == obj3


@pytest.mark.asyncio
async def test_count(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    obj1 = await repo.create(dict(data='1'))
    obj2 = await repo.create(dict(data='2'))
    obj3 = await repo.create(dict(data='3'))

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

    res = await repo.count(Q([text('data > :data')], params=dict(data='1')))
    assert res == 2


@pytest.mark.asyncio
async def test_exists(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    obj1 = await repo.create(dict(data='1'))
    obj2 = await repo.create(dict(data='2'))
    obj3 = await repo.create(dict(data='3'))

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

    res = await repo.exists_by(Q([text('data > :data')], params=dict(data='1')))
    assert res is True

    res = await repo.exists_by(Q([text('data > :data')], params=dict(data='3')))
    assert res is False


@pytest.mark.asyncio
async def test_load(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    instance = await repo.create(dict(id=1, data='1'))

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

    assert await repo.update_by_id(1, dict(data='3', create_date=datetime.now().replace(microsecond=0)))
    instance.data = '1'
    instance.create_date = None
    assert await repo.load(instance, only=['data'])

    assert instance.id == 1
    assert instance.data == '3'
    assert instance.create_date is None


@pytest.mark.asyncio
async def test_save(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    instance = TestModel(id=1, data='1')

    assert not await repo.get(1)

    assert await repo.save(instance)
    assert instance.id == 1
    assert instance.data == '1'
    assert isinstance(instance.create_date, datetime)

    instance2 = await repo.get(instance.id)
    assert instance2.id == instance.id
    assert instance2.data == instance.data
    assert isinstance(instance2.create_date, datetime)
    assert instance2.create_date == instance.create_date


@pytest.mark.asyncio
async def test_save_all(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    obj1 = TestModel(data='1')
    obj2 = TestModel(data='2')
    obj3 = TestModel(data='3')

    assert await repo.save_all([obj1, obj2, obj3])

    objects = await repo.get_any([obj1.id, obj2.id, obj3.id])
    assert len(objects) == 3
    assert objects[0] == obj1
    assert objects[1] == obj2
    assert objects[2] == obj3
    assert objects[0].id == obj1.id
    assert objects[0].data == obj1.data
    assert objects[1].id == obj2.id
    assert objects[1].data == obj2.data
    assert objects[2].id == obj3.id
    assert objects[2].data == obj3.data

    obj1.data = '4'
    obj2.data = '5'
    obj3.data = '6'

    assert await repo.save_all([obj1, obj2, obj3])

    objects = await repo.get_any([obj1.id, obj2.id, obj3.id])
    assert len(objects) == 3
    assert objects[0] == obj1
    assert objects[1] == obj2
    assert objects[2] == obj3
    assert objects[0].id == obj1.id
    assert objects[0].data == obj1.data
    assert objects[1].id == obj2.id
    assert objects[1].data == obj2.data
    assert objects[2].id == obj3.id
    assert objects[2].data == obj3.data


@pytest.mark.asyncio
async def test_delete(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    obj = await repo.create(dict(data='123'))

    objects = await repo.list()
    assert len(objects) == 1
    assert objects[0] == obj
    obj2 = await repo.get(obj.id)
    assert obj == obj2

    assert await repo.delete(obj)

    objects = await repo.list()
    assert len(objects) == 0
    assert not await repo.get(obj.id)

    assert not await repo.delete(obj)


@pytest.mark.asyncio
async def test_delete_all(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    obj1 = await repo.create(dict(data='1'))
    obj2 = await repo.create(dict(data='2'))
    obj3 = await repo.create(dict(data='3'))

    assert 2 == await repo.delete_all([obj1.id, obj2.id])
    assert 0 == await repo.delete_all([obj1.id, obj2.id])

    assert not await repo.load(obj1)
    assert not await repo.load(obj2)
    assert await repo.load(obj3)


@pytest.mark.asyncio
async def test_delete_by_id(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    obj = await repo.create(dict(data='123'))

    objects = await repo.list()
    assert len(objects) == 1
    assert objects[0] == obj
    obj2 = await repo.get(obj.id)
    assert obj == obj2

    assert await repo.delete_by_id(obj.id)

    objects = await repo.list()
    assert len(objects) == 0
    assert not await repo.get(obj.id)

    assert not await repo.delete_by_id(obj.id)
    assert not await repo.delete_by_id(-1)


@pytest.mark.asyncio
async def test_delete_by(sqla_session):
    repo = SqlaModelRepository(TestModel, sqla_session)
    obj1 = await repo.create(dict(data='1'))
    obj2 = await repo.create(dict(data='2'))
    obj3 = await repo.create(dict(data='3'))

    assert 2 == await repo.delete_by(Q([TestModel.data != '1']))
    assert 0 == await repo.delete_by(Q([TestModel.data != '1']))

    assert await repo.load(obj1)
    assert not await repo.load(obj2)
    assert not await repo.load(obj3)
