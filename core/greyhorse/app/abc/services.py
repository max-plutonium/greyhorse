import asyncio
import threading
from abc import ABC, abstractmethod
from typing import Awaitable, Callable

from greyhorse.enum import Enum, Unit, Tuple, Struct
from greyhorse.error import Error, ErrorCase
from greyhorse.result import Result, Ok
from .collectors import Collector, MutCollector
from .operators import Operator
from .providers import Provider


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


type ServiceFactoryFn = Callable[[...], Result[Service, ServiceError]]
type ServiceFactories = dict[type[Service], ServiceFactoryFn]


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
        self, providers: Collector[Provider], operators: Collector[Operator],
    ) -> Result[ServiceState, ServiceError] | Awaitable[Result[ServiceState, ServiceError]]:
        ...

    @abstractmethod
    def teardown(
        self, providers: MutCollector[Provider], operators: MutCollector[Operator],
    ) -> Result[ServiceState, ServiceError] | Awaitable[Result[ServiceState, ServiceError]]:
        ...

    def _switch_to_idle(self) -> Result[ServiceState, ServiceError]:
        self._state = ServiceState.Idle
        return Ok(self._state)

    def _switch_to_active(self, started: bool = False) -> Result[ServiceState, ServiceError]:
        self._state = ServiceState.Active(started=started)
        return Ok(self._state)
