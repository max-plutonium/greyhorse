import inspect
from dataclasses import dataclass, field
from functools import partial
from typing import Any

from greyhorse.maybe import Just, Maybe, Nothing

from ..abc.resources import Lifetime, TypeFactoryFn
from .factories import TypeFactory


@dataclass(slots=True)
class _ModuleNode:
    default_factory: TypeFactory | None = None
    children: dict[str, '_ModuleNode'] = field(default_factory=dict)
    factories: dict[type, TypeFactory] = field(default_factory=dict)


class FactoryRegistry:
    __slots__ = ('_lifetime', '_root')

    def __init__(self, lifetime: Lifetime) -> None:
        self._lifetime = lifetime
        self._root = _ModuleNode()

    def __repr__(self) -> str:
        return f'FactoryRegistry<{self._lifetime.name}>'

    def __len__(self) -> int:
        nodes = list(self._root.children.values())
        curr_idx = 0

        while curr_idx < len(nodes):
            node = nodes[curr_idx]
            nodes += node.children.values()
            curr_idx += 1

        result = 0

        for node in nodes:
            result += len(node.factories)

        return result

    @property
    def lifetime(self) -> Lifetime:
        return self._lifetime

    @staticmethod
    def _into_factory[T](key: type[T], fn: TypeFactoryFn[T]) -> TypeFactory[T]:
        if callable(fn):
            orig_fn = fn
            while isinstance(orig_fn, partial):
                orig_fn = orig_fn.func

            if inspect.isgeneratorfunction(inspect.unwrap(orig_fn)):
                return TypeFactory[key].from_syncgen(fn)
            if inspect.isasyncgenfunction(inspect.unwrap(orig_fn)):
                return TypeFactory[key].from_asyncgen(fn)
            if inspect.isfunction(orig_fn) or inspect.ismethod(orig_fn):
                return TypeFactory[key].from_fn(fn)
        if inspect.isclass(fn):
            return TypeFactory[key].from_class(fn)
        return TypeFactory[key].from_instance(fn)

    def add_default_factory(
        self, path: str, fn: TypeFactoryFn[Any], cache: bool = False
    ) -> bool:
        factory = self._into_factory(Any, fn)
        factory.cache |= cache
        current = self._root

        if path != '':
            for path_entry in path.split('.'):
                if path_entry not in current.children:
                    current.children[path_entry] = _ModuleNode()
                current = current.children[path_entry]

        if current.default_factory:
            return False

        current.default_factory = factory
        return True

    def add_factory[T](
        self, key: type[T], fn: TypeFactoryFn[T] | None = None, cache: bool = True
    ) -> bool:
        factory = self._into_factory(key, fn if fn is not None else key)
        factory.cache |= cache
        path = key.__module__
        current = self._root

        for path_entry in path.split('.'):
            if path_entry not in current.children:
                current.children[path_entry] = _ModuleNode()
            current = current.children[path_entry]

        if key in current.factories:
            return False

        current.factories[key] = factory
        return True

    def remove_factory[T](self, key: type[T]) -> bool:
        path = key.__module__
        current = self._root

        for path_entry in path.split('.'):
            if path_entry not in current.children:
                return False
            current = current.children[path_entry]

        if key not in current.factories:
            return False

        del current.factories[key]
        return True

    def get_factory[T](self, key: type[T]) -> Maybe[TypeFactory]:
        path = key.__module__
        current = self._root
        nodes: list[_ModuleNode] = []
        wrong_path = False

        for path_entry in path.split('.'):
            if path_entry not in current.children:
                if not current.default_factory:
                    wrong_path = True
                    break
                if current.default_factory.has(key):
                    return Just(current.default_factory)
            else:
                nodes.append(current)
                current = current.children[path_entry]

        if not wrong_path:
            if key in current.factories:
                return Just(current.factories[key])
            if current.default_factory and current.default_factory.has(key):
                return Just(current.default_factory)

        for node in reversed(nodes):
            if node.default_factory and node.default_factory.has(key):
                return Just(node.default_factory)

        return Nothing

    def clear(self) -> None:
        self._root = _ModuleNode()
