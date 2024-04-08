import enum
from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager, AbstractContextManager, asynccontextmanager, contextmanager
from typing import Callable

from greyhorse.result import Result
from ..utils.registry import ReadonlyRegistry

type ProviderKey = type[Provider]
type ProviderFactoryFn = Callable[[...], Result[Provider]]
type ProviderFactoryRegistry = ReadonlyRegistry[ProviderKey, ProviderFactoryFn]


class BorrowType(str, enum.Enum):
    SIMPLE = 'simple'
    SESSION = 'session'
    EXCLUSIVE = 'exclusive'
    SHARED = 'shared'


class Provider:
    is_sync: bool
    is_async: bool
    type: BorrowType

    @property
    def active(self) -> bool:
        return False


class SyncSimpleProvider[R](Provider, ABC):
    is_sync = True
    is_async = False
    type = BorrowType.SIMPLE

    @abstractmethod
    def get(self, *args, **kwargs) -> R:
        ...


class AsyncSimpleProvider[R](Provider, ABC):
    is_sync = False
    is_async = True
    type = BorrowType.SIMPLE

    @abstractmethod
    async def get(self, *args, **kwargs) -> R:
        ...


class SyncSessionProvider[R](Provider, ABC):
    is_sync = True
    is_async = False
    type = BorrowType.SESSION

    @contextmanager
    @abstractmethod
    def acquire_session(self, *args, **kwargs) -> AbstractContextManager[R]:
        ...

    def release(self):
        pass


class AsyncSessionProvider[R](Provider, ABC):
    is_sync = False
    is_async = True
    type = BorrowType.SESSION

    @asynccontextmanager
    @abstractmethod
    async def acquire_session(self, *args, **kwargs) -> AbstractAsyncContextManager[R]:
        ...

    async def release(self):
        pass


class SyncExclusiveProvider[R](Provider, ABC):
    is_sync = True
    is_async = False
    type = BorrowType.EXCLUSIVE

    @abstractmethod
    def acquire(self, *args, **kwargs) -> Result[R]:
        ...

    @abstractmethod
    def release(self, instance: R) -> Result:
        ...


class AsyncExclusiveProvider[R](Provider, ABC):
    is_sync = False
    is_async = True
    type = BorrowType.EXCLUSIVE

    @abstractmethod
    async def acquire(self, *args, **kwargs) -> Result[R]:
        ...

    @abstractmethod
    async def release(self, instance: R) -> Result:
        ...


class SyncSharedProvider[ExclR, SharedR](Provider, ABC):
    is_sync = True
    is_async = False
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
    is_sync = False
    is_async = True
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
