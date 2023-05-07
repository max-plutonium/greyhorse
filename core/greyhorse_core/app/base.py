from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, List, Optional, Protocol, runtime_checkable, Self

from dependency_injector.containers import Container


@runtime_checkable
class BaseResource(Protocol):
    pass


class Resource(BaseResource):
    def __init__(self, *args, **kwargs):
        self._initialized: bool = False

    @property
    def initialized(self) -> bool:
        return self._initialized

    def sync_startup(self, application, module, service, *args, **kwargs):
        pass

    def sync_shutdown(self, application, module, service, *args, **kwargs):
        pass

    async def startup(self, application, module, service, *args, **kwargs):
        pass

    async def shutdown(self, application, module, service, *args, **kwargs):
        pass


class SessionResource(Resource):
    def sync_session_begin(self, application, module, service, *args, **kwargs):
        pass

    def sync_session_finish(self, application, module, service, *args, **kwargs):
        pass

    async def session_begin(self, application, module, service, *args, **kwargs):
        pass

    async def session_finish(self, application, module, service, *args, **kwargs):
        pass


ResourceFactory = Callable[[], Resource]


class ContainerResource(Resource):
    def __init__(self, container: Container, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._container = container

    @property
    def container(self) -> Container:
        return self._container


class Service(Resource, ABC):
    name: str
    resources: list[Resource]

    @abstractmethod
    def get_resource(self, name) -> Resource | None:
        ...


ServiceFactory = Callable[[], Service]


class Module(Resource, ABC):
    resources: list[Resource]
    services: list[Service]
    modules: list['Module']

    @abstractmethod
    def get_resource(self, name) -> Resource | None:
        ...

    @abstractmethod
    def get_service(self, name) -> Service | None:
        ...

    @abstractmethod
    def get_module(self, name) -> Self | None:
        ...


ModuleFactory = Callable[[], Module]


class Application(Module, ABC):
    name: str

    @property
    @abstractmethod
    def version(self) -> str:
        ...

    @property
    @abstractmethod
    def debug(self) -> bool:
        ...

    @abstractmethod
    def get_cwd(self) -> Path:
        ...

    @abstractmethod
    def sync_load_packages(self, *args, **kwargs):
        ...

    @abstractmethod
    async def load_packages(self, *args, **kwargs):
        ...
