from abc import ABC, abstractmethod
from collections.abc import Awaitable, Mapping
from typing import NewType, override

from greyhorse.app.abc.providers import Provider
from greyhorse.app.registries import MutDictRegistry
from greyhorse.maybe import Just, Maybe, Nothing


class ProviderRegistry:
    __slots__ = ('_storage',)

    def __init__(self) -> None:
        self._storage = MutDictRegistry[tuple[type, str], Provider]()

    def add(self, conn_type: type, name: str, provider: Provider) -> bool:
        return self._storage.add((conn_type, name), provider)

    def remove(self, conn_type: type, name: str) -> bool:
        return self._storage.remove((conn_type, name))

    def has(self, conn_type: type, name: str | None = None) -> bool:
        items = self._storage.items(
            lambda key: key[0] == conn_type and (key[1] == name if name else True)
        )
        return len(items) > 0

    def get[T: Provider](self, conn_type: type, name: str | None = None) -> Maybe[T]:
        items = self._storage.items(
            lambda key: key[0] == conn_type and (key[1] == name if name else True)
        )
        if items:
            return Just(items[0][1])
        return Nothing

    def __len__(self) -> int:
        return len(self._storage)


ConnectionProviderRegistry = NewType('ConnectionProviderRegistry', ProviderRegistry)
SessionProviderRegistry = NewType('SessionProviderRegistry', ProviderRegistry)


class DataStorageEngine(ABC):
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    @abstractmethod
    def active(self) -> bool: ...

    @abstractmethod
    def get_provider[P: Provider](self, prov_type: type[P]) -> Maybe[P]: ...

    def start(self) -> Awaitable[None] | None:
        pass

    def stop(self) -> Awaitable[None] | None:
        pass


class DataStorageEngineFactory(ABC):
    @abstractmethod
    def create_engine(self, name: str, *args, **kwargs) -> DataStorageEngine: ...

    @abstractmethod
    def destroy_engine(self, name: str) -> bool: ...

    @abstractmethod
    def get_engine_names(self) -> list[str]: ...

    @abstractmethod
    def get_engine(self, name: str) -> Maybe[DataStorageEngine]: ...

    @abstractmethod
    def get_engines(
        self, names: list[str] | None = None
    ) -> Mapping[str, DataStorageEngine]: ...


class SimpleDataStorageFactory[T: DataStorageEngine](DataStorageEngineFactory, ABC):
    def __init__(self) -> None:
        self._engines = MutDictRegistry[str, DataStorageEngine]()

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
