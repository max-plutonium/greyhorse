from greyhorse.app.resources import make_container
from greyhorse_renders.abc import AsyncRender, AsyncRenderFactory, SyncRender, SyncRenderFactory
from greyhorse_renders.controller import RendersController


def test_controller() -> None:
    ctrl = RendersController()
    container = make_container()

    assert ctrl.setup(container).unwrap()
    assert len(container.registry) > 0

    sync_render_factory = container.get(SyncRenderFactory)
    assert sync_render_factory.is_just()
    sync_render_factory = sync_render_factory.unwrap()

    render = sync_render_factory('', [])
    assert isinstance(render, SyncRender)

    async_render_factory = container.get(AsyncRenderFactory)
    assert async_render_factory.is_just()
    async_render_factory = async_render_factory.unwrap()

    render = async_render_factory('', [])
    assert isinstance(render, AsyncRender)

    assert ctrl.teardown(container).unwrap()

    assert len(container.registry) == 0
