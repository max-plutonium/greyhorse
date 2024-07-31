from abc import ABC, abstractmethod
from typing import Awaitable, Union

from greyhorse.app.context import SyncContext, AsyncContext, SyncMutContext, AsyncMutContext
from greyhorse.error import Error, ErrorCase
from greyhorse.maybe import Maybe
from greyhorse.result import Result
from greyhorse.utils.types import TypeWrapper


class BorrowError(Error):
    namespace = 'greyhorse.app'

    Empty = ErrorCase(
        msg='Cannot borrow "{name}" as immutable because the value is empty',
        name=str,
    )

    MovedOut = ErrorCase(
        msg='Cannot borrow "{name}" as immutable because the value was moved out',
        name=str,
    )

    BorrowedAsMutable = ErrorCase(
        msg='Cannot borrow "{name}" as immutable because it is also borrowed as mutable',
        name=str,
    )


class BorrowMutError(Error):
    namespace = 'greyhorse.app'

    Empty = ErrorCase(
        msg='Cannot borrow "{name}" as mutable because the value is empty',
        name=str,
    )

    MovedOut = ErrorCase(
        msg='Cannot borrow "{name}" as mutable because the value was moved out',
        name=str,
    )

    AlreadyBorrowed = ErrorCase(
        msg='Cannot borrow "{name}" as mutable more than once at a time',
        name=str,
    )

    BorrowedAsImmutable = ErrorCase(
        msg='Cannot borrow "{name}" as mutable because it is also borrowed as immutable',
        name=str,
    )


class FactoryError(Error):
    namespace = 'greyhorse.app'

    Internal = ErrorCase(
        msg='Cannot construct "{name}" because an internal error occurred: "{details}"',
        name=str, details=str,
    )


class Provider[T](TypeWrapper[T]):
    ...


class SharedProvider[T](Provider[T], ABC):
    @abstractmethod
    def borrow(self) -> Result[T, BorrowError] | Awaitable[Result[T, BorrowError]]:
        ...

    @abstractmethod
    def reclaim(self, instance: T) -> Union[None, Awaitable[None]]:
        ...


class MutProvider[T](Provider[T], ABC):
    @abstractmethod
    def acquire(self) -> Result[T, BorrowMutError] | Awaitable[Result[T, BorrowMutError]]:
        ...

    @abstractmethod
    def release(self, instance: T) -> Union[None, Awaitable[None]]:
        ...


class ContextProvider[T](SharedProvider, ABC):
    def __class_getitem__[C: SyncContext | AsyncContext](cls, args: tuple[type[C], type[T]]):
        class_, type_ = args
        return super(ContextProvider, cls).__class_getitem__(class_[type_])


class MutContextProvider[T](MutProvider, ABC):
    def __class_getitem__[C: SyncMutContext | AsyncMutContext](cls, args: tuple[type[C], type[T]]):
        class_, type_ = args
        return super(MutContextProvider, cls).__class_getitem__(class_[type_])


class FactoryProvider[T](Provider[T], ABC):
    @abstractmethod
    def create(self) -> Result[T, FactoryError] | Awaitable[Result[T, FactoryError]]:
        ...

    @abstractmethod
    def destroy(self, instance: T) -> Union[None, Awaitable[None]]:
        ...


class ForwardProvider[T](ABC):
    @abstractmethod
    def take(self) -> Maybe[T] | Awaitable[Maybe[T]]:
        ...

    @abstractmethod
    def drop(self, instance: T) -> Union[None, Awaitable[None]]:
        ...

    @abstractmethod
    def __bool__(self) -> Union[bool, Awaitable[bool]]:
        ...


AnyProvider = Union[FactoryProvider, ForwardProvider, ContextProvider, MutContextProvider]
AnyComponentProvider = Union[ContextProvider, MutContextProvider]