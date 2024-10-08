from abc import ABC, abstractmethod

from greyhorse.app.abc.providers import ForwardProvider
from greyhorse.result import Result


class FunctionalOperator(ABC):
    @abstractmethod
    def add_number(self, value: int) -> Result[None, str]: ...

    @abstractmethod
    def get_number(self) -> Result[int, str]: ...

    @abstractmethod
    def remove_number(self) -> Result[bool, str]: ...


FunctionalOpProvider = ForwardProvider[FunctionalOperator]
