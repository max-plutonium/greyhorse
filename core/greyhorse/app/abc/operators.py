from abc import ABC, abstractmethod
from abc import ABC, abstractmethod
from functools import partial
from typing import Awaitable, override, Union, Any, Literal, Callable

from greyhorse.app.context import SyncContext, AsyncContext, SyncMutContext, AsyncMutContext
from greyhorse.maybe import Maybe, Just, Nothing
from greyhorse.utils.types import TypeWrapper


class Operator[T](TypeWrapper[T], ABC):
    @abstractmethod
    def accept(self, instance: T) -> Union[bool, Awaitable[bool]]:
        ...

    @abstractmethod
    def revoke(self) -> Maybe[T] | Awaitable[Maybe[T]]:
        ...


class ContextOperator[T](Operator, ABC):
    def __class_getitem__[C: SyncContext | AsyncContext](cls, args: tuple[type[C], type[T]]):
        class_, type_ = args
        return super(ContextOperator, cls).__class_getitem__(class_[type_])


class MutContextOperator[T](Operator, ABC):
    def __class_getitem__[C: SyncMutContext | AsyncMutContext](cls, args: tuple[type[C], type[T]]):
        class_, type_ = args
        return super(MutContextOperator, cls).__class_getitem__(class_[type_])


class AssignOperator[T](Operator[T]):
    def __init__(self, getter: Callable[[], Maybe[T]], setter: Callable[[Maybe[T]], Any]):
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
    def __init__(self, instance: object, attr: str):
        if hasattr(instance, attr):
            super().__init__(partial(getattr, instance, attr), partial(setattr, instance, attr))
        else:
            raise ValueError(f'Instance {repr(instance)} has no attribute {attr}')
