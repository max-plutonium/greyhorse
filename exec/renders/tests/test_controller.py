from typing import Any

from greyhorse.app.registries import MutNamedDictRegistry
from greyhorse_renders.abc import AsyncRender, AsyncRenderFactory, SyncRender, SyncRenderFactory
from greyhorse_renders.controller import RendersController


def test_controller() -> None:
    ctrl = RendersController()

    registry = MutNamedDictRegistry[type, Any]()
    assert ctrl.setup(registry).unwrap()
    assert len(registry) > 0

    sync_render_factory = registry.get(SyncRenderFactory)
    assert sync_render_factory.is_just()
    sync_render_factory = sync_render_factory.unwrap()

    render = sync_render_factory('', [])
    assert isinstance(render, SyncRender)

    async_render_factory = registry.get(AsyncRenderFactory)
    assert async_render_factory.is_just()
    async_render_factory = async_render_factory.unwrap()

    render = async_render_factory('', [])
    assert isinstance(render, AsyncRender)

    assert ctrl.teardown(registry).unwrap()

    assert len(registry) == 0
