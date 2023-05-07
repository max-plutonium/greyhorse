from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager, AbstractContextManager, asynccontextmanager, contextmanager
from typing import Callable, Generic, List, Mapping, Optional, TypeVar, Union

SessionType = TypeVar('SessionType')
SyncSessionFactory = Callable[[], AbstractContextManager[SessionType]]
AsyncSessionFactory = Callable[[], AbstractAsyncContextManager[SessionType]]


class SyncEngine(Generic[SessionType], ABC):
    is_sync = True
    is_async = False

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @contextmanager
    @abstractmethod
    def session(self, *args, **kwargs) -> AbstractContextManager[SessionType]:
        ...

    def teardown_session(self):
        pass

    @abstractmethod
    def start(self):
        ...

    @abstractmethod
    def stop(self):
        ...


class AsyncEngine(Generic[SessionType], ABC):
    is_sync = False
    is_async = True

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @asynccontextmanager
    @abstractmethod
    async def session(self, *args, **kwargs) -> AbstractAsyncContextManager[SessionType]:
        ...

    async def teardown_session(self):
        pass

    @abstractmethod
    async def start(self):
        ...

    @abstractmethod
    async def stop(self):
        ...
