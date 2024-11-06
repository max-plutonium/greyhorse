import asyncio
import inspect
import threading
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from greyhorse.enum import Enum, Struct, Tuple, Unit
from greyhorse.error import Error, ErrorCase
from greyhorse.result import Result

from .resources import Lifetime, TypeFactoryFn
from .visitor import Visitor


class ServiceState(Enum):
    Idle = Unit()
    Active = Struct(started=bool)


class ServiceWaiter(Enum):
    Sync = Tuple(threading.Event)
    Async = Tuple(asyncio.Event)


class ServiceError(Error):
    namespace = 'greyhorse.app'

    Factory = ErrorCase(msg='Service factory error: "{details}"', details=str)
    NoSuchResource = ErrorCase(msg='Resource "{name}" is not found', name=str)


type ServiceFactoryFn = Callable[[...], Service | Result[Service, ServiceError]]
type ServiceFactories = dict[type[Service], ServiceFactoryFn]


@dataclass(slots=True, frozen=True)
class ResourceMember:
    resource_type: type
    lifetime: Lifetime
    cache: bool
    method: classmethod
    params: dict[str, type] = field(default_factory=dict)


def _is_resource_member(member: classmethod) -> bool:
    return hasattr(member, '__res_provider__')


class Service(ABC):
    def __init__(self) -> None:
        self._state = ServiceState.Idle
        self._resources: dict[type, TypeFactoryFn] = {}
        self._resource_members: dict[type, ResourceMember] = {}
        self._init_members()

    def accept_visitor(self, visitor: Visitor) -> None:
        visitor.visit_service(self)

    def _init_members(self) -> None:
        resource_members = inspect.getmembers(self, _is_resource_member)

        for _, member in resource_members:
            member = member.__res_provider__
            self._resources[member.resource_type] = member.method
            self._resource_members[member.resource_type] = member

    def inspect(self, callback: Callable[[ResourceMember], Any]) -> None:
        for member in self._resource_members.values():
            callback(member)

    @property
    def state(self) -> ServiceState:
        return self._state

    @property
    @abstractmethod
    def waiter(self) -> ServiceWaiter: ...

    @abstractmethod
    def setup(
        self,
        *args,  # noqa: ANN002
        **kwargs,  # noqa: ANN003
    ) -> Result[ServiceState, ServiceError] | Awaitable[Result[ServiceState, ServiceError]]: ...

    @abstractmethod
    def teardown(
        self,
        *args,  # noqa: ANN002
        **kwargs,  # noqa: ANN003
    ) -> Result[ServiceState, ServiceError] | Awaitable[Result[ServiceState, ServiceError]]: ...

    def _switch_to_idle(self) -> None:
        self._state = ServiceState.Idle

    def _switch_to_active(self, started: bool = False) -> None:
        self._state = ServiceState.Active(started=started)
