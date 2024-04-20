from abc import ABC, abstractmethod
from typing import Awaitable, Mapping, override

from greyhorse.app.context import Context


class DataStorageEngine(ABC):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    @abstractmethod
    def active(self) -> bool:
        ...

    def start(self) -> Awaitable[None] | None:
        pass

    def stop(self) -> Awaitable[None] | None:
        pass

    @abstractmethod
    def get_context[T: Context](self, kind: type[T]) -> T | None:
        ...


class DataStorageEngineFactory(ABC):
    @abstractmethod
    def create_engine(self, name: str, *args, **kwargs) -> DataStorageEngine:
        ...

    @abstractmethod
    def destroy_engine(self, name: str) -> bool:
        ...

    @abstractmethod
    def get_engine_names(self) -> list[str]:
        ...

    @abstractmethod
    def get_engine(self, name: str) -> DataStorageEngine | None:
        ...

    @abstractmethod
    def get_engines(self, names: list[str] | None = None) -> Mapping[str, DataStorageEngine]:
        ...


class SimpleDataStorageFactory[T](DataStorageEngineFactory, ABC):
    def __init__(self):
        self._engines: dict[str, T] = {}

    @override
    def destroy_engine(self, name: str) -> bool:
        return self._engines.pop(name, None) is not None

    @override
    def get_engine_names(self) -> list[str]:
        return list(self._engines.keys())

    @override
    def get_engine(self, name: str) -> T | None:
        return self._engines.get(name)

    @override
    def get_engines(self, names: list[str] | None = None) -> Mapping[str, T]:
        engines = dict()

        if not names:
            names = self.get_engine_names()

        for name in names:
            if engine := self.get_engine(name):
                engines[name] = engine

        return engines
