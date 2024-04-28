from pathlib import Path
from typing import override

from greyhorse.app.entities.controller import Controller
from greyhorse.app.errors import DependencyCreationFailure
from greyhorse.logging import logger
from greyhorse.result import Result
from greyhorse.utils.imports import import_path
from .abc import SyncRender, AsyncRender, SyncRenderFactory, AsyncRenderFactory

_RENDER_PACKAGES = {
    '': ('simple:SimpleSyncRender', 'simple:SimpleAsyncRender'),
    'jinja': ('jinja:JinjaSyncRender', 'jinja:JinjaAsyncRender'),
}


class SyncRenderFactoryImpl(SyncRenderFactory):
    def __init__(self, renders: dict[str, type[SyncRender]]):
        self._renders = renders

    @override
    def __call__(self, name: str, templates_dirs: list[Path]) -> SyncRender:
        if name in self._renders:
            return self._renders[name](templates_dirs)
        return self._renders[''](templates_dirs)


class AsyncRenderFactoryImpl(AsyncRenderFactory):
    def __init__(self, renders: dict[str, type[AsyncRender]]):
        self._renders = renders

    @override
    def __call__(self, name: str, templates_dirs: list[Path]) -> AsyncRender:
        if name in self._renders:
            return self._renders[name](templates_dirs)
        return self._renders[''](templates_dirs)


class RendersController(Controller):
    def __init__(self, name: str):
        super().__init__(name)
        self._sync_renders: dict[str, type[SyncRender]] = {}
        self._async_renders: dict[str, type[AsyncRender]] = {}

        self._op_factories.set(
            SyncRenderFactory, lambda: SyncRenderFactoryImpl(self._sync_renders),
        )
        self._op_factories.set(
            AsyncRenderFactory, lambda: AsyncRenderFactoryImpl(self._async_renders),
        )

    def create(self) -> Result:
        for key, class_paths in _RENDER_PACKAGES.items():
            for class_path, is_async in zip(class_paths, (False, True)):
                if not class_path:
                    continue

                try:
                    class_obj = import_path(f'..private.{class_path}', __name__)

                except (ImportError, AttributeError):
                    error = DependencyCreationFailure(
                        type='controller', name=self.name, dep_name=class_path,
                    )
                    logger.warn(error.message)
                    continue

                if is_async:
                    self._async_renders[key] = class_obj
                else:
                    self._sync_renders[key] = class_obj

        return Result.from_ok()

    def destroy(self) -> Result:
        del self._sync_renders
        del self._async_renders
        self._sync_renders = {}
        self._async_renders = {}
        return Result.from_ok()

    @property
    def active(self) -> bool:
        return len(self._sync_renders) > 0 or len(self._async_renders) > 0
