from pathlib import Path

import pytest
from greyhorse.app.resources import Container, make_container
from greyhorse_renders.abc import AsyncRender, AsyncRenderFactory, SyncRender, SyncRenderFactory
from greyhorse_renders.controller import RendersController


@pytest.fixture
def container() -> Container:
    ctrl = RendersController()
    container = make_container()

    assert ctrl.setup(container).unwrap()
    assert len(container.registry) > 0

    yield container

    assert ctrl.teardown(container).unwrap()
    assert len(container.registry) == 0


@pytest.mark.parametrize('param', ('', 'jinja'), ids=('Simple', 'Jinja'))
def test_sync_render(param: str, container: Container) -> None:
    sync_render_factory = container.get(SyncRenderFactory).unwrap()
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
async def test_async_render(param: str, container: Container) -> None:
    async_render_factory = container.get(AsyncRenderFactory).unwrap()
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
