import contextlib
from abc import ABC
from pathlib import Path
from typing import Mapping

from dependency_injector import providers
from dependency_injector.containers import Container
from dependency_injector.wiring import Provide, inject

from . import base, module
from .visitors import StartVisitor, StopVisitor, BindVisitor, AcquireVisitor, ReleaseVisitor
from ..logging import logger
from ..utils.imports import import_path
from ..utils.invoke import invoke_sync, invoke_async


class Application(module.Module, base.Application, base.HasContainer, ABC):
    def __init__(
        self, container: Container, name: str, debug: bool = False, version: str = '',
        resources: Mapping[str, base.ResourceFactory] | None = None,
        services: Mapping[str, base.ServiceFactory] | None = None,
        modules: Mapping[str, base.ModuleFactory] | None = None,
    ):
        module.Module.__init__(self, name, resources, services, modules)
        base.Application.__init__(self, name)
        base.HasContainer.__init__(self, container)

        self._version = version
        self._debug = debug
        self._path = self._inspect_cwd()

        self._imported_packages = None

        container.instance = providers.Object(self)
        container.wire(modules=[__name__])

    @staticmethod
    def _inspect_cwd():
        import inspect

        for frame in reversed(inspect.stack()):
            path = Path(frame.filename).absolute()

            while path.parent != path:
                path = path.parent
                pyproject_toml_path = path / 'pyproject.toml'
                if pyproject_toml_path.exists():
                    return path

    @property
    def version(self) -> str:
        return self._version

    @property
    def debug(self) -> bool:
        return self._debug

    def get_cwd(self) -> Path:
        return self._path.absolute()

    def _import_packages(self, key: str | None = None):
        from tomlkit import parse

        packages, result = dict(), dict()
        pyproject_toml_path = self.get_cwd() / 'pyproject.toml'

        if pyproject_toml_path.exists():
            with open(str(pyproject_toml_path)) as f:
                pyproject_toml = parse(string=f.read())

            if project := pyproject_toml.get('project'):
                if key:
                    if section := project.get(key):
                        packages = section.get('packages', dict())
                else:
                    packages = project.get('packages', dict())

        key = key or 'package'

        for name, dotted_path in packages.items():
            logger.info(f'Import package: "{name}"')
            dotted_path = dotted_path if ':' in dotted_path else f'{dotted_path}:{key}_init'

            if entrypoint := import_path(dotted_path):
                result[name] = entrypoint

        return result


class SyncApplication(Application):
    def initialize(self, *args, **kwargs):
        invoke_sync(self.accept(BindVisitor()))
        visitor = StartVisitor(self)

        for r in self.resources:
            invoke_sync(r.accept(visitor))
        for s in self.services:
            invoke_sync(s.accept(visitor))
        for m in self.modules:
            invoke_sync(m.accept(visitor))

    def finalize(self, *args, **kwargs):
        visitor = StopVisitor(self)

        for m in self.modules:
            invoke_sync(m.accept(visitor))
        for s in self.services:
            invoke_sync(s.accept(visitor))
        for r in self.resources:
            invoke_sync(r.accept(visitor))

    def _begin(self):
        visitor = AcquireVisitor(self)

        for r in self.resources:
            invoke_sync(r.accept(visitor))
        for s in self.services:
            invoke_sync(s.accept(visitor))
        for m in self.modules:
            invoke_sync(m.accept(visitor))

    def _end(self):
        visitor = ReleaseVisitor(self)

        for m in self.modules:
            invoke_sync(m.accept(visitor))
        for s in self.services:
            invoke_sync(s.accept(visitor))
        for r in self.resources:
            invoke_sync(r.accept(visitor))

    @contextlib.contextmanager
    def session(self) -> contextlib.AbstractContextManager:
        with contextlib.ExitStack() as stack:
            self._begin()
            stack.callback(self._end)
            yield

    def load_packages(self, key, *args, **kwargs):
        if not self._imported_packages:
            self._imported_packages = self._import_packages(key)

        with self.session():
            for name, entrypoint in self._imported_packages.items():
                logger.info(f'Application "{self.name}": load package "{name}"')
                invoke_sync(entrypoint, self, self.container, *args, **kwargs)


class AsyncApplication(Application):
    async def initialize(self, *args, **kwargs):
        await invoke_async(self.accept(BindVisitor()))
        visitor = StartVisitor(self)

        for r in self.resources:
            await invoke_async(r.accept(visitor))
        for s in self.services:
            await invoke_async(s.accept(visitor))
        for m in self.modules:
            await invoke_async(m.accept(visitor))

    async def finalize(self, *args, **kwargs):
        visitor = StopVisitor(self)

        for m in self.modules:
            await invoke_async(m.accept(visitor))
        for s in self.services:
            await invoke_async(s.accept(visitor))
        for r in self.resources:
            await invoke_async(r.accept(visitor))

    async def _begin(self):
        visitor = AcquireVisitor(self)

        for r in self.resources:
            await invoke_async(r.accept(visitor))
        for s in self.services:
            await invoke_async(s.accept(visitor))
        for m in self.modules:
            await invoke_async(m.accept(visitor))

    async def _end(self):
        visitor = ReleaseVisitor(self)

        for m in self.modules:
            await invoke_async(m.accept(visitor))
        for s in self.services:
            await invoke_async(s.accept(visitor))
        for r in self.resources:
            await invoke_async(r.accept(visitor))

    @contextlib.asynccontextmanager
    async def session(self) -> contextlib.AbstractAsyncContextManager:
        async with contextlib.AsyncExitStack() as stack:
            await self._begin()
            stack.push_async_callback(self._end)
            yield

    async def load_packages(self, key, *args, **kwargs):
        if not self._imported_packages:
            self._imported_packages = self._import_packages(key)

        async with self.session():
            for name, entrypoint in self._imported_packages.items():
                logger.info(f'Application "{self.name}": load package "{name}"')
                await invoke_async(entrypoint, self, self.container, *args, **kwargs)


@inject
def current_application(_app: Application = Provide['instance']):
    return _app
