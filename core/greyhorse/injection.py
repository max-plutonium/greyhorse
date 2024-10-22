from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, TypeVar, get_type_hints

from greyhorse.maybe import Maybe, Nothing
from greyhorse.utils.types import unwrap_optional

Target = TypeVar('Target', bound=Callable | type)
TypeFactory = Callable[[type], Maybe]


@dataclass(slots=True)
class _ModuleNode:
    default_factory: TypeFactory | None = None
    factories: dict[type, TypeFactory] = field(default_factory=dict)
    targets: list[Target] = field(default_factory=list)
    children: dict[str, '_ModuleNode'] = field(default_factory=dict)


class _FactoryStorage:
    __slots__ = ('_root', '_factory_cache')

    def __init__(self) -> None:
        self._root = _ModuleNode()
        self._factory_cache: dict[type, TypeFactory] = {}

    def add_target(self, target: Target) -> bool:
        path = target.__module__
        current = self._root

        for path_entry in path.split('.'):
            if path_entry not in current.children:
                current.children[path_entry] = _ModuleNode()
            current = current.children[path_entry]

        if target in current.targets:
            return False

        current.targets.append(target)
        return True

    def list_targets(self, path: str) -> list[Target]:
        current = self._root

        for path_entry in path.split('.'):
            if path_entry not in current.children:
                return []
            current = current.children[path_entry]

        return current.targets

    def add_default_factory(self, path: str, factory: TypeFactory) -> bool:
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

    def add_factory(self, key: type, factory: TypeFactory) -> bool:
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

    def get[T](self, key: type[T]) -> Maybe[T]:
        if key in self._factory_cache:
            return self._factory_cache[key](key)

        path = key.__module__
        current = self._root
        nodes: list[_ModuleNode] = []
        wrong_path = False

        for path_entry in path.split('.'):
            if path_entry not in current.children:
                if current.default_factory:
                    if res := current.default_factory(key):
                        self._factory_cache[key] = current.default_factory
                        return res
                else:
                    wrong_path = True
                    break
            else:
                nodes.append(current)
                current = current.children[path_entry]

        if not wrong_path:
            if factory := current.factories.get(type):
                self._factory_cache[key] = factory
                return factory(key)
            if current.default_factory and (res := current.default_factory(key)):
                self._factory_cache[key] = current.default_factory
                return res

        for node in reversed(nodes):
            if node.default_factory and (res := node.default_factory(key)):
                self._factory_cache[key] = node.default_factory
                return res

        return Nothing


storage = _FactoryStorage()


def _invoke_target[T, **P](
    func: Callable[P, T], hints: dict[str, Any], /, *args: P.args, **kwargs: P.kwargs
) -> T:
    injected_args = {}
    args_count = len(args) if func.__name__ != '__init__' else len(args) - 1

    for i, (k, v) in enumerate(hints.items()):
        if i < args_count or k in kwargs:
            continue
        if value := storage.get(unwrap_optional(v)):
            injected_args[k] = value.unwrap()

    kwargs.update(injected_args)
    return func(*args, **kwargs)


def inject[T, **P](target: Callable[P, T] | type[T]) -> Callable[P, T]:
    hints = get_type_hints(target)
    hints.pop('return', None)

    @wraps(target)
    def decorator(*args: P.args, **kwargs: P.kwargs) -> T:
        return _invoke_target(target, hints, *args, **kwargs)

    storage.add_target(target)
    return decorator
