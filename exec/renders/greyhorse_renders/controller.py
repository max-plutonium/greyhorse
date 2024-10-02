from pathlib import Path
from typing import Any, override

from greyhorse.app.abc.collectors import Collector, MutCollector
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
        self._sync_renders: dict[str, type[SyncRender]] = {}
        self._async_renders: dict[str, type[AsyncRender]] = {}

    @override
    def setup(self, collector: Collector[type, Any]) -> Result[bool, ControllerError]:
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
                    self._async_renders[key] = class_obj
                else:
                    self._sync_renders[key] = class_obj

        res = collector.add(SyncRenderFactory, SyncRenderFactoryImpl(self._sync_renders))
        res &= collector.add(AsyncRenderFactory, AsyncRenderFactoryImpl(self._async_renders))
        return Ok(res)

    @override
    def teardown(self, collector: MutCollector[type, Any]) -> Result[bool, ControllerError]:
        del self._sync_renders
        del self._async_renders
        self._sync_renders = {}
        self._async_renders = {}

        res = collector.remove(SyncRenderFactory)
        res &= collector.remove(AsyncRenderFactory)
        return Ok(res)
