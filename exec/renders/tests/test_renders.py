from pathlib import Path

import pytest

from greyhorse_renders.abc import SyncRenderFactory, SyncRender, AsyncRenderFactory, AsyncRender
from greyhorse_renders.controller import RendersController


@pytest.mark.parametrize(
    'param',
    ('', 'jinja'),
    ids=('Simple', 'Jinja'),
)
def test_sync_render(param):
    ctrl = RendersController('test')
    assert ctrl.create().success

    sync_render_factory = ctrl.operator_factories.get(SyncRenderFactory)()
    render = sync_render_factory(param, [Path('tests/data')])
    assert isinstance(render, SyncRender)

    res = render(
        f'template{'.' if param else ''}{param}.txt',
        seq=range(1, 10),
    )
    assert res.success
    print(res.result)

    assert ctrl.destroy().success


@pytest.mark.parametrize(
    'param',
    ('', 'jinja'),
    ids=('Simple', 'Jinja'),
)
@pytest.mark.asyncio
async def test_async_render(param):
    ctrl = RendersController('test')
    assert ctrl.create().success

    async_render_factory = ctrl.operator_factories.get(AsyncRenderFactory)()
    render = async_render_factory(param, [Path('tests/data')])
    assert isinstance(render, AsyncRender)

    res = await render(
        f'template{'.' if param else ''}{param}.txt',
        seq=range(1, 10),
    )
    assert res.success
    print(res.result)

    assert ctrl.destroy().success
