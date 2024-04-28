from greyhorse_renders.abc import SyncRenderFactory, SyncRender, AsyncRenderFactory, AsyncRender
from greyhorse_renders.controller import RendersController


def test_controller():
    ctrl = RendersController('test')
    assert ctrl.create().success

    sync_render_factory = ctrl.operator_factories.get(SyncRenderFactory)
    assert sync_render_factory
    sync_render_factory = sync_render_factory()

    render = sync_render_factory('', [])
    assert isinstance(render, SyncRender)

    async_render_factory = ctrl.operator_factories.get(AsyncRenderFactory)
    assert async_render_factory
    async_render_factory = async_render_factory()

    render = async_render_factory('', [])
    assert isinstance(render, AsyncRender)

    assert ctrl.destroy().success
