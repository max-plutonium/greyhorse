from abc import ABC, abstractmethod


class Collector[K, T](ABC):
    @abstractmethod
    def add(self, key: K, instance: T) -> bool:
        ...


class MutCollector[K, T](Collector[K, T], ABC):
    @abstractmethod
    def remove(self, key: K, instance: T) -> bool:
        ...
