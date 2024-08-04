from abc import ABC, abstractmethod
from typing import Awaitable, Callable

from greyhorse.error import Error, ErrorCase
from greyhorse.result import Result
from .collectors import Collector, MutCollector
from .operators import Operator


class ControllerError(Error):
    namespace = 'greyhorse.app'

    Unexpected = ErrorCase(msg='Controller unexpected error: "{details}"', details=str)
    Deps = ErrorCase(msg='Dependency error occurred: "{details}"', details=str)


type ControllerFactoryFn = Callable[[...], Controller | Result[Controller, ControllerError]]
type ControllerFactories = dict[type[Controller], ControllerFactoryFn]


class Controller(ABC):
    @abstractmethod
    def setup(
        self, collector: Collector[type, Operator],
    ) -> Result[bool, ControllerError] | Awaitable[Result[bool, ControllerError]]:
        ...

    @abstractmethod
    def teardown(
        self, collector: MutCollector[type, Operator],
    ) -> Result[bool, ControllerError] | Awaitable[Result[bool, ControllerError]]:
        ...