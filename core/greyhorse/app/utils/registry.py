from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Mapping, Self, override


@dataclass
class KeyMapping[K]:
    map_to: K
    names: list[str] = field(default_factory=list)


class ReadonlyRegistry[K, V](ABC):
    @abstractmethod
    def get_names(self, key: K) -> list[str]:
        ...

    @abstractmethod
    def has(self, key: K, name: str | None = None) -> bool:
        ...

    @abstractmethod
    def get(self, key: K, name: str | None = None) -> V | None:
        ...


class Registry[K, V](ReadonlyRegistry[K, V], ABC):
    @abstractmethod
    def set(self, key: K, instance: V, name: str | None = None) -> bool:
        ...

    @abstractmethod
    def reset(self, key: K, name: str | None = None) -> bool:
        ...

    @abstractmethod
    def merge(self, other: Self, key_mapping: Mapping[K, KeyMapping[K]] | None = None):
        ...

    @abstractmethod
    def subtract(self, other: Self, key_mapping: Mapping[K, KeyMapping[K]] | None = None):
        ...


class DictRegistry[K, V](Registry[K, V]):
    def __init__(self):
        self._registry: dict[K, dict[str, V]] = defaultdict(dict)

    def list_keys(self) -> list[K]:
        return list(self._registry.keys())

    @override
    def get_names(self, key: K) -> list[str]:
        if key in self._registry:
            return list(self._registry[key].keys())
        else:
            return []

    @override
    def has(self, key: K, name: str | None = None) -> bool:
        if key in self._registry:
            if name is None:
                return True
            else:
                return name in self._registry[key]
        else:
            return False

    @override
    def get(self, key: K, name: str | None = None) -> V | None:
        if key in self._registry:
            if name is None:
                values = list(self._registry[key].values())
                return values[0] if len(values) > 0 else None
            else:
                return self._registry[key].get(name)
        else:
            return None

    @override
    def set(self, key: K, instance: V, name: str | None = None) -> bool:
        if key in self._registry:
            if name is None:
                return instance is self._registry[key]['']
            elif name in self._registry[key]:
                return instance is self._registry[key][name]
        self._registry[key][name or ''] = instance
        return True

    @override
    def reset(self, key: K, name: str | None = None) -> bool:
        if key in self._registry:
            if name is None:
                del self._registry[key]
                return True
            elif name in self._registry[key]:
                if len(self._registry[key]) == 1:
                    del self._registry[key]
                else:
                    del self._registry[key][name]
                return True
        return False

    @override
    def merge(self, other: Self, key_mapping: Mapping[K, KeyMapping[K]] | None = None):
        for key, values_dict in other._registry.items():
            only_names = set()
            if key_mapping is not None:
                if key not in key_mapping:
                    continue
                else:
                    only_names = set(key_mapping[key].names)
                    key = key_mapping[key].map_to

            for name, value in values_dict.items():
                if not only_names or name in only_names:
                    self.set(key, value, name=name)

    @override
    def subtract(self, other: Self, key_mapping: Mapping[K, KeyMapping[K]] | None = None):
        for key, values_dict in other._registry.items():
            only_names = set()
            if key_mapping is not None:
                if key not in key_mapping:
                    continue
                else:
                    only_names = set(key_mapping[key].names)
                    key = key_mapping[key].map_to

            for name in values_dict.keys():
                if not only_names or name in only_names:
                    self.reset(key, name=name)


class ScopedReadonlyRegistry[K, V](ReadonlyRegistry[K, V]):
    def __init__(
        self, factory: Callable[[], ReadonlyRegistry[K, V]],
        scope_func: Callable[[], str],
    ):
        self._factory = factory
        self._scope_func = scope_func
        self._registries: dict[str, ReadonlyRegistry[K, V]] = defaultdict(self._factory)

    def _get_registry(self) -> ReadonlyRegistry[K, V]:
        key = self._scope_func()
        return self._registries[key]

    def clear(self):
        key = self._scope_func()
        self._registries.pop(key, None)

    @override
    def get_names(self, key: K) -> list[str]:
        registry = self._get_registry()
        return registry.get_names(key)

    @override
    def has(self, key: K, name: str | None = None) -> bool:
        registry = self._get_registry()
        return registry.has(key, name)

    @override
    def get(self, key: K, name: str | None = None) -> V | None:
        registry = self._get_registry()
        return registry.get(key, name)


class ScopedRegistry[K, V](Registry[K, V]):
    def __init__(
        self, factory: Callable[[], Registry[K, V]],
        scope_func: Callable[[], str],
    ):
        self._factory = factory
        self._scope_func = scope_func
        self._registries: dict[str, Registry[K, V]] = defaultdict(self._factory)

    def _get_registry(self) -> Registry[K, V]:
        key = self._scope_func()
        return self._registries[key]

    def clear(self):
        key = self._scope_func()
        self._registries.pop(key, None)

    @override
    def get_names(self, key: K) -> list[str]:
        registry = self._get_registry()
        return registry.get_names(key)

    @override
    def has(self, key: K, name: str | None = None) -> bool:
        registry = self._get_registry()
        return registry.has(key, name)

    @override
    def get(self, key: K, name: str | None = None) -> V | None:
        registry = self._get_registry()
        return registry.get(key, name)

    @override
    def set(self, key: K, instance: V, name: str | None = None) -> bool:
        registry = self._get_registry()
        return registry.set(key, instance, name)

    @override
    def reset(self, key: K, name: str | None = None) -> bool:
        registry = self._get_registry()
        return registry.reset(key, name)

    @override
    def merge(self, other: Self, key_mapping: Mapping[K, KeyMapping[K]] | None = None):
        registry = self._get_registry()
        return registry.merge(other, key_mapping)

    @override
    def subtract(self, other: Self, key_mapping: Mapping[K, KeyMapping[K]] | None = None):
        registry = self._get_registry()
        return registry.subtract(other, key_mapping)
