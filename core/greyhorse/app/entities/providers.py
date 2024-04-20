import enum
from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager, AbstractContextManager, asynccontextmanager, contextmanager
from typing import Callable

from greyhorse.result import Result
from ..context import AsyncContext, SyncContext
from ..utils.registry import ReadonlyRegistry

type ProviderKey = type[Provider]
type ProviderFactoryFn = Callable[[], Provider]
type ProviderFactoryRegistry = ReadonlyRegistry[ProviderKey, ProviderFactoryFn]


class BorrowType(str, enum.Enum):
    CONTEXT = 'context'
    SESSION = 'session'
    EXCLUSIVE = 'exclusive'
    SHARED = 'shared'


class Provider:
    type: BorrowType


class SyncContextProvider[T](Provider):
    type = BorrowType.CONTEXT

    def __init__(self, instance: SyncContext[T]):
        self._instance = instance

    def get(self) -> SyncContext[T]:
        return self._instance


class AsyncContextProvider[T](Provider):
    type = BorrowType.CONTEXT

    def __init__(self, instance: AsyncContext[T]):
        self._instance = instance

    def get(self) -> AsyncContext[T]:
        return self._instance


class SyncSessionProvider[T](Provider, ABC):
    type = BorrowType.SESSION

    @contextmanager
    @abstractmethod
    def acquire_session(self, *args, **kwargs) -> AbstractContextManager[T]:
        ...

    def release(self):
        pass


class AsyncSessionProvider[T](Provider, ABC):
    type = BorrowType.SESSION

    @asynccontextmanager
    @abstractmethod
    async def acquire_session(self, *args, **kwargs) -> AbstractAsyncContextManager[T]:
        ...

    async def release(self):
        pass


class SyncExclusiveProvider[T](Provider, ABC):
    type = BorrowType.EXCLUSIVE

    @abstractmethod
    def acquire(self, *args, **kwargs) -> Result[T]:
        ...

    @abstractmethod
    def release(self, instance: T) -> Result:
        ...


class AsyncExclusiveProvider[T](Provider, ABC):
    type = BorrowType.EXCLUSIVE

    @abstractmethod
    async def acquire(self, *args, **kwargs) -> Result[T]:
        ...

    @abstractmethod
    async def release(self, instance: T) -> Result:
        ...


class SyncSharedProvider[ExclR, SharedR](Provider, ABC):
    type = BorrowType.SHARED

    @abstractmethod
    def acquire_exclusive(self, *args, **kwargs) -> Result[ExclR]:
        ...

    @abstractmethod
    def acquire_shared(self, *args, **kwargs) -> Result[SharedR]:
        ...

    @abstractmethod
    def release(self, instance: ExclR | SharedR) -> Result:
        ...


class AsyncSharedProvider[ExclR, SharedR](Provider, ABC):
    type = BorrowType.SHARED

    @abstractmethod
    async def acquire_exclusive(self, *args, **kwargs) -> Result[ExclR]:
        ...

    @abstractmethod
    async def acquire_shared(self, *args, **kwargs) -> Result[SharedR]:
        ...

    @abstractmethod
    async def release(self, instance: ExclR | SharedR) -> Result:
        ...
