from abc import ABC, abstractmethod
from typing import overload

from greyhorse.maybe import Maybe


class Selector[T](ABC):
    @overload
    def has(self, **keys) -> bool:
        ...

    @overload
    def has(self, class_: type[T], **keys) -> bool:
        ...

    @abstractmethod
    def has(self, class_: type[T] | None = None, **keys) -> bool:
        ...

    @overload
    def get(self, **keys) -> Maybe[T]:
        ...

    @overload
    def get(self, class_: type[T], **keys) -> Maybe[T]:
        ...

    @abstractmethod
    def get(self, class_: type[T] | None = None, **keys) -> Maybe[T]:
        ...
