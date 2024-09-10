from abc import ABC, abstractmethod
from typing import Callable

from greyhorse.maybe import Maybe
from greyhorse.utils.types import TypeWrapper


class Selector[K, T](TypeWrapper[K, T], ABC):
    @abstractmethod
    def has(self, key: K) -> bool: ...

    @abstractmethod
    def get(self, key: K) -> Maybe[T]: ...


class ListSelector[K, T](Selector[K, T], ABC):
    @abstractmethod
    def items(self, filter_fn: Callable[[K], bool] | None = None) -> list[tuple[K, T]]: ...
