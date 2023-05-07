import contextlib
from pathlib import Path
from typing import Mapping, Optional

from dependency_injector import providers
from dependency_injector.containers import Container
from dependency_injector.wiring import Provide, inject

from . import base, module
from ..context import with_context
from ..logging import logger
from ..utils.imports import import_path
from ..utils.invoke import invoke_sync, invoke_async


class Application(base.Application, module.SessionModule, base.ContainerResource):
    def __init__(self, container: Container, name: str, debug: bool = False, version: str = '',
                 resources: Mapping[str, base.ResourceFactory] | None = None,
                 services: Mapping[str, base.ServiceFactory] | None = None,
                 modules: Mapping[str, base.ModuleFactory] | None = None):
        super().__init__(container=container, resources=resources, services=services, modules=modules)

        self._name = name
        self._version = version
        self._debug = debug
        self._path = self._inspect_cwd()

        self._imported_packages = None

        container.instance = providers.Object(self)
        container.wire(modules=[__name__])

    @property
    def name(self) -> str:
        return self._name

    @staticmethod
    def _inspect_cwd():
        import inspect
        path = Path(inspect.stack()[3].filename).absolute()
        result = None
        while path.parent != path and result is None:
            path = path.parent
            pyproject_toml_path = path / 'pyproject.toml'
            if pyproject_toml_path.exists():
                result = path
        return result

    @property
    def version(self) -> str:
        return self._version

    @property
    def debug(self) -> bool:
        return self._debug

    def get_cwd(self) -> Path:
        return self._path.absolute()

    def sync_startup(self, *args, **kwargs):
        super().sync_startup(application=self, *args, **kwargs)

    def sync_shutdown(self, *args, **kwargs):
        super().sync_shutdown(application=self, *args, **kwargs)

    async def startup(self, *args, **kwargs):
        await super().startup(application=self, *args, **kwargs)

    async def shutdown(self, *args, **kwargs):
        await super().shutdown(application=self, *args, **kwargs)

    def sync_session_begin(self, *args, **kwargs):
        super().sync_session_begin(application=self, *args, **kwargs)

    def sync_session_finish(self, *args, **kwargs):
        super().sync_session_finish(application=self, *args, **kwargs)

    async def session_begin(self, *args, **kwargs):
        await super().session_begin(application=self, *args, **kwargs)

    async def session_finish(self, *args, **kwargs):
        await super().session_finish(application=self, *args, **kwargs)

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

    def sync_load_packages(self, key, *args, **kwargs):
        if not self._imported_packages:
            self._imported_packages = self._import_packages(key)

        with self.sync_with_app_sessions():
            for name, entrypoint in self._imported_packages.items():
                logger.info(f'Application "{self.name}": load package "{name}"')
                invoke_sync(entrypoint, self, self.container, *args, **kwargs)

    async def load_packages(self, key, *args, **kwargs):
        if not self._imported_packages:
            self._imported_packages = self._import_packages(key)

        async with self.with_app_sessions():
            for name, entrypoint in self._imported_packages.items():
                logger.info(f'Application "{self.name}": load package "{name}"')
                await invoke_async(entrypoint, self, self.container, *args, **kwargs)

    @contextlib.contextmanager
    def sync_with_app_resources(self):
        with with_context(True):
            with contextlib.ExitStack() as stack:
                invoke_sync(self.startup)
                self.sync_startup()
                stack.callback(self.sync_shutdown)
                stack.callback(invoke_sync, self.shutdown)
                yield

    @contextlib.asynccontextmanager
    async def with_app_resources(self):
        with with_context(True):
            async with contextlib.AsyncExitStack() as stack:
                await self.startup()
                await invoke_async(self.sync_startup)
                stack.push_async_callback(invoke_async, self.sync_shutdown)
                stack.push_async_callback(self.shutdown)
                yield

    @contextlib.contextmanager
    def sync_with_app_sessions(self):
        with with_context(False):
            with contextlib.ExitStack() as stack:
                invoke_sync(self.session_begin)
                self.sync_session_begin()
                stack.callback(self.sync_session_finish)
                stack.callback(invoke_sync, self.session_finish)
                yield

    @contextlib.asynccontextmanager
    async def with_app_sessions(self):
        with with_context(False):
            async with contextlib.AsyncExitStack() as stack:
                await self.session_begin()
                await invoke_async(self.sync_session_begin)
                stack.push_async_callback(invoke_async, self.sync_session_finish)
                stack.push_async_callback(self.session_finish)
                yield


@inject
def current_application(_app: Application = Provide['instance']):
    return _app
