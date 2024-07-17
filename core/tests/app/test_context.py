import contextlib
from dataclasses import dataclass
from datetime import datetime
from unittest.mock import Mock, MagicMock

import pytest

from greyhorse.app.context import SyncContext, ContextBuilder, AsyncContext


def test_sync_context_scalar():
    ctx_builder = ContextBuilder[int](lambda: 123, SyncContext[int])

    mock_context = MagicMock(spec=contextlib.AbstractContextManager)

    @contextlib.contextmanager
    def mock_fn():
        with mock_context:
            yield

    mock_finalizer = Mock()

    ctx_builder.add_context(mock_fn)
    ctx_builder.add_finalizer(mock_finalizer)

    ctx = ctx_builder.build()

    with ctx as number:
        assert number == 123

    mock_context.__enter__.assert_called_once()
    mock_context.__exit__.assert_called_once()
    mock_finalizer.assert_called_once()


@dataclass
class ContextData:
    id: int
    name: str
    timestamp: datetime


def test_sync_context_complex():
    ctx_builder = ContextBuilder[ContextData](ContextData, SyncContext[ContextData])

    mock_context = MagicMock(spec=contextlib.AbstractContextManager)

    @contextlib.contextmanager
    def mock_fn():
        with mock_context:
            yield

    mock_finalizer = Mock()

    ctx_builder.add_context(mock_fn)
    ctx_builder.add_finalizer(mock_finalizer)
    ctx_builder.add_param('id', 123)
    ctx_builder.add_param('name', lambda: 'name')
    ctx_builder.add_param('timestamp', datetime.now)

    ctx = ctx_builder.build()

    with ctx as data:
        assert data.id == 123
        assert data.name == 'name'
        assert data.timestamp.replace(second=0, microsecond=0) == datetime.now().replace(second=0, microsecond=0)

    mock_context.__enter__.assert_called_once()
    mock_context.__exit__.assert_called_once()
    mock_finalizer.assert_called_once()


@pytest.mark.asyncio
async def test_async_context_scalar():
    ctx_builder = ContextBuilder[int](lambda: 123, AsyncContext[int])

    mock_context = MagicMock(spec=contextlib.AbstractAsyncContextManager)

    @contextlib.asynccontextmanager
    async def mock_fn():
        async with mock_context:
            yield

    mock_finalizer = Mock()

    ctx_builder.add_context(mock_fn)
    ctx_builder.add_finalizer(mock_finalizer)

    ctx = ctx_builder.build()

    async with ctx as number:
        assert number == 123

    mock_context.__aenter__.assert_called_once()
    mock_context.__aexit__.assert_called_once()
    mock_finalizer.assert_called_once()


@pytest.mark.asyncio
async def test_async_context_complex():
    ctx_builder = ContextBuilder[ContextData](ContextData, AsyncContext[ContextData])

    mock_context = MagicMock(spec=contextlib.AbstractAsyncContextManager)

    @contextlib.asynccontextmanager
    async def mock_fn():
        async with mock_context:
            yield

    async def _get_name():
        return 'name'

    mock_finalizer = Mock()

    ctx_builder.add_context(mock_fn)
    ctx_builder.add_finalizer(mock_finalizer)
    ctx_builder.add_param('id', 123)
    ctx_builder.add_param('name', _get_name)
    ctx_builder.add_param('timestamp', datetime.now)

    ctx = ctx_builder.build()

    async with ctx as data:
        assert data.id == 123
        assert data.name == 'name'
        assert data.timestamp.replace(second=0, microsecond=0) == datetime.now().replace(second=0, microsecond=0)

    mock_context.__aenter__.assert_called_once()
    mock_context.__aexit__.assert_called_once()
    mock_finalizer.assert_called_once()
