from collections import defaultdict
from collections.abc import Callable, Iterable
from typing import Any, override

from greyhorse.maybe import Just, Maybe, Nothing

from .abc.collectors import Collector, MutCollector
from .abc.selectors import ListSelector


class DictRegistry[K, T](Collector[K, T], ListSelector[K, T]):
    __slots__ = ('_storage', '_allow_many')

    def __init__(self, allow_many: bool = False) -> None:
        self._storage: dict[K, dict[int, tuple[T, dict[str, Any]]]] = {}
        self._allow_many = allow_many

    def __len__(self) -> int:
        return len(self._storage)

    @override
    def add(self, key: K, instance: T, **metadata: dict[str, Any]) -> bool:
        if key in self._storage:
            if not self._allow_many:
                return id(instance) in self._storage[key]
            self._storage[key][id(instance)] = (instance, metadata)
        else:
            self._storage[key] = {id(instance): (instance, metadata)}
        return True

    @override
    def has(self, key: K) -> bool:
        return key in self._storage

    @override
    def get(self, key: K) -> Maybe[T]:
        if key not in self._storage:
            return Nothing

        item = next(iter(self._storage[key].values()))
        return Just(item[0])

    @override
    def get_with_metadata(self, key: K) -> Maybe[tuple[T, dict[str, Any]]]:
        if key not in self._storage:
            return Nothing

        item = next(iter(self._storage[key].values()))
        return Just(item)

    @override
    def list(self, key: K | None = None) -> Iterable[tuple[K, T] | T]:
        if key is None:
            for k, v in self._storage.items():
                for item in v.values():
                    yield k, item[0]
        else:
            if key not in self._storage:
                return

            for item in self._storage[key].values():
                yield item[0]

    @override
    def list_with_metadata(self, key: K | None = None) -> Iterable[tuple[K, T, dict[str, Any]]]:
        if key is None:
            for k, v in self._storage.items():
                for item in v.values():
                    yield k, *item
        else:
            if key not in self._storage:
                return

            yield from self._storage[key].values()

    @override
    def filter(
        self, filter_fn: Callable[[K, dict[str, Any]], bool] | None = None
    ) -> Iterable[tuple[K, T, dict[str, Any]]]:
        for k, v in self._storage.items():
            for item in v.values():
                if not filter_fn or filter_fn(k, item[1]):
                    yield k, *item

    def clear(self) -> None:
        while key := next(iter(self._storage), None):
            del self._storage[key]


class MutDictRegistry[K, T](MutCollector[K, T], DictRegistry[K, T]):
    @override
    def remove(self, key: K, instance: T | None = None) -> bool:
        if key not in self._storage:
            return False

        if instance is None:
            del self._storage[key]
            result = True

        else:
            result = self._storage[key].pop(id(instance), None) is not None
            if len(self._storage[key]) == 0:
                del self._storage[key]

        return result


class ScopedDictRegistry[K, T](Collector[K, T], ListSelector[K, T]):
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
    def add(self, key: K, instance: T, **metadata: dict[str, Any]) -> bool:
        registry = self._get_registry()
        return registry.add(key, instance, **metadata)

    @override
    def has(self, key: K) -> bool:
        registry = self._get_registry()
        return registry.has(key)

    @override
    def get(self, key: K) -> Maybe[T]:
        registry = self._get_registry()
        return registry.get(key)

    @override
    def get_with_metadata(self, key: K) -> Maybe[tuple[T, dict[str, Any]]]:
        registry = self._get_registry()
        return registry.get_with_metadata(key)

    @override
    def list(self, key: K | None = None) -> Iterable[tuple[K, T] | T]:
        registry = self._get_registry()
        return registry.list(key)

    @override
    def list_with_metadata(self, key: K | None = None) -> Iterable[tuple[K, T, dict[str, Any]]]:
        registry = self._get_registry()
        return registry.list_with_metadata(key)

    @override
    def filter(
        self, filter_fn: Callable[[K, dict[str, Any]], bool] | None = None
    ) -> Iterable[tuple[K, T, dict[str, Any]]]:
        registry = self._get_registry()
        yield from registry.filter(filter_fn)

    def clear(self) -> None:
        registry = self._get_registry()
        registry.clear()
        del self._storage[self._scope_func()]


class ScopedMutDictRegistry[K, T](MutCollector[K, T], ListSelector[K, T]):
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
    def add(self, key: K, instance: T, **metadata: dict[str, Any]) -> bool:
        registry = self._get_registry()
        return registry.add(key, instance, **metadata)

    @override
    def has(self, key: K) -> bool:
        registry = self._get_registry()
        return registry.has(key)

    @override
    def get(self, key: K) -> Maybe[T]:
        registry = self._get_registry()
        return registry.get(key)

    @override
    def get_with_metadata(self, key: K) -> Maybe[tuple[T, dict[str, Any]]]:
        registry = self._get_registry()
        return registry.get_with_metadata(key)

    @override
    def list(self, key: K | None = None) -> Iterable[tuple[K, T] | T]:
        registry = self._get_registry()
        return registry.list(key)

    @override
    def list_with_metadata(self, key: K | None = None) -> Iterable[tuple[K, T, dict[str, Any]]]:
        registry = self._get_registry()
        return registry.list_with_metadata(key)

    @override
    def filter(
        self, filter_fn: Callable[[K, dict[str, Any]], bool] | None = None
    ) -> Iterable[tuple[K, T, dict[str, Any]]]:
        registry = self._get_registry()
        yield from registry.filter(filter_fn)

    @override
    def remove(self, key: K, instance: T | None = None) -> bool:
        registry = self._get_registry()
        return registry.remove(key, instance)

    def clear(self) -> None:
        registry = self._get_registry()
        registry.clear()
        del self._storage[self._scope_func()]
