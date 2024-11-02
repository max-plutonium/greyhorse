from __future__ import annotations

from types import TracebackType
from typing import Any

from greyhorse.maybe import Just, Maybe, Nothing
from greyhorse.utils.invoke import invoke_sync

from ..contexts import CtxCallbacks, SyncContext, SyncContextWithCallbacks
from ..registries import DictRegistry
from .registry import FactoryRegistry, Lifetime, TypeFactory


class Container:
    __slots__ = (
        '_registry',
        '_child_registries',
        '_parent',
        '_context',
        '_resources',
        '_scoped_factories',
        '_ctx',
    )

    def __init__(
        self,
        registry: FactoryRegistry,
        *child_registries: FactoryRegistry,
        parent: Container | None = None,
        context: dict[Any, Any] | None = None,
    ) -> None:
        self._registry = registry
        self._child_registries = child_registries
        self._parent = parent
        self._context = {type(self): self}

        self._resources = DictRegistry[type, Any]()
        self._scoped_factories: dict[type, TypeFactory] = {}

        if context:
            self._context.update(context)

        self._ctx = self._create_ctx()

    def __repr__(self) -> str:
        return f'Container<{self.lifetime.name}>'

    @property
    def registry(self) -> FactoryRegistry:
        return self._registry

    @property
    def lifetime(self) -> Lifetime:
        return self._registry.lifetime

    @property
    def context(self) -> SyncContext[Container]:
        return self._ctx

    def child_registry(self, lifetime: Lifetime) -> Maybe[FactoryRegistry]:
        for child in self._child_registries:
            if child.lifetime == lifetime:
                return Just(child)
        return Nothing

    def __call__(
        self, context: dict[Any, Any] | None = None, lifetime: Lifetime | None = None
    ) -> SyncContext[Container]:
        if lifetime is not None and lifetime.order <= self.lifetime.order:
            return self.context

        if not self._child_registries:
            return self.context

        child = Container(*self._child_registries, parent=self, context=context)

        if lifetime is None:
            while child.registry.lifetime.autocreate:
                if not child._child_registries:  # noqa: SLF001
                    break
                child = Container(*child._child_registries, parent=child, context=context)  # noqa: SLF001
        else:
            while child.registry.lifetime.order < lifetime.order:
                if not child._child_registries:  # noqa: SLF001
                    raise ValueError(
                        f'Cannot find {lifetime} as a child of current '
                        f'{self._registry.lifetime}'
                    )
                child = Container(*child._child_registries, parent=child, context=context)  # noqa: SLF001

        return child.context

    def get[T](self, key: type[T]) -> Maybe[T]:
        return self._get(key)[0]

    def _get[T](self, key: type[T]) -> tuple[Maybe[T], bool]:
        if res := self._resources.get(key):
            return res, True

        if factory := self._registry.get_factory(key).unwrap_or_none():
            if res := invoke_sync(factory.create, key):
                if factory.scoped:
                    self._scoped_factories[key] = factory
                if factory.cache:
                    self._resources.add(key, res.unwrap())
            return res, factory.cache

        if not self._parent:
            return Nothing, False

        res, cached = self._parent._get(key)  # noqa: SLF001
        if cached:
            self._resources.add(key, res.unwrap())
        return res, cached

    def _enter(self, _) -> None:  # noqa: ANN001
        if self._parent:
            self._parent.context.__enter__()

        for k, v in self._context.items():
            self._resources.add(k, v)

    def _exit(
        self,
        _,  # noqa: ANN001
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        while key := next(reversed(self._scoped_factories), None):
            factory = self._scoped_factories[key]
            res = self._resources.get(key).unwrap_or_none()
            invoke_sync(factory.destroy, res)
            del self._scoped_factories[key]

        self._resources.clear()

        if self._parent:
            self._parent.context.__exit__(exc_type, exc_value, traceback)

    def _create_ctx(self) -> SyncContext[Container]:
        return SyncContextWithCallbacks[Container](
            callbacks=CtxCallbacks(on_enter=Just(self._enter), on_exit=Just(self._exit)),
            factory=lambda *_: self,
        )


def make_container(
    context: dict[Any, Any] | None = None, lifetime: Lifetime | None = None
) -> Container:
    registries = [FactoryRegistry(s) for s in Lifetime.all()]
    container = Container(*registries, context=context)

    if lifetime is None:
        while container.registry.lifetime.autocreate:
            container = Container(
                *container._child_registries,  # noqa: SLF001
                parent=container,
                context=context,
            )
    else:
        while container.registry.lifetime.order < lifetime.order:
            container = Container(
                *container._child_registries,  # noqa: SLF001
                parent=container,
                context=context,
            )

    return container


root = make_container(lifetime=Lifetime.ROOT())  # type: ignore
