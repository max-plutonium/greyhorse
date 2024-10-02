from pathlib import Path
from typing import Any

import pytest
from greyhorse.app.registries import MutDictRegistry
from greyhorse_renders.abc import AsyncRender, AsyncRenderFactory, SyncRender, SyncRenderFactory
from greyhorse_renders.controller import RendersController


@pytest.fixture
def registry():
    ctrl = RendersController()

    registry = MutDictRegistry[type, Any]()
    assert ctrl.setup(registry).unwrap()
    assert len(registry) > 0

    yield registry

    assert ctrl.teardown(registry).unwrap()
    assert len(registry) == 0


@pytest.mark.parametrize('param', ('', 'jinja'), ids=('Simple', 'Jinja'))
def test_sync_render(param, registry) -> None:
    sync_render_factory = registry.get(SyncRenderFactory).unwrap()
    render = sync_render_factory(param, [Path('tests/data')])
    assert isinstance(render, SyncRender)

    res = render(f'template{'.' if param else ''}{param}.txt', seq=range(1, 10))
    assert res.is_ok()
    print(res.unwrap())

    res = render.eval_string('data.upper() == "TEST"', data='test')
    assert res.is_ok()

    if param == 'jinja':
        assert res.unwrap() is True
    else:
        assert res.unwrap() is None


@pytest.mark.parametrize('param', ('', 'jinja'), ids=('Simple', 'Jinja'))
@pytest.mark.asyncio
async def test_async_render(param, registry) -> None:
    async_render_factory = registry.get(AsyncRenderFactory).unwrap()
    render = async_render_factory(param, [Path('tests/data')])
    assert isinstance(render, AsyncRender)

    res = await render(f'template{'.' if param else ''}{param}.txt', seq=range(1, 10))
    assert res.is_ok()
    print(res.unwrap())

    res = await render.eval_string('data.upper() == "TEST"', data='test')
    assert res.is_ok()

    if param == 'jinja':
        assert res.unwrap() is True
    else:
        assert res.unwrap() is None
