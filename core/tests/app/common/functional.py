from abc import ABC, abstractmethod

from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import FactoryProvider
from greyhorse.app.contexts import SyncContext, SyncMutContext
from greyhorse.result import Result
from .resources import DictResource


class FunctionalOperator(ABC):
    @abstractmethod
    def add_number(self, value: int) -> Result[None, str]:
        ...

    @abstractmethod
    def get_number(self) -> Result[int, str]:
        ...

    @abstractmethod
    def remove_number(self) -> Result[bool, str]:
        ...


FunctionalOpProvider = FactoryProvider[FunctionalOperator]

DictCtxOperator = Operator[SyncContext[DictResource]]
DictMutCtxOperator = Operator[SyncMutContext[DictResource]]
