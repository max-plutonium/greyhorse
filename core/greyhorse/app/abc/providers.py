from abc import ABC, abstractmethod
from typing import Awaitable, Union

from greyhorse.error import Error, ErrorCase
from greyhorse.result import Result
from greyhorse.utils.types import TypeWrapper


class BorrowError(Error):
    namespace = 'greyhorse.app'

    Empty = ErrorCase(
        msg='Cannot borrow "{name}" as immutable because the value is empty', name=str,
    )

    MovedOut = ErrorCase(
        msg='Cannot borrow "{name}" as immutable because the value was moved out', name=str,
    )

    BorrowedAsMutable = ErrorCase(
        msg='Cannot borrow "{name}" as immutable because it is also borrowed as mutable',
        name=str,
    )


class BorrowMutError(Error):
    namespace = 'greyhorse.app'

    Empty = ErrorCase(
        msg='Cannot borrow "{name}" as mutable because the value is empty', name=str,
    )

    MovedOut = ErrorCase(
        msg='Cannot borrow "{name}" as mutable because the value was moved out', name=str,
    )

    AlreadyBorrowed = ErrorCase(
        msg='Cannot borrow "{name}" as mutable more than once at a time', name=str,
    )

    BorrowedAsImmutable = ErrorCase(
        msg='Cannot borrow "{name}" as mutable because it is also borrowed as immutable',
        name=str,
    )


class FactoryError(Error):
    namespace = 'greyhorse.app'

    Internal = ErrorCase(
        msg='Cannot construct "{name}" because an internal error occurred: "{details}"',
        name=str,
        details=str,
    )


class ForwardError(Error):
    namespace = 'greyhorse.app'

    Empty = ErrorCase(msg='Cannot forward "{name}" because the value is empty', name=str)

    MovedOut = ErrorCase(
        msg='Cannot forward "{name}" because the value was moved out', name=str,
    )


class Provider[T](TypeWrapper[T]): ...


class SharedProvider[T](Provider[T], ABC):
    @abstractmethod
    def borrow(self) -> Result[T, BorrowError] | Awaitable[Result[T, BorrowError]]: ...

    @abstractmethod
    def reclaim(self, instance: T) -> Union[None, Awaitable[None]]: ...


class MutProvider[T](Provider[T], ABC):
    @abstractmethod
    def acquire(self) -> Result[T, BorrowMutError] | Awaitable[Result[T, BorrowMutError]]: ...

    @abstractmethod
    def release(self, instance: T) -> Union[None, Awaitable[None]]: ...


class FactoryProvider[T](Provider[T], ABC):
    @abstractmethod
    def create(self) -> Result[T, FactoryError] | Awaitable[Result[T, FactoryError]]: ...

    @abstractmethod
    def destroy(self, instance: T) -> Union[None, Awaitable[None]]: ...


class ForwardProvider[T](Provider[T], ABC):
    @abstractmethod
    def take(self) -> Result[T, ForwardError] | Awaitable[Result[T, ForwardError]]: ...

    @abstractmethod
    def drop(self, instance: T) -> Union[None, Awaitable[None]]: ...

    @abstractmethod
    def __bool__(self) -> Union[bool, Awaitable[bool]]: ...


AnyProvider = Union[SharedProvider, MutProvider, FactoryProvider, ForwardProvider]
