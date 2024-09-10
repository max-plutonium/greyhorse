from abc import ABC, abstractmethod

from greyhorse.utils.types import TypeWrapper


class Collector[K, T](TypeWrapper[K, T], ABC):
    @abstractmethod
    def add(self, key: K, instance: T) -> bool: ...


class MutCollector[K, T](Collector[K, T], ABC):
    @abstractmethod
    def remove(self, key: K, instance: T | None = None) -> bool: ...
