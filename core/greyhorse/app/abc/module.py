from abc import ABC, abstractmethod

from greyhorse.error import Error, ErrorCase
from greyhorse.maybe import Maybe
from greyhorse.result import Result

from .operators import Operator
from .providers import Provider
from .visitor import Visitor


class ModuleError(Error):
    namespace = 'greyhorse.app.module'

    Component = ErrorCase(
        msg='{path}: Component error in module, details: "{details}"', path=str, details=str
    )

    Resource = ErrorCase(
        msg='{path}: Resource error in module: "{details}"', path=str, details=str
    )


class Module(ABC):
    __slots__ = ('_path',)

    def __init__(self, path: str) -> None:
        self._path = path

    @property
    def path(self) -> str:
        return self._path

    @abstractmethod
    def accept_visitor(self, visitor: Visitor) -> None: ...

    @abstractmethod
    def get_provider[P: Provider](self, prov_type: type[P]) -> Maybe[P]: ...

    @abstractmethod
    def add_provider[T](self, prov_type: type[Provider[T]], provider: Provider[T]) -> bool: ...

    @abstractmethod
    def remove_provider[T](self, prov_type: type[Provider[T]]) -> bool: ...

    @abstractmethod
    def add_resource[T](self, res_type: type[T], resource: T) -> bool: ...

    @abstractmethod
    def remove_resource[T](self, res_type: type[T]) -> bool: ...

    @abstractmethod
    def add_operator[T](self, operator: Operator[T]) -> bool: ...

    @abstractmethod
    def remove_operator[T](self, operator: Operator[T]) -> bool: ...

    @abstractmethod
    def create(self) -> Result[None, ModuleError]: ...

    @abstractmethod
    def setup(self) -> Result[None, ModuleError]: ...

    @abstractmethod
    def teardown(self) -> Result[None, ModuleError]: ...

    @abstractmethod
    def destroy(self) -> Result[None, ModuleError]: ...
