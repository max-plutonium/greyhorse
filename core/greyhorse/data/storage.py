from abc import ABC, abstractmethod
from collections.abc import Awaitable, Mapping
from typing import override

from greyhorse.app.abc.collectors import MutCollector
from greyhorse.app.abc.selectors import ListSelector, Selector
from greyhorse.app.contexts import Context
from greyhorse.app.registries import MutDictRegistry
from greyhorse.maybe import Maybe


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


class EngineCollector[E: Engine](MutCollector[str, E], ABC):
    pass


class EngineSelector[E: Engine](Selector[str, E], ABC):
    pass


class EngineListSelector[E: Engine](ListSelector[str, E], ABC):
    pass


class EngineFactory[T: Engine](ABC):
    @abstractmethod
    def create_engine[T](self, name: str, config: T) -> Engine: ...

    @abstractmethod
    def destroy_engine(self, name: str) -> bool: ...

    @abstractmethod
    def get_engine_names(self) -> list[str]: ...

    @abstractmethod
    def get_engine(self, name: str) -> Maybe[T]: ...

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
        return [k for k, _ in self._engines.list()]

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
