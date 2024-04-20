from abc import ABC, abstractmethod
from typing import Any

from .operator import OperatorFactoryFn, OperatorKey
from .providers import ProviderFactoryFn, ProviderKey


class DepsProvider(ABC):
    @abstractmethod
    def get_operator_factory(
        self, key: OperatorKey, name: str | None = None,
    ) -> OperatorFactoryFn | None:
        ...

    @abstractmethod
    def get_provider_factory(
        self, key: ProviderKey, name: str | None = None,
    ) -> ProviderFactoryFn | None:
        ...

    @abstractmethod
    def get_resource(
        self, key: Any, name: str | None = None,
    ) -> Any | None:
        ...


class DepsOperator(ABC):

    @abstractmethod
    def set_resource(
        self, key: Any, instance: Any, name: str | None = None,
    ) -> bool:
        ...

    @abstractmethod
    def reset_resource(
        self, key: Any, name: str | None = None,
    ) -> bool:
        ...
