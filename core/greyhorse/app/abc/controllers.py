import inspect
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from greyhorse.error import Error, ErrorCase
from greyhorse.result import Result

from .collectors import MutNamedCollector, NamedCollector
from .visitor import Visitor


class ControllerError(Error):
    namespace = 'greyhorse.app'

    Factory = ErrorCase(msg='Controller factory error: "{details}"', details=str)
    NoSuchResource = ErrorCase(msg='Resource "{name}" is not set', name=str)


type ControllerFactoryFn = Callable[[...], Controller | Result[Controller, ControllerError]]
type ControllerFactories = dict[type[Controller], ControllerFactoryFn]


@dataclass(slots=True, frozen=True)
class OperatorMember:
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

    def accept_visitor(self, visitor: Visitor) -> None:
        visitor.visit_controller(self)

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
        self, collector: NamedCollector[type, Any]
    ) -> Result[bool, ControllerError] | Awaitable[Result[bool, ControllerError]]: ...

    @abstractmethod
    def teardown(
        self, collector: MutNamedCollector[type, Any]
    ) -> Result[bool, ControllerError] | Awaitable[Result[bool, ControllerError]]: ...
