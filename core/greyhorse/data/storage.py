from abc import ABC, abstractmethod
from collections.abc import Awaitable, Mapping
from typing import override

from greyhorse.app.contexts import Context
from greyhorse.app.registries import MutDictRegistry
from greyhorse.maybe import Maybe
from greyhorse.utils.types import TypeWrapper


class Engine(ABC):
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    @abstractmethod
    def active(self) -> bool: ...

    @abstractmethod
    def get_context[T: Context](self, kind: type[T]) -> Maybe[T]: ...

    @abstractmethod
    def start(self) -> Awaitable[None] | None: ...

    @abstractmethod
    def stop(self) -> Awaitable[None] | None: ...


class EngineReader[T: Engine](TypeWrapper[T], ABC):
    @abstractmethod
    def get_engine(self, name: str) -> Maybe[T]: ...


class EngineFactory[T: Engine](EngineReader[T], ABC):
    @abstractmethod
    def create_engine[T](self, name: str, config: T) -> Engine: ...

    @abstractmethod
    def destroy_engine(self, name: str) -> bool: ...

    @abstractmethod
    def get_engine_names(self) -> list[str]: ...

    @abstractmethod
    def get_engines(self, names: list[str] | None = None) -> Mapping[str, Engine]: ...


class SimpleEngineFactory[T: Engine](EngineFactory[T], ABC):
    def __init__(self) -> None:
        self._engines = MutDictRegistry[str, Engine]()

    @override
    def destroy_engine(self, name: str) -> bool:
        return self._engines.remove(name)

    @override
    def get_engine_names(self) -> list[str]:
        return [k for k, _ in self._engines.items()]

    @override
    def get_engine(self, name: str) -> Maybe[T]:
        return self._engines.get(name)

    @override
    def get_engines(self, names: list[str] | None = None) -> Mapping[str, T]:
        engines = {}

        if not names:
            names = self.get_engine_names()

        for name in names:
            if engine := self.get_engine(name).unwrap_or_none():
                engines[name] = engine

        return engines
