from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager, asynccontextmanager, contextmanager, AbstractContextManager
from dataclasses import dataclass
from typing import Callable

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
        self, command: str, shell: bool = False,
        sudo: bool = False, as_bytes: bool = False,
        input: str | bytes | None = None,
    ) -> Callable[..., AbstractContextManager[SyncProcessAdapter]]:
        ...

    @abstractmethod
    def run(
        self, command: str, shell: bool = False,
        sudo: bool = False, as_bytes: bool = False,
        input: str | bytes | None = None,
    ) -> CompletedProcess:
        ...

    def sudo(
        self, command: str, shell: bool = False, as_bytes: bool = False,
        input: str | bytes | None = None,
    ) -> CompletedProcess:
        return self.run(command, shell=shell, sudo=True, as_bytes=as_bytes, input=input)


class AsyncSession(ABC):
    @asynccontextmanager
    @abstractmethod
    async def create_process(
        self, command: str, shell: bool = False,
        sudo: bool = False, as_bytes: bool = False,
        input: str | bytes | None = None,
    ) -> Callable[..., AbstractAsyncContextManager[AsyncProcessAdapter]]:
        ...

    @abstractmethod
    async def run(
        self, command: str, shell: bool = False,
        sudo: bool = False, as_bytes: bool = False,
        input: str | bytes | None = None,
    ) -> CompletedProcess:
        ...

    async def sudo(
        self, command: str, shell: bool = False, as_bytes: bool = False,
        input: str | bytes | None = None,
    ) -> CompletedProcess:
        return await self.run(command, shell=shell, sudo=True, as_bytes=as_bytes, input=input)


class SyncConnection(ABC):
    @abstractmethod
    @asynccontextmanager
    def session(self) -> Callable[[], AbstractContextManager[SyncSession]]:
        ...


class AsyncConnection(ABC):
    @abstractmethod
    @asynccontextmanager
    async def session(self) -> Callable[[], AbstractAsyncContextManager[AsyncSession]]:
        ...
