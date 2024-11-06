import inspect
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, TypeVar, get_type_hints

from greyhorse.maybe import Just, Maybe, Nothing
from greyhorse.utils.invoke import caller_path
from greyhorse.utils.types import is_maybe, is_optional, unwrap_maybe, unwrap_optional

from ..abc.module import Module
from .container import Container, root

Target = TypeVar('Target', bound=Callable | type)


@dataclass(slots=True)
class _ModuleNode:
    children: dict[str, '_ModuleNode'] = field(default_factory=dict)
    targets: list[Target] = field(default_factory=list)


class _TargetCollector:
    __slots__ = ('_root',)

    def __init__(self) -> None:
        self._root = _ModuleNode()

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

        result = current.targets.copy()
        nodes = list(current.children.values())
        curr_idx = 0

        while curr_idx < len(nodes):
            node = nodes[curr_idx]
            nodes += node.children.values()
            curr_idx += 1

        for node in nodes:
            result += node.targets.copy()

        return result


_collector = _TargetCollector()


def get_current_module(depth: int = 2) -> Maybe[Module]:
    current_module_path = caller_path(depth)

    while len(current_module_path):
        dotted_module_path = '.'.join(current_module_path)
        if (mod := sys.modules.get(dotted_module_path)) and (
            instance := getattr(mod, '__gh_module__', None)
        ):
            return Just(instance)

        current_module_path = current_module_path[: len(current_module_path) - 1]

    return Nothing


def inject_targets(container: Container, paths: Iterable[str]) -> int:
    targets = set()

    for path in paths:
        targets.update(set(_collector.list_targets(path)))

    for target in targets:
        target.__container__ = container

    return len(targets)


def uninject_targets(paths: Iterable[str]) -> int:
    targets = set()

    for path in paths:
        targets.update(set(_collector.list_targets(path)))

    for target in targets:
        delattr(target, '__container__')

    return len(targets)


def _invoke_target[T, **P](
    func: Callable[P, T],
    hints: dict[str, Any],
    container: Container,
    /,
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    injected_args = {}
    args_count = len(args) if inspect.ismethod(func) else len(args) - 1

    for i, (k, v) in enumerate(hints.items()):
        if i < args_count or k in kwargs:
            continue
        if value := container.get(unwrap_maybe(unwrap_optional(v))):
            injected_args[k] = value if is_maybe(v) else value.unwrap()
        elif is_maybe(v):
            injected_args[k] = Nothing
        elif is_optional(v):
            injected_args[k] = None

    kwargs.update(injected_args)
    return func(*args, **kwargs)


def inject[T, **P](target: Callable[P, T] | type[T]) -> Callable[P, T]:
    hints = get_type_hints(target)
    hints.pop('return', None)

    @wraps(target)
    def decorator(*args: P.args, **kwargs: P.kwargs) -> T:
        container = getattr(target, '__container__', root)
        return _invoke_target(target, hints, container, *args, **kwargs)

    _collector.add_target(target)
    return decorator
