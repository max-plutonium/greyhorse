from abc import ABC, abstractmethod
from contextlib import AbstractContextManager, AbstractAsyncContextManager
from pathlib import Path
from typing import Callable, Optional, Self

from dependency_injector.containers import Container


class Resource(ABC):
    def __init__(self):
        self._active: bool = False

    def accept(self, visitor: 'Visitor'):
        return visitor.visit_resource(self)

    @property
    def active(self) -> bool:
        return self._active

    @abstractmethod
    def create(
        self, application: 'Application',
        module: Optional['Module'] = None,
        service: Optional['Service'] = None,
    ):
        pass

    @abstractmethod
    def destroy(
        self, application: 'Application',
        module: Optional['Module'] = None,
        service: Optional['Service'] = None,
    ):
        pass

    @abstractmethod
    def acquire(
        self, application: 'Application',
        module: Optional['Module'] = None,
        service: Optional['Service'] = None,
    ):
        pass

    @abstractmethod
    def release(
        self, application: 'Application',
        module: Optional['Module'] = None,
        service: Optional['Service'] = None,
    ):
        pass


ResourceFactory = Callable[[], Resource]


class HasContainer:
    def __init__(self, container: Container):
        self._container = container

    @property
    def container(self) -> Container:
        return self._container


class Service(ABC):
    resources: list[Resource]

    def __init__(self):
        self._active: bool = False

    def accept(self, visitor: 'Visitor'):
        return visitor.visit_service(self)

    @property
    def active(self) -> bool:
        return self._active

    @abstractmethod
    def get_resource(self, name) -> Resource | None:
        ...

    @abstractmethod
    def start(self, application: 'Application', module: Optional['Module'] = None):
        ...

    @abstractmethod
    def stop(self, application: 'Application', module: Optional['Module'] = None):
        ...


ServiceFactory = Callable[[], Service]


class Module(ABC):
    resources: list[Resource]
    services: list[Service]
    modules: list['Module']

    def __init__(self, name: str):
        self._name = name

    def accept(self, visitor: 'Visitor'):
        return visitor.visit_module(self)

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def get_resource(self, name) -> Resource | None:
        ...

    @abstractmethod
    def get_service(self, name) -> Service | None:
        ...

    @abstractmethod
    def get_module(self, name) -> Self | None:
        ...

    @abstractmethod
    def initialize(self, application: 'Application', module: Optional['Module'] = None):
        ...

    @abstractmethod
    def finalize(self, application: 'Application', module: Optional['Module'] = None):
        ...


ModuleFactory = Callable[[], Module]


class Application(Module, ABC):
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
    def initialize(self, *args, **kwargs):
        ...

    @abstractmethod
    def finalize(self, *args, **kwargs):
        ...

    @abstractmethod
    def session(self) -> AbstractContextManager | AbstractAsyncContextManager:
        ...

    @abstractmethod
    def load_packages(self, *args, **kwargs):
        ...


class Visitor:
    def visit_resource(self, instance: Resource):
        pass

    def visit_service(self, instance: Service):
        pass

    def visit_module(self, instance: Module):
        pass
