from collections import defaultdict
from collections.abc import Callable
from typing import override

from greyhorse.app.abc.collectors import (
    Collector,
    MutCollector,
    MutNamedCollector,
    NamedCollector,
)
from greyhorse.app.abc.selectors import ListSelector, NamedListSelector
from greyhorse.maybe import Just, Maybe, Nothing


class DictRegistry[K, T](Collector[K, T], ListSelector[K, T]):
    __slots__ = ('_storage',)

    def __init__(self) -> None:
        self._storage: dict[K, T] = {}

    def __len__(self) -> int:
        return len(self._storage)

    @override
    def add(self, key: K, instance: T) -> bool:
        if key in self._storage:
            return instance is self._storage[key]
        self._storage[key] = instance
        return True

    @override
    def has(self, key: K) -> bool:
        return key in self._storage

    @override
    def get(self, key: K) -> Maybe[T]:
        if key not in self._storage:
            return Nothing

        return Just(self._storage[key])

    @override
    def items(self, filter_fn: Callable[[K], bool] | None = None) -> list[tuple[K, T]]:
        result = []

        for k, v in self._storage.items():
            if not filter_fn or filter_fn(k):
                result.append((k, v))

        return result


class MutDictRegistry[K, T](MutCollector[K, T], DictRegistry[K, T]):
    @override
    def remove(self, key: K, instance: T | None = None) -> bool:
        if key not in self._storage:
            return False

        value = self._storage[key]

        if instance is None:
            del self._storage[key]

        else:
            if instance != value:
                return False
            del self._storage[key]

        return True


class ScopedDictRegistry[K, T](DictRegistry[K, T]):
    def __init__(
        self, factory: Callable[[], DictRegistry[K, T]], scope_func: Callable[[], str]
    ) -> None:
        super().__init__()
        self._scope_func = scope_func
        self._storage: dict[str, DictRegistry[K, T]] = defaultdict(factory)

    def _get_registry(self) -> DictRegistry[K, T]:
        key = self._scope_func()
        return self._storage[key]

    def __len__(self) -> int:
        registry = self._get_registry()
        return registry.__len__()

    @override
    def add(self, key: K, instance: T) -> bool:
        registry = self._get_registry()
        return registry.add(key, instance)

    @override
    def has(self, key: K) -> bool:
        registry = self._get_registry()
        return registry.has(key)

    @override
    def get(self, key: K) -> Maybe[T]:
        registry = self._get_registry()
        return registry.get(key)

    @override
    def items(self, filter_fn: Callable[[K], bool] | None = None) -> list[tuple[K, T]]:
        registry = self._get_registry()
        return registry.items(filter_fn)


class ScopedMutDictRegistry[K, T](MutDictRegistry[K, T]):
    def __init__(
        self, factory: Callable[[], MutDictRegistry[K, T]], scope_func: Callable[[], str]
    ) -> None:
        super().__init__()
        self._scope_func = scope_func
        self._storage: dict[str, MutDictRegistry[K, T]] = defaultdict(factory)

    def _get_registry(self) -> MutDictRegistry[K, T]:
        key = self._scope_func()
        return self._storage[key]

    def __len__(self) -> int:
        registry = self._get_registry()
        return registry.__len__()

    @override
    def add(self, key: K, instance: T) -> bool:
        registry = self._get_registry()
        return registry.add(key, instance)

    @override
    def has(self, key: K) -> bool:
        registry = self._get_registry()
        return registry.has(key)

    @override
    def get(self, key: K) -> Maybe[T]:
        registry = self._get_registry()
        return registry.get(key)

    @override
    def items(self, filter_fn: Callable[[K], bool] | None = None) -> list[tuple[K, T]]:
        registry = self._get_registry()
        return registry.items(filter_fn)

    @override
    def remove(self, key: K, instance: T | None = None) -> bool:
        registry = self._get_registry()
        return registry.remove(key, instance)


class NamedDictRegistry[K, T](NamedCollector[K, T], NamedListSelector[K, T]):
    __slots__ = ('_storage',)

    def __init__(self) -> None:
        self._storage: dict[K, dict[str | None, T]] = defaultdict(dict)

    def __len__(self) -> int:
        return len(self._storage)

    @override
    def add(self, key: K, instance: T, name: str | None = None) -> bool:
        if key in self._storage and name in self._storage[key]:
            return instance is self._storage[key][name]
        self._storage[key][name] = instance
        return True

    @override
    def has(self, key: K, name: str | None = None) -> bool:
        if key not in self._storage:
            return False
        if name is None:
            return True
        return name in self._storage[key]

    @override
    def get(self, key: K, name: str | None = None) -> Maybe[T]:
        if key not in self._storage:
            return Nothing

        if name is None:
            first_name = next(iter(self._storage[key]))
            return Just(self._storage[key][first_name])
        return Just(self._storage[key][name])

    @override
    def items(
        self, filter_fn: Callable[[K, str], bool] | None = None
    ) -> list[tuple[K, str, T]]:
        result = []

        for k, values in self._storage.items():
            for name, v in values.items():
                if not filter_fn or filter_fn(k, name):
                    result.append((k, name, v))

        return result


class MutNamedDictRegistry[K, T](MutNamedCollector[K, T], NamedDictRegistry[K, T]):
    @override
    def remove(self, key: K, instance: T | None = None, name: str | None = None) -> bool:
        if key not in self._storage:
            return False

        if name is None:
            values = self._storage[key]

            if instance is None:
                del self._storage[key]
            else:
                while len(values):
                    name = next(iter(values))
                    if instance == values[name]:
                        del values[name]
                if len(values) == 0:
                    del self._storage[key]

            return True

        if name not in self._storage[key]:
            return False

        del self._storage[key][name]

        if len(self._storage[key]) == 0:
            del self._storage[key]
        return True
