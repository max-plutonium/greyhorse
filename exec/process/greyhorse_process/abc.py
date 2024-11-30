from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable, Generator
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    asynccontextmanager,
    contextmanager,
)
from dataclasses import dataclass

from .adapters import AsyncProcessAdapter, SyncProcessAdapter


@dataclass(slots=True, frozen=True)
class CompletedProcess:
    command: str
    returncode: int
    stdout: str | bytes
    stderr: str | bytes

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class SyncSession(ABC):
    @contextmanager
    @abstractmethod
    def create_process(
        self,
        command: str,
        shell: bool = False,
        sudo: bool = False,
        as_bytes: bool = False,
        input: str | bytes | None = None,
    ) -> Callable[..., AbstractContextManager[SyncProcessAdapter]]: ...

    @abstractmethod
    def run(
        self,
        command: str,
        shell: bool = False,
        sudo: bool = False,
        as_bytes: bool = False,
        input: str | bytes | None = None,
    ) -> CompletedProcess: ...

    def sudo(
        self,
        command: str,
        shell: bool = False,
        as_bytes: bool = False,
        input: str | bytes | None = None,
    ) -> CompletedProcess:
        return self.run(command, shell=shell, sudo=True, as_bytes=as_bytes, input=input)


class AsyncSession(ABC):
    @asynccontextmanager
    @abstractmethod
    async def create_process(
        self,
        command: str,
        shell: bool = False,
        sudo: bool = False,
        as_bytes: bool = False,
        input: str | bytes | None = None,
    ) -> Callable[..., AbstractAsyncContextManager[AsyncProcessAdapter]]: ...

    @abstractmethod
    async def run(
        self,
        command: str,
        shell: bool = False,
        sudo: bool = False,
        as_bytes: bool = False,
        input: str | bytes | None = None,
    ) -> CompletedProcess: ...

    async def sudo(
        self,
        command: str,
        shell: bool = False,
        as_bytes: bool = False,
        input: str | bytes | None = None,
    ) -> CompletedProcess:
        return await self.run(command, shell=shell, sudo=True, as_bytes=as_bytes, input=input)


class SyncConnection(ABC):
    @abstractmethod
    def session(self) -> Generator[AbstractContextManager[SyncSession], None, None]: ...


class AsyncConnection(ABC):
    @abstractmethod
    async def session(
        self,
    ) -> AsyncGenerator[AbstractAsyncContextManager[AsyncSession], None]: ...
