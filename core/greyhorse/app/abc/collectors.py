from abc import ABC, abstractmethod
from typing import overload

from greyhorse.maybe import Maybe
from greyhorse.utils.types import TypeWrapper


class Collector[T](TypeWrapper[T], ABC):
    @overload
    def add(self, instance: T, **keys) -> bool:
        ...

    @overload
    def add(self, instance: T, class_: type[T], **keys) -> bool:
        ...

    @overload
    def add(self, instance: T, classes: list[type[T]], **keys) -> bool:
        ...

    @abstractmethod
    def add(
        self, instance: T, class_: type[T] | None = None,
        classes: list[type[T]] | None = None, **keys,
    ) -> bool:
        ...


class MutCollector[T](Collector[T], ABC):
    @overload
    def remove(self, **keys) -> Maybe[T]:
        ...

    @overload
    def remove(self, class_: type[T], **keys) -> Maybe[T]:
        ...

    @overload
    def remove(self, classes: list[type[T]], **keys) -> Maybe[T]:
        ...

    @abstractmethod
    def remove(
        self, class_: type[T] | None = None, classes: list[type[T]] | None = None, **keys,
    ) -> Maybe[T]:
        ...
