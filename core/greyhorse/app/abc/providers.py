from abc import ABC, abstractmethod
from collections.abc import Awaitable
from typing import Union

from greyhorse.error import Error, ErrorCase
from greyhorse.result import Result
from greyhorse.utils.types import TypeWrapper


class BorrowError(Error):
    namespace = 'greyhorse.app'

    Empty = ErrorCase(
        msg='Cannot borrow "{name}" as immutable because the value is empty', name=str
    )

    MovedOut = ErrorCase(
        msg='Cannot borrow "{name}" as immutable because the value was moved out', name=str
    )

    BorrowedAsMutable = ErrorCase(
        msg='Cannot borrow "{name}" as immutable because it is also borrowed as mutable',
        name=str,
    )

    Unexpected = ErrorCase(
        msg='Cannot borrow "{name}" as immutable because an unexpected error occurred: "{details}"',
        name=str,
        details=str,
    )

    InsufficientDeps = ErrorCase(
        msg='Cannot borrow "{name}" as immutable because dependencies are not enough to satisfy',
        name=str,
    )


class BorrowMutError(Error):
    namespace = 'greyhorse.app'

    Empty = ErrorCase(
        msg='Cannot borrow "{name}" as mutable because the value is empty', name=str
    )

    MovedOut = ErrorCase(
        msg='Cannot borrow "{name}" as mutable because the value was moved out', name=str
    )

    AlreadyBorrowed = ErrorCase(
        msg='Cannot borrow "{name}" as mutable more than once at a time', name=str
    )

    BorrowedAsImmutable = ErrorCase(
        msg='Cannot borrow "{name}" as mutable because it is also borrowed as immutable',
        name=str,
    )

    Unexpected = ErrorCase(
        msg='Cannot borrow "{name}" as mutable because an unexpected error occurred: "{details}"',
        name=str,
        details=str,
    )

    InsufficientDeps = ErrorCase(
        msg='Cannot borrow "{name}" as mutable because dependencies are not enough to satisfy',
        name=str,
    )


class FactoryError(Error):
    namespace = 'greyhorse.app'

    Unexpected = ErrorCase(
        msg='Cannot construct "{name}" because an unexpected error occurred: "{details}"',
        name=str,
        details=str,
    )

    InsufficientDeps = ErrorCase(
        msg='Cannot construct "{name}" because dependencies are not enough to satisfy', name=str
    )


class ForwardError(Error):
    namespace = 'greyhorse.app'

    Empty = ErrorCase(msg='Cannot forward "{name}" because the value is empty', name=str)

    MovedOut = ErrorCase(
        msg='Cannot forward "{name}" because the value was moved out', name=str
    )

    Unexpected = ErrorCase(
        msg='Cannot forward "{name}" because an unexpected error occurred: "{details}"',
        name=str,
        details=str,
    )

    InsufficientDeps = ErrorCase(
        msg='Cannot forward "{name}" because dependencies are not enough to satisfy', name=str
    )


class Provider[T](TypeWrapper[T]): ...


class SharedProvider[T](Provider[T], ABC):
    @abstractmethod
    def borrow(self) -> Result[T, BorrowError] | Awaitable[Result[T, BorrowError]]: ...

    @abstractmethod
    def reclaim(self, instance: T) -> None | Awaitable[None]: ...


class MutProvider[T](Provider[T], ABC):
    @abstractmethod
    def acquire(self) -> Result[T, BorrowMutError] | Awaitable[Result[T, BorrowMutError]]: ...

    @abstractmethod
    def release(self, instance: T) -> None | Awaitable[None]: ...


class FactoryProvider[T](Provider[T], ABC):
    @abstractmethod
    def create(self) -> Result[T, FactoryError] | Awaitable[Result[T, FactoryError]]: ...

    @abstractmethod
    def destroy(self, instance: T) -> None | Awaitable[None]: ...


class ForwardProvider[T](Provider[T], ABC):
    @abstractmethod
    def take(self) -> Result[T, ForwardError] | Awaitable[Result[T, ForwardError]]: ...

    @abstractmethod
    def drop(self, instance: T) -> None | Awaitable[None]: ...

    @abstractmethod
    def __bool__(self) -> bool | Awaitable[bool]: ...


AnyProvider = Union[SharedProvider, MutProvider, FactoryProvider, ForwardProvider]
