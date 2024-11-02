from abc import ABC, abstractmethod
from collections.abc import Iterable

from greyhorse.error import Error, ErrorCase
from greyhorse.maybe import Maybe
from greyhorse.result import Result

from .operators import Operator
from .providers import Provider
from .visitor import Visitor


class ComponentError(Error):
    namespace = 'greyhorse.app.component'

    Resource = ErrorCase(
        msg='{path}: Resource error in component: "{name}", details: "{details}"',
        path=str,
        name=str,
        details=str,
    )
    Ctrl = ErrorCase(
        msg='{path}: Controller error in component: "{name}", details: "{details}"',
        path=str,
        name=str,
        details=str,
    )
    Service = ErrorCase(
        msg='{path}: Service error in component: "{name}", details: "{details}"',
        path=str,
        name=str,
        details=str,
    )
    Module = ErrorCase(
        msg='{path}: Submodule error in component: "{name}", details: "{details}"',
        path=str,
        name=str,
        details=str,
    )


class Component(ABC):
    __slots__ = ('_name', '_path')

    def __init__(self, name: str, path: str) -> None:
        self._name = name
        self._path = path

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> str:
        return self._path

    @abstractmethod
    def accept_visitor(self, visitor: Visitor) -> None: ...

    @abstractmethod
    def get_provider[P: Provider](self, prov_type: type[P]) -> Maybe[P]: ...

    @abstractmethod
    def get_operators[T](self, res_type: type[T]) -> Iterable[Operator[T]]: ...

    @abstractmethod
    def add_resource[T](self, res_type: type[T], resource: T) -> bool: ...

    @abstractmethod
    def remove_resource[T](self, res_type: type[T]) -> bool: ...

    @abstractmethod
    def create(self) -> Result[None, ComponentError]: ...

    @abstractmethod
    def setup(self) -> Result[None, ComponentError]: ...

    @abstractmethod
    def teardown(self) -> Result[None, ComponentError]: ...

    @abstractmethod
    def destroy(self) -> Result[None, ComponentError]: ...
