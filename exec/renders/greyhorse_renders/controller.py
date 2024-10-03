from pathlib import Path
from typing import Any, override

from greyhorse.app.abc.collectors import MutNamedCollector, NamedCollector
from greyhorse.app.abc.controllers import ControllerError
from greyhorse.app.entities.controllers import SyncController
from greyhorse.logging import logger
from greyhorse.result import Ok, Result
from greyhorse.utils.imports import import_path

from .abc import AsyncRender, AsyncRenderFactory, SyncRender, SyncRenderFactory

_RENDER_PACKAGES = {
    '': ('simple:SimpleSyncRender', 'simple:SimpleAsyncRender'),
    'jinja': ('jinja:JinjaSyncRender', 'jinja:JinjaAsyncRender'),
}


class SyncRenderFactoryImpl(SyncRenderFactory):
    def __init__(self, renders: dict[str, type[SyncRender]]) -> None:
        self._renders = renders

    @override
    def __call__(self, name: str, templates_dirs: list[Path]) -> SyncRender:
        if name in self._renders:
            return self._renders[name](templates_dirs)
        return self._renders[''](templates_dirs)


class AsyncRenderFactoryImpl(AsyncRenderFactory):
    def __init__(self, renders: dict[str, type[AsyncRender]]) -> None:
        self._renders = renders

    @override
    def __call__(self, name: str, templates_dirs: list[Path]) -> AsyncRender:
        if name in self._renders:
            return self._renders[name](templates_dirs)
        return self._renders[''](templates_dirs)


class RendersController(SyncController):
    def __init__(self) -> None:
        super().__init__()

    @override
    def setup(self, collector: NamedCollector[type, Any]) -> Result[bool, ControllerError]:
        sync_renders: dict[str, type[SyncRender]] = {}
        async_renders: dict[str, type[AsyncRender]] = {}

        for key, class_paths in _RENDER_PACKAGES.items():
            for class_path, is_async in zip(class_paths, (False, True), strict=False):
                if not class_path:
                    continue

                try:
                    class_obj = import_path(f'..private.{class_path}', __name__)

                except (ImportError, AttributeError):
                    logger.warn(f'Render not found for {class_path}')
                    continue

                if is_async:
                    async_renders[key] = class_obj
                else:
                    sync_renders[key] = class_obj

        res = collector.add(SyncRenderFactory, SyncRenderFactoryImpl(sync_renders))
        res &= collector.add(AsyncRenderFactory, AsyncRenderFactoryImpl(async_renders))
        return Ok(res)

    @override
    def teardown(
        self, collector: MutNamedCollector[type, Any]
    ) -> Result[bool, ControllerError]:
        res = collector.remove(SyncRenderFactory)
        res &= collector.remove(AsyncRenderFactory)
        return Ok(res)
