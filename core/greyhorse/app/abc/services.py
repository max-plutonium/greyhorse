import asyncio
import inspect
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from greyhorse.enum import Enum, Struct, Tuple, Unit
from greyhorse.error import Error, ErrorCase
from greyhorse.result import Result

from .providers import Provider
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
class ProviderMember:
    resource_type: type
    provider_type: type[Provider]
    method: classmethod
    params: dict[str, type] = field(default_factory=dict)
    ret_type: type | None = None


def _is_provider_member(member: classmethod) -> bool:
    return hasattr(member, '__provider__')


class Service(ABC):
    def __init__(self) -> None:
        self._state = ServiceState.Idle
        self._providers: dict[type, list[type[Provider]]] = defaultdict(list)
        self._provider_members: dict[type[Provider], ProviderMember] = {}
        self._init_provider_members()

    def accept_visitor(self, visitor: Visitor) -> None:
        visitor.visit_service(self)

    def _init_provider_members(self) -> None:
        provider_members = inspect.getmembers(self, _is_provider_member)

        for _, member in provider_members:
            member = member.__provider__
            self._providers[member.resource_type].append(member.provider_type)
            self._provider_members[member.provider_type] = member

    def inspect(self, callback: Callable[[ProviderMember], Any]) -> None:
        for member in self._provider_members.values():
            callback(member)

    @property
    def state(self) -> ServiceState:
        return self._state

    @property
    @abstractmethod
    def waiter(self) -> ServiceWaiter: ...

    @abstractmethod
    def setup(
        self, *args, **kwargs
    ) -> Result[ServiceState, ServiceError] | Awaitable[Result[ServiceState, ServiceError]]: ...

    @abstractmethod
    def teardown(
        self, *args, **kwargs
    ) -> Result[ServiceState, ServiceError] | Awaitable[Result[ServiceState, ServiceError]]: ...

    def can_provide(self, resource_type: type) -> bool:
        if resource_type not in self._providers:
            return False
        return len(self._providers[resource_type]) > 0

    def get_resource_types(self) -> list[type]:
        return list(self._providers.keys())

    def get_provider_types(self, resource_type: type) -> list[type[Provider]]:
        if resource_type not in self._providers:
            return []
        return self._providers[resource_type].copy()

    def _switch_to_idle(self) -> None:
        self._state = ServiceState.Idle

    def _switch_to_active(self, started: bool = False) -> None:
        self._state = ServiceState.Active(started=started)
