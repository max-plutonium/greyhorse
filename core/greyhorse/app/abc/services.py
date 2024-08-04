import asyncio
import threading
from abc import ABC, abstractmethod
from typing import Awaitable, Callable

from greyhorse.enum import Enum, Unit, Tuple, Struct
from greyhorse.error import Error, ErrorCase
from greyhorse.result import Result, Ok
from .operators import Operator
from .providers import Provider
from .selectors import ListSelector


class ServiceState(Enum):
    Idle = Unit()
    Active = Struct(started=bool)


class ServiceWaiter(Enum):
    Sync = Tuple(threading.Event)
    Async = Tuple(asyncio.Event)


class ServiceError(Error):
    namespace = 'greyhorse.app'

    Unexpected = ErrorCase(msg='Service unexpected error: "{details}"', details=str)
    # Factory = ErrorCase(msg='Service factory error: "{details}"', details=str)
    Deps = ErrorCase(msg='Dependency error occurred: "{details}"', details=str)


type ServiceFactoryFn = Callable[[...], Service | Result[Service, ServiceError]]
type ServiceFactories = dict[type[Service], ServiceFactoryFn]


class ResourceProvisionError(Error):
    namespace = 'greyhorse.app'

    WrongState = ErrorCase(
        msg='Cannot create provider "{type_}" because service is in wrong state: "{state}"',
        name=str, state=str,
    )

    InsufficientDeps = ErrorCase(
        msg='Cannot create provider "{type_}" because dependencies are not enough to satisfy',
        name=str,
    )

    NoSuchProvider = ErrorCase(msg='No such provider: "{type_}"', type_=str)
    Provision = ErrorCase(msg='Provision error occurred: "{details}"', details=str)


class Service(ABC):
    def __init__(self, *args, **kwargs):
        self._state = ServiceState.Idle

    @property
    def state(self) -> ServiceState:
        return self._state

    @property
    @abstractmethod
    def waiter(self) -> ServiceWaiter:
        ...

    @abstractmethod
    def setup(
        self, selector: ListSelector[type, Operator],
    ) -> Result[ServiceState, ServiceError] | Awaitable[Result[ServiceState, ServiceError]]:
        ...

    @abstractmethod
    def teardown(
        self, selector: ListSelector[type, Operator],
    ) -> Result[ServiceState, ServiceError] | Awaitable[Result[ServiceState, ServiceError]]:
        ...

    @abstractmethod
    def can_provide(self, resource_type: type) -> bool:
        ...

    @abstractmethod
    def get_resource_types(self) -> list[type]:
        ...

    @abstractmethod
    def get_provider_types(self, resource_type: type) -> list[type[Provider]]:
        ...

    @abstractmethod
    def setup_resource[T](
        self, prov_type: type[Provider[T]], operator: Operator[T], *args, **kwargs,
    ) -> Result[bool, ResourceProvisionError]:
        ...

    @abstractmethod
    def teardown_resource[T](
        self, prov_type: type[Provider[T]], operator: Operator[T],
    ) -> Result[bool, ResourceProvisionError]:
        ...

    def _switch_to_idle(self) -> Result[ServiceState, ServiceError]:
        self._state = ServiceState.Idle
        return Ok(self._state)

    def _switch_to_active(self, started: bool = False) -> Result[ServiceState, ServiceError]:
        self._state = ServiceState.Active(started=started)
        return Ok(self._state)
