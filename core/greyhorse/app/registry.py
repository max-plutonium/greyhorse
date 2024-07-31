from dataclasses import dataclass, field
from typing import Any, override

from greyhorse.app.abc.collectors import Collector, MutCollector
from greyhorse.app.abc.selectors import Selector
from greyhorse.maybe import Nothing, Maybe
from greyhorse.utils import json, dicts, hashes
from greyhorse.utils.types import TypeWrapper


@dataclass(slots=True, frozen=True)
class _RegistryItem:
    hashsum: str = field(repr=False, hash=True, compare=True)
    dump: str = field(repr=True, hash=False, compare=False)
    class_: type | None = field(default=None, repr=False, hash=True, compare=True)


class ResourceRegistry[T](Collector[T], Selector[T], TypeWrapper[T]):
    def __init__(self):
        type_ = type[self.wrapped_type]
        self._storage: dict[_RegistryItem, type_] = {}

    @staticmethod
    def _prepare_keys(keys: dict[str, Any]) -> tuple[str, str]:
        flat_keys = dicts.dict_values_to_str(keys)
        dumped = json.dumps(flat_keys).decode('utf-8')
        digest = hashes.calculate_digest(flat_keys)
        return digest, dumped

    def __len__(self):
        return len(self._storage)

    @override
    def add(
        self, instance: T, class_: type[T] | None = None,
        classes: list[type[T]] | None = None, **keys,
    ) -> bool:
        if class_ is not None:
            classes = [class_] + classes if classes is not None else [class_]

        hashsum, dump = self._prepare_keys(keys)

        if not classes:
            item = _RegistryItem(hashsum=hashsum, dump=dump)
            if item in self._storage:
                return instance is self._storage[item]
            else:
                self._storage[item] = instance
                return True
        else:
            res = []

            for c in classes:
                item = _RegistryItem(hashsum=hashsum, dump=dump, class_=c)
                if item in self._storage:
                    res.append(instance is self._storage[item])
                else:
                    self._storage[item] = instance
                    res.append(True)

            return any(res)

    @override
    def has(self, class_: type[T] | None = None, **keys) -> bool:
        if class_ is None and not keys:
            return False

        hashsum, dump = self._prepare_keys(keys)
        item = _RegistryItem(hashsum=hashsum, dump=dump, class_=class_)
        return item in self._storage

    @override
    def get(self, class_: type[T] | None = None, **keys) -> Maybe[T]:
        if class_ is None and not keys:
            return Nothing

        hashsum, dump = self._prepare_keys(keys)
        item = _RegistryItem(hashsum=hashsum, dump=dump, class_=class_)
        value = self._storage.get(item, None)
        return Maybe(value)


class MutResourceRegistry[T](MutCollector[T], ResourceRegistry[T]):
    @override
    def remove(
        self, class_: type[T] | None = None, classes: list[type[T]] | None = None, **keys,
    ) -> Maybe[T]:
        if class_ is not None:
            classes = [class_] + classes if classes is not None else [class_]

        hashsum, dump = self._prepare_keys(keys)
        value = None

        if not classes:
            item = _RegistryItem(hashsum=hashsum, dump=dump)
            if item in self._storage:
                value = self._storage.pop(item, None)
        else:
            for c in classes:
                item = _RegistryItem(hashsum=hashsum, dump=dump, class_=c)
                if item in self._storage:
                    value = self._storage.pop(item, None)

        return Maybe(value)
