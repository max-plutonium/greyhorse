from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any, Literal, override

from greyhorse.maybe import Just, Maybe, Nothing
from greyhorse.utils.types import TypeWrapper


class Operator[T](TypeWrapper[T], ABC):
    @abstractmethod
    def accept(self, instance: T) -> bool | Awaitable[bool]: ...

    @abstractmethod
    def revoke(self) -> Maybe[T] | Awaitable[Maybe[T]]: ...


class AssignOperator[T](Operator[T]):
    def __init__(
        self, getter: Callable[[], Maybe[T]], setter: Callable[[Maybe[T]], Any]
    ) -> None:
        super().__init__()
        self._getter = getter
        self._setter = setter

    def _set(self, value: T) -> Literal[True]:
        self._setter(Just(value))
        return True

    def _clear(self, value: T) -> T:
        self._setter(Nothing)
        return value

    @override
    def accept(self, instance: T) -> bool:
        return self._getter().map_or_else(partial(self._set, instance), lambda _: False)

    @override
    def revoke(self) -> Maybe[T]:
        return self._getter().map(self._clear)


class AttrOperator[T](AssignOperator[T]):
    def __init__(self, instance: object, attr: str) -> None:
        if hasattr(instance, attr):
            super().__init__(partial(getattr, instance, attr), partial(setattr, instance, attr))
        else:
            raise ValueError(f'Instance {instance!r} has no attribute "{attr}"')
