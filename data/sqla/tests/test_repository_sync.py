from datetime import UTC, datetime, timedelta

import pytest
from greyhorse.data.repositories import EntityError
from greyhorse.result import Err
from greyhorse_sqla.config import EngineConf, SqlEngineType
from greyhorse_sqla.contexts import SqlaSyncConnCtx, SqlaSyncSessionCtx
from greyhorse_sqla.engine_sync import SyncSqlaEngine
from greyhorse_sqla.factory import SyncSqlaEngineFactory
from greyhorse_sqla.query import SqlaQuery as Q  # noqa: N814
from greyhorse_sqla.repositories import SyncSqlaRepository
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


@pytest.fixture(
    scope='module',
    params=(
        (SQLITE_URI, SqlEngineType.SQLITE),
        (POSTGRES_URI, SqlEngineType.POSTGRES),
        (MYSQL_URI, SqlEngineType.MYSQL),
    ),
    ids=('SQLite', 'Postgres', 'MySQL'),
)
def sqla_engine(request) -> SyncSqlaEngine:  # noqa: ANN001
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

    factory = SyncSqlaEngineFactory()
    engine = factory.create_engine('test', config)
    engine.start()

    conn_ctx = engine.get_context(SqlaSyncConnCtx).unwrap()

    with conn_ctx as conn:
        Base.metadata.drop_all(conn, tables=[TestModel.__table__])
        Base.metadata.create_all(conn, tables=[TestModel.__table__])
        conn.commit()

    yield engine

    with conn_ctx as conn:
        Base.metadata.drop_all(conn, tables=[TestModel.__table__])
        conn.commit()

    engine.stop()


@pytest.fixture(scope='function')
def session_ctx(sqla_engine: SyncSqlaEngine) -> SqlaSyncSessionCtx:
    session_ctx = sqla_engine.get_context(SqlaSyncSessionCtx).unwrap()

    with session_ctx:
        yield session_ctx


TestModelSyncRepo = SyncSqlaRepository[TestModel, int]


@pytest.mark.asyncio
def test_create(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    instance = repo.create({'id': 1, 'data': '123'}).unwrap()
    assert instance.id > 0
    assert instance.data == '123'
    now = datetime.now(UTC).replace(microsecond=0, tzinfo=None)
    assert now - instance.create_date.replace(microsecond=0, tzinfo=None) < timedelta(seconds=2)


@pytest.mark.asyncio
def test_get_or_create(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    res, created = repo.get_or_create(999, dict(id=999, data='123'))
    assert created is True
    assert res.is_ok()

    obj1 = res.unwrap()
    assert obj1.id == 999
    assert obj1.data == '123'

    res, created = repo.get_or_create(999, dict(id=999, data='123'))
    assert created is False
    assert res.is_ok()

    obj2 = res.unwrap()
    assert obj2.id == 999
    assert obj2.data == '123'


@pytest.mark.asyncio
def test_update_by_id(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    obj1 = repo.create(dict(data='123')).unwrap()

    assert repo.update_by_id(obj1.id, dict(data='234'))
    assert Err(EntityError.Empty()) == repo.update_by_id(-1, dict(data='234'))


@pytest.mark.asyncio
def test_get(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    obj1 = repo.create(dict(data='123')).unwrap()

    obj2 = repo.get(obj1.id).unwrap()
    assert obj1.id == obj2.id
    assert obj1.data == obj2.data
    assert obj1 == obj2

    assert not repo.get(-1)


@pytest.mark.asyncio
def test_get_any(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    obj1 = repo.create(dict(data='1')).unwrap()
    obj2 = repo.create(dict(data='2')).unwrap()
    obj3 = repo.create(dict(data='3')).unwrap()

    objects = list(repo.get_any([]))
    assert len(objects) == 0

    objects = list(repo.get_any([obj1.id, obj2.id, obj3.id]))
    assert len(objects) == 3
    assert objects[0].unwrap() == obj1
    assert objects[1].unwrap() == obj2
    assert objects[2].unwrap() == obj3

    objects = list(repo.get_any([obj1.id, obj3.id]))
    assert len(objects) == 2
    assert objects[0].unwrap() == obj1
    assert objects[1].unwrap() == obj3

    objects = list(repo.get_any([-1, obj1.id, 999999, obj3.id, 0]))
    assert len(objects) == 5
    assert objects[0].is_nothing()
    assert objects[1].unwrap() == obj1
    assert objects[2].is_nothing()
    assert objects[3].unwrap() == obj3
    assert objects[4].is_nothing()


@pytest.mark.asyncio
def test_exists(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    obj1 = repo.create(dict(data='1')).unwrap()
    repo.create(dict(data='2'))
    repo.create(dict(data='3'))

    res = repo.exists(obj1.id)
    assert res is True

    res = repo.exists(-1)
    assert res is False

    res = repo.exists_by(Q([]))
    assert res is True

    res = repo.exists_by(Q([TestModel.data == '-1']))
    assert res is False

    res = repo.exists_by(Q([TestModel.data == '1']))
    assert res is True

    res = repo.exists_by(Q([TestModel.data == '1', TestModel.data == '2']))
    assert res is False

    res = repo.exists_by(Q([(TestModel.data == '1') | (TestModel.data == '2')]))
    assert res is True

    res = repo.exists_by(Q([(TestModel.data == '1') & (TestModel.id == obj1.id)]))
    assert res is True

    res = repo.exists_by(Q([text('data > :data')], data='1'))
    assert res is True

    res = repo.exists_by(Q([text('data > :data')], data='3'))
    assert res is False


@pytest.mark.asyncio
def test_load(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    instance = repo.create(dict(id=1, data='1')).unwrap()

    assert not repo.load(TestModel(id=1))

    assert instance.id == 1
    assert instance.data == '1'
    assert isinstance(instance.create_date, datetime)

    assert repo.update_by_id(1, dict(data='2'))
    instance.data = '1'
    instance.create_date = None
    assert repo.load(instance)

    assert instance.id == 1
    assert instance.data == '2'
    assert isinstance(instance.create_date, datetime)

    assert repo.update_by_id(
        1, dict(data='3', create_date=datetime.now().replace(microsecond=0))
    )
    instance.data = '1'
    instance.create_date = None
    assert repo.load(instance, only=['data'])

    assert instance.id == 1
    assert instance.data == '3'
    assert instance.create_date is None


@pytest.mark.asyncio
def test_list(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    obj1 = repo.create(dict(data='1')).unwrap()
    obj2 = repo.create(dict(data='2')).unwrap()
    obj3 = repo.create(dict(data='3')).unwrap()

    objects = list(repo.list())
    assert len(objects) == 3
    assert objects[0] == obj1
    assert objects[1] == obj2
    assert objects[2] == obj3

    objects = list(repo.list(skip=1))
    assert len(objects) == 2
    assert objects[0] == obj2
    assert objects[1] == obj3

    objects = list(repo.list(skip=2))
    assert len(objects) == 1
    assert objects[0] == obj3

    objects = list(repo.list(skip=3))
    assert len(objects) == 0

    objects = list(repo.list(limit=1))
    assert len(objects) == 1
    assert objects[0] == obj1

    objects = list(repo.list(limit=2))
    assert len(objects) == 2
    assert objects[0] == obj1
    assert objects[1] == obj2

    objects = list(repo.list(limit=3))
    assert len(objects) == 3
    assert objects[0] == obj1
    assert objects[1] == obj2
    assert objects[2] == obj3

    objects = list(repo.list(skip=1, limit=3))
    assert len(objects) == 2
    assert objects[0] == obj2
    assert objects[1] == obj3

    objects = list(repo.list(skip=2, limit=1))
    assert len(objects) == 1
    assert objects[0] == obj3

    objects = list(repo.list(skip=3, limit=3))
    assert len(objects) == 0

    objects = list(repo.list(skip=2, limit=0))
    assert len(objects) == 1
    assert objects[0] == obj3


@pytest.mark.asyncio
def test_list_filters(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    obj1 = repo.create(dict(data='1')).unwrap()
    obj2 = repo.create(dict(data='2')).unwrap()
    obj3 = repo.create(dict(data='3')).unwrap()

    objects = list(repo.list())
    assert len(objects) == 3
    assert objects[0] == obj1
    assert objects[1] == obj2
    assert objects[2] == obj3

    objects = list(repo.list(Q([])))
    assert len(objects) == 3
    assert objects[0] == obj1
    assert objects[1] == obj2
    assert objects[2] == obj3

    objects = list(repo.list(Q([TestModel.data == '-1'])))
    assert len(objects) == 0

    objects = list(repo.list(Q([TestModel.data == '1'])))
    assert len(objects) == 1
    assert objects[0] == obj1

    objects = list(repo.list(Q([TestModel.data == '1', TestModel.data == '2'])))
    assert len(objects) == 0

    objects = list(repo.list(Q([(TestModel.data == '1') | (TestModel.data == '2')])))
    assert len(objects) == 2
    assert objects[0] == obj1
    assert objects[1] == obj2

    objects = list(repo.list(Q([(TestModel.data == '1') & (TestModel.id == obj1.id)])))
    assert len(objects) == 1
    assert objects[0] == obj1

    objects = list(repo.list(Q([text('data > :data')], data='1')))
    assert len(objects) == 2
    assert objects[0] == obj2
    assert objects[1] == obj3


@pytest.mark.asyncio
def test_count(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    obj1 = repo.create(dict(data='1')).unwrap()
    repo.create(dict(data='2'))
    repo.create(dict(data='3'))

    res = repo.count()
    assert res == 3

    res = repo.count(Q([]))
    assert res == 3

    res = repo.count(Q([TestModel.data == '-1']))
    assert res == 0

    res = repo.count(Q([TestModel.data == '1']))
    assert res == 1

    res = repo.count(Q([TestModel.data == '1', TestModel.data == '2']))
    assert res == 0

    res = repo.count(Q([(TestModel.data == '1') | (TestModel.data == '2')]))
    assert res == 2

    res = repo.count(Q([(TestModel.data == '1') & (TestModel.id == obj1.id)]))
    assert res == 1

    res = repo.count(Q([text('data > :data')], data='1'))
    assert res == 2


@pytest.mark.asyncio
def test_save(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    instance = TestModel(id=1, data='1')

    assert not repo.get(1)

    assert repo.save(instance)
    assert instance.id == 1
    assert instance.data == '1'
    assert isinstance(instance.create_date, datetime)

    instance2 = repo.get(instance.id).unwrap()
    assert instance2.id == instance.id
    assert instance2.data == instance.data
    assert isinstance(instance2.create_date, datetime)
    assert instance2.create_date == instance.create_date


@pytest.mark.asyncio
def test_save_all(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    obj1 = TestModel(data='1')
    obj2 = TestModel(data='2')
    obj3 = TestModel(data='3')

    assert repo.save_all([obj1, obj2, obj3]) == 3

    objects = list(repo.get_any([obj1.id, obj2.id, obj3.id]))
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

    assert repo.save_all([obj1, obj2, obj3])

    objects = list(repo.get_any([obj1.id, obj2.id, obj3.id]))
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
def test_delete(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    obj = repo.create(dict(data='123')).unwrap()

    obj2 = repo.get(obj.id).unwrap()
    assert obj == obj2

    assert repo.delete(obj)

    assert (repo.get(obj.id)).is_nothing()
    assert not repo.delete(obj)


@pytest.mark.asyncio
def test_delete_all(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    obj1 = repo.create(dict(data='1')).unwrap()
    obj2 = repo.create(dict(data='2')).unwrap()
    obj3 = repo.create(dict(data='3')).unwrap()

    assert repo.delete_all([obj1.id, obj2.id]) == 2
    assert repo.delete_all([obj1.id, obj2.id]) == 0

    assert not repo.load(obj1)
    assert not repo.load(obj2)
    assert repo.load(obj3)

    assert repo.delete_all() == 1
    assert not repo.load(obj3)


@pytest.mark.asyncio
def test_delete_by_id(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    obj = repo.create(dict(data='123')).unwrap()

    obj2 = repo.get(obj.id).unwrap()
    assert obj == obj2

    assert repo.delete_by_id(obj.id)

    assert (repo.get(obj.id)).is_nothing()
    assert not repo.delete_by_id(obj.id)

    assert not repo.delete_by_id(-1)


@pytest.mark.asyncio
def test_update_by(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    obj1 = repo.create(dict(data='1')).unwrap()
    obj2 = repo.create(dict(data='2')).unwrap()
    obj3 = repo.create(dict(data='3')).unwrap()

    assert repo.update_by(Q([TestModel.data != '1']), dict(data='0')) == 2

    assert obj1.data == '1'
    assert obj2.data == '0'
    assert obj3.data == '0'


@pytest.mark.asyncio
def test_delete_by(session_ctx: SqlaSyncSessionCtx) -> None:
    repo = TestModelSyncRepo(session_ctx)
    obj1 = repo.create(dict(data='1')).unwrap()
    obj2 = repo.create(dict(data='2')).unwrap()
    obj3 = repo.create(dict(data='3')).unwrap()

    assert repo.delete_by(Q([TestModel.data != '1'])) == 2
    assert repo.delete_by(Q([TestModel.data != '1'])) == 0

    assert repo.load(obj1)
    assert not repo.load(obj2)
    assert not repo.load(obj3)
