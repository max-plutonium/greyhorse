import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Union

from greyhorse.error import Error, ErrorCase
from greyhorse.result import Result

from ...utils.types import TypeWrapper
from .collectors import Collector, MutCollector
from .providers import Provider
from .selectors import ListSelector


class ControllerError(Error):
    namespace = 'greyhorse.app'

    Factory = ErrorCase(msg='Controller factory error: "{details}"', details=str)
    Deps = ErrorCase(msg='Dependency error occurred: "{details}"', details=str)


type ControllerFactoryFn = Callable[[...], Controller | Result[Controller, ControllerError]]
type ControllerFactories = dict[type[Controller], ControllerFactoryFn]


@dataclass(slots=True, frozen=True)
class OperatorMember:
    class_name: str
    method_name: str
    resource_type: type
    method: classmethod
    params: dict[str, type] = field(default_factory=dict)
    ret_type: type | None = None


def _is_operator_member(member: classmethod) -> bool:
    return hasattr(member, '__operator__')


class Controller(ABC):
    def __init__(self) -> None:
        self._operator_members: dict[type, OperatorMember] = {}
        self._init_operator_members()

    def _init_operator_members(self) -> None:
        operator_members = inspect.getmembers(self, _is_operator_member)

        for _, member in operator_members:
            member = member.__operator__
            self._operator_members[member.resource_type] = member

    def inspect(self, callback: Callable[[OperatorMember], Any]) -> None:
        for member in self._operator_members.values():
            callback(member)

    @abstractmethod
    def setup(
        self, providers: ListSelector[type[Provider], Provider],
    ) -> Result[bool, ControllerError] | Awaitable[Result[bool, ControllerError]]: ...

    @abstractmethod
    def teardown(
        self, providers: ListSelector[type[Provider], Provider],
    ) -> Result[bool, ControllerError] | Awaitable[Result[bool, ControllerError]]: ...


class CollectorController[K, T](TypeWrapper[K, T], ABC):
    @abstractmethod
    def setup(self, collector: Collector[K, T]) -> Union[bool, Awaitable[bool]]: ...

    @abstractmethod
    def teardown(self, collector: MutCollector[K, T]) -> Union[bool, Awaitable[bool]]: ...
