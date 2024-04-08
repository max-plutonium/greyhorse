from abc import ABC, abstractmethod
from typing import Mapping

from .base import AsyncEngine, SyncEngine


class EngineFactory(ABC):
    @abstractmethod
    def get_engine_names(self) -> list[str]:
        ...


class SyncEngineFactory(EngineFactory):
    @abstractmethod
    def __call__(self, name: str, *args, **kwargs) -> SyncEngine:
        ...

    @abstractmethod
    def get_engine(self, name: str) -> SyncEngine | None:
        ...

    @abstractmethod
    def get_engines(self, names: list[str] | None = None) -> Mapping[str, SyncEngine]:
        ...


class AsyncEngineFactory(EngineFactory):
    @abstractmethod
    def __call__(self, name: str, *args, **kwargs) -> AsyncEngine:
        ...

    @abstractmethod
    def get_engine(self, name: str) -> AsyncEngine | None:
        ...

    @abstractmethod
    def get_engines(self, names: list[str] | None = None) -> Mapping[str, AsyncEngine]:
        ...
