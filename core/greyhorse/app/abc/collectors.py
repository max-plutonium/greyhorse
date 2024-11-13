from abc import ABC, abstractmethod
from typing import Any

from greyhorse.utils.types import TypeWrapper


class Collector[K, T](TypeWrapper[K, T], ABC):
    @abstractmethod
    def add(self, key: K, instance: T, **metadata: dict[str, Any]) -> bool: ...


class MutCollector[K, T](Collector[K, T], ABC):
    @abstractmethod
    def remove(self, key: K, instance: T | None = None) -> bool: ...
