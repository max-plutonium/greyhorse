from datetime import datetime
from unittest import mock

import pytest
from greyhorse_sqla.model import SqlaModel
from greyhorse_sqla.query import SqlaFiltersQuery as Q
from greyhorse_sqla.repository import SqlaModelRepository
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column as C


class TestModel(SqlaModel[int]):
    __tablename__ = 'test_model'

    id: Mapped[int] = C(primary_key=True)
    data: Mapped[str] = C(String(128))
    create_date: Mapped[datetime] = C(DateTime(timezone=False), server_default=func.now())

    __mapper_args__ = {'eager_defaults': True}


@pytest.mark.asyncio
async def test_model_fields() -> None:
    m = TestModel()
    assert TestModel.get_fields() == {'id', 'create_date', 'data'}
    assert m.get_values() == {'id': None, 'create_date': None, 'data': None}

    m.id = 123
    m.data = 'qwer'
    assert m.get_values() == {'id': 123, 'create_date': None, 'data': 'qwer'}


@pytest.mark.asyncio
async def test_get() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    repo_mock.get.return_value = TestModel(id=1, data='123')
    instance = await TestModel.get(1)
    assert instance
    assert instance.id == 1
    assert instance.data == '123'
    repo_mock.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_any() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    repo_mock.get_any.return_value = [TestModel(id=1, data='123')]
    objects = await TestModel.get_any([1])
    assert len(objects) == 1
    assert objects[0].id == 1
    assert objects[0].data == '123'
    repo_mock.get_any.assert_called_once_with([1])


@pytest.mark.asyncio
async def test_list() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    repo_mock.list.return_value = [TestModel(id=1, data='123')]
    objects = await TestModel.list(Q([1]))
    assert len(objects) == 1
    assert objects[0].id == 1
    assert objects[0].data == '123'
    repo_mock.list.assert_called_once_with(Q([1]), None, 0, 0)


@pytest.mark.asyncio
async def test_count() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    repo_mock.count.return_value = 3
    assert await TestModel.count(Q([1])) == 3
    repo_mock.count.assert_called_once_with(Q([1]))


@pytest.mark.asyncio
async def test_exists() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    repo_mock.exists.return_value = True
    assert await TestModel.exists(1)
    repo_mock.exists.assert_called_once_with(1)

    repo_mock.exists_by.return_value = True
    assert await TestModel.exists_by(Q([1]))
    repo_mock.exists_by.assert_called_once_with(Q([1]))


@pytest.mark.asyncio
async def test_load() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    instance = TestModel(id=1, data='123')

    repo_mock.load.return_value = True
    assert await instance.load(only=['data'])
    repo_mock.load.assert_called_once_with(instance, ['data'])


@pytest.mark.asyncio
async def test_create() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    repo_mock.create.return_value = TestModel(id=1, data='123')
    instance = await TestModel.create({'id': 1, 'data': '123'})
    assert instance
    assert instance.id == 1
    assert instance.data == '123'
    repo_mock.create.assert_called_once_with({'id': 1, 'data': '123'})


@pytest.mark.asyncio
async def test_get_or_create() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    repo_mock.get.return_value = None
    repo_mock.create.return_value = TestModel(id=1, data='123')
    instance, created = await TestModel.get_or_create(1, {'id': 1, 'data': '123'})
    assert instance
    assert created
    assert instance.id == 1
    assert instance.data == '123'
    repo_mock.get.assert_called_once_with(1)
    repo_mock.create.assert_called_once_with({'id': 1, 'data': '123'})
    repo_mock.get.reset_mock()
    repo_mock.create.reset_mock()

    repo_mock.get.return_value = TestModel(id=1, data='123')
    instance, created = await TestModel.get_or_create(1, {'a': 1, 'b': '123'})
    assert instance
    assert not created
    assert instance.id == 1
    assert instance.data == '123'
    repo_mock.get.assert_called_once_with(1)
    repo_mock.create.assert_not_called()


@pytest.mark.asyncio
async def test_update() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    instance = TestModel(id=1, data='123')
    instance.get_id_value = lambda: 1

    repo_mock.update_by_id.return_value = True
    assert await instance.update({'data': '456'})
    repo_mock.update_by_id.assert_called_once_with(1, {'data': '456'})


@pytest.mark.asyncio
async def test_update_by_id() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    repo_mock.update_by_id.return_value = True
    assert await TestModel.update_by_id(2, {'data': '123'})
    repo_mock.update_by_id.assert_called_once_with(2, {'data': '123'})


@pytest.mark.asyncio
async def test_update_by() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    repo_mock.update_by.return_value = 1
    assert await TestModel.update_by(Q([0]), {'data': '123'}) == 1
    repo_mock.update_by.assert_called_once_with(Q([0]), {'data': '123'})


@pytest.mark.asyncio
async def test_save() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    instance = TestModel(id=1, data='123')

    repo_mock.save.return_value = True
    assert await instance.save()
    repo_mock.save.assert_called_once_with(instance)


@pytest.mark.asyncio
async def test_save_all() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    repo_mock.save_all.return_value = True
    assert await TestModel.save_all([1, 2])
    repo_mock.save_all.assert_called_once_with([1, 2])


@pytest.mark.asyncio
async def test_delete() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    instance = TestModel(id=1, data='123')

    repo_mock.delete.return_value = True
    assert await instance.delete()
    repo_mock.delete.assert_called_once_with(instance)


@pytest.mark.asyncio
async def test_delete_all() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    repo_mock.delete_all.return_value = 2
    assert await TestModel.delete_all([1, 2]) == 2
    repo_mock.delete_all.assert_called_once_with([1, 2])


@pytest.mark.asyncio
async def test_delete_by_id() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    repo_mock.delete_by_id.return_value = True
    assert await TestModel.delete_by_id(1)
    repo_mock.delete_by_id.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_by() -> None:
    repo_mock = mock.AsyncMock(spec=SqlaModelRepository)
    TestModel.bind(repo_mock)

    repo_mock.delete_by.return_value = 1
    assert await TestModel.delete_by(Q([0])) == 1
    repo_mock.delete_by.assert_called_once_with(Q([0]))
