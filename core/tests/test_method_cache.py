from datetime import datetime, timedelta
from unittest import mock
from unittest.mock import call

import pytest
from greyhorse.data.cache.base import CacheData, ModelCacheOperator
from greyhorse.data.cache.method import MethodCache


@pytest.mark.asyncio
async def test_keys() -> None:
    operator_mock = mock.AsyncMock(spec=ModelCacheOperator)
    method_cache = MethodCache(operator_mock, timedelta(seconds=3))

    operator_mock.get_model_cache_key.return_value = 'greyhorse.models.test'
    operator_mock.get_cache_id.return_value = '123'
    operator_mock.get_cache_key.return_value = 'greyhorse.models.test:1'

    assert method_cache.get_model_cache_key() == 'greyhorse.models.test'
    assert method_cache.get_cache_id(123) == '123'
    assert method_cache.get_cache_key(1) == 'greyhorse.models.test:1'

    operator_mock.get_model_cache_key.assert_called_once()
    operator_mock.get_cache_id.assert_called_once_with(123)
    operator_mock.get_cache_key.assert_called_once_with(1)
    operator_mock.get_model_cache_key.reset_mock()
    operator_mock.get_cache_id.reset_mock()
    operator_mock.get_cache_key.reset_mock()


@pytest.mark.asyncio
async def test_put() -> None:
    operator_mock = mock.AsyncMock(spec=ModelCacheOperator)
    method_cache = MethodCache(operator_mock, timedelta(seconds=3))
    args = {'a': 1, 'b': 12.34, 'c': 'asdf', 'd': datetime.now()}

    operator_mock.cache_one.return_value = True
    assert await method_cache.put('method', None, None)
    operator_mock.cache_one.assert_called_once_with(
        CacheData(cache_id=MethodCache.cache_key_for('method', None), data=None),
        ttl=timedelta(seconds=3),
    )
    operator_mock.cache_one.reset_mock()

    operator_mock.cache_one.return_value = True
    assert await method_cache.put('method', args, 123)
    operator_mock.cache_one.assert_called_once_with(
        CacheData(cache_id=MethodCache.cache_key_for('method', args), data=123),
        ttl=timedelta(seconds=3),
    )
    operator_mock.cache_one.reset_mock()


@pytest.mark.asyncio
async def test_get() -> None:
    operator_mock = mock.AsyncMock(spec=ModelCacheOperator)
    method_cache = MethodCache(operator_mock)
    args = {'a': 1, 'b': 12.34, 'c': 'asdf', 'd': datetime.now()}

    operator_mock.get_cache_key.return_value = 'greyhorse.models.test:1'

    operator_mock.load_one.return_value = (False, None)
    exists, data = await method_cache.get('method', args)
    assert not exists
    assert not data
    operator_mock.get_cache_key.assert_called_once_with(
        MethodCache.cache_key_for('method', args)
    )
    operator_mock.load_one.assert_called_once_with('greyhorse.models.test:1')
    operator_mock.get_cache_key.reset_mock()
    operator_mock.load_one.reset_mock()

    operator_mock.load_one.return_value = (True, 123)
    exists, data = await method_cache.get('method', args)
    assert exists
    assert data == 123
    operator_mock.get_cache_key.assert_called_once_with(
        MethodCache.cache_key_for('method', args)
    )
    operator_mock.load_one.assert_called_once_with('greyhorse.models.test:1')
    operator_mock.get_cache_key.reset_mock()
    operator_mock.load_one.reset_mock()


@pytest.mark.asyncio
async def test_drop() -> None:
    operator_mock = mock.AsyncMock(spec=ModelCacheOperator)
    method_cache = MethodCache(operator_mock)
    args = {'a': 1, 'b': 12.34, 'c': 'asdf', 'd': datetime.now()}

    operator_mock.get_cache_key.return_value = 'greyhorse.models.test:1'

    operator_mock.drop_one.return_value = True
    assert await method_cache.drop('method', args)
    operator_mock.get_cache_key.assert_called_once_with(
        MethodCache.cache_key_for('method', args)
    )
    operator_mock.drop_one.assert_called_once_with('greyhorse.models.test:1')
    operator_mock.get_cache_key.reset_mock()
    operator_mock.drop_one.reset_mock()


@pytest.mark.asyncio
async def test_drop_all() -> None:
    operator_mock = mock.AsyncMock(spec=ModelCacheOperator)
    method_cache = MethodCache(operator_mock)

    operator_mock.drop_all.return_value = 1
    assert await method_cache.drop_all() == 1
    operator_mock.drop_all.assert_called_once()
    operator_mock.drop_all.reset_mock()

    assert await method_cache.drop_all(['1', '2']) == 2
    operator_mock.drop_all.assert_has_calls([call('1'), call('2')], any_order=True)
    operator_mock.drop_all.reset_mock()
