from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from typing import Any

from greyhorse.maybe import Maybe
from greyhorse.utils.types import TypeWrapper


class Selector[K, T](TypeWrapper[K, T], ABC):
    @abstractmethod
    def has(self, key: K) -> bool: ...

    @abstractmethod
    def get(self, key: K) -> Maybe[T]: ...

    @abstractmethod
    def get_with_metadata(self, key: K) -> Maybe[tuple[T, dict[str, Any]]]: ...


class ListSelector[K, T](Selector[K, T], ABC):
    @abstractmethod
    def list(self, key: K | None = None) -> Iterable[tuple[K, T] | T]: ...

    @abstractmethod
    def list_with_metadata(
        self, key: K | None = None
    ) -> Iterable[tuple[K, T, dict[str, Any]]]: ...

    @abstractmethod
    def filter(
        self, filter_fn: Callable[[K, dict[str, Any]], bool] | None = None
    ) -> Iterable[tuple[K, T, dict[str, Any]]]: ...
