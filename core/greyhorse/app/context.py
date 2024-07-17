from __future__ import annotations

import asyncio
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import AbstractAsyncContextManager, AbstractContextManager, AsyncExitStack, ExitStack
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, AsyncContextManager, Awaitable, Callable, ContextManager, Mapping, override
from uuid import uuid4

from greyhorse.enum import Enum, Struct, Unit
from greyhorse.maybe import Maybe, Nothing, Just
from greyhorse.utils.invoke import get_asyncio_loop, invoke_async, invoke_sync, is_like_sync_context_manager, \
    is_like_async_context_manager

type FieldFactory[T] = (
    T | Callable[[], Awaitable[T] | T] |
    AbstractContextManager[T] | AbstractAsyncContextManager[T] |
    Callable[[], AbstractContextManager[T]] | Callable[[], AbstractAsyncContextManager[T]]
)


type ContextManagerLike[T] = (
    AbstractContextManager[T] | AbstractAsyncContextManager[T] |
    Callable[[], AbstractContextManager[T]] | Callable[[], AbstractAsyncContextManager[T]]
)


class ContextState[T](Enum):
    Idle = Unit()
    InUse = Struct(count=int, value=T)
    Applied = Struct(count=int, value=T)
    Cancelled = Struct(count=int, value=T)


@dataclass(slots=True, frozen=True)
class ContextData[T]:
    factory: Callable[[...], T]
    ident: str = field(default_factory=lambda: str(uuid4()))
    field_factories: dict[str, FieldFactory[Any]] = field(default_factory=dict)
    finalizers: list[Callable[[], Awaitable[None] | None]] = field(default_factory=list)


class InvalidContextState(RuntimeError):
    pass


class Context(object):
    __slots__ = ('_state', '_data', '_parent', '_prev')

    def __init__(
        self, factory: Callable[[...], Any],
        fields: Mapping[str, FieldFactory[Any]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
    ):
        self._state = ContextState[Any].Idle
        self._data = ContextData(
            factory=factory, field_factories=fields or {},
            finalizers=finalizers or [],
        )
        self._parent: Maybe[Context] = Nothing
        self._prev: Maybe[Context] = Nothing

    @property
    def ident(self) -> str:
        return self._data.ident

    def __enter__(self) -> Any:
        raise NotImplementedError

    def __exit__(self, exc_type, exc_value, traceback):
        raise NotImplementedError

    async def __aenter__(self) -> Any:
        raise NotImplementedError

    async def __aexit__(self, exc_type, exc_value, traceback):
        raise NotImplementedError

    def children(self) -> list[Context]:
        raise NotImplementedError


class MutContext(Context, ABC):
    @abstractmethod
    def apply(self) -> Awaitable[None] | None:
        ...

    @abstractmethod
    def cancel(self) -> Awaitable[None] | None:
        ...

    @abstractmethod
    def mutable_children(self) -> list[MutContext]:
        ...


class _ContextStorage(threading.local):
    __slots__ = ('_storage',)

    def __init__(self):
        self._storage: dict[type, list[Context]] = defaultdict(list)

    def add(self, kind: type, instance: Context):
        self._storage[kind].append(instance)

    def remove(self, kind: type, instance: Context):
        self._storage[kind].remove(instance)

    def get_last(self, kind: type) -> Maybe[Context]:
        if objects := self._storage.get(kind, []):
            return Just(objects[0])
        return Nothing


_current_context: ContextVar[Context] = ContextVar('_ctx')
_context_storage = _ContextStorage()


def current_context(kind: type | None = None) -> Maybe[Context]:
    if kind is None:
        return Maybe(_current_context.get(None))
    else:
        return _context_storage.get_last(kind)


def current_scope_id(kind: type | None = None) -> str:
    if kind is None:
        if ctx := _current_context.get(None):
            return ctx.ident
    else:
        if ctx := _context_storage.get_last(kind):
            return ctx.unwrap().ident

    if loop := get_asyncio_loop():
        return f'asyncio:{id(asyncio.current_task(loop))}'
    else:
        return f'thread:{threading.current_thread().ident}'


class SyncContext[T](Context, ContextManager):
    __slots__ = (
        '_sync_stack', '_context_managers', '_children', '_lock',
    )

    def __init__(
        self, factory: Callable[[...], T],
        fields: dict[str, FieldFactory[T]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
        contexts: list[ContextManagerLike[T]] | None = None,
    ):
        fields = fields.copy() if fields else {}
        children: list[SyncContext] = []
        context_managers: list[tuple[ContextManagerLike, str | None]] = []

        if contexts:
            for ctx in contexts:
                if is_like_sync_context_manager(ctx):
                    context_managers.append((ctx, None))

        names_to_remove = set()

        for name, value in fields.items():
            if isinstance(value, SyncContext):
                children.append(value)
                names_to_remove.add(name)
            if is_like_sync_context_manager(value):
                context_managers.append((value, name))
                names_to_remove.add(name)
            elif is_like_async_context_manager(value):
                names_to_remove.add(name)

        for name in names_to_remove:
            fields.pop(name)

        super().__init__(factory, fields, finalizers)
        self._sync_stack = ExitStack()
        self._context_managers = context_managers
        self._children = children
        self._lock = threading.Lock()

    @override
    def children(self) -> list[Context]:
        return self._children.copy()

    def _switch_to_use(self):
        self._sync_stack.__enter__()
        kwargs: dict[str, Any] = {}

        for ctx, field in self._context_managers:
            if callable(ctx):
                ctx = ctx()
            if value := self._sync_stack.enter_context(ctx):
                if field is not None:
                    kwargs[field] = value

        for name, value in self._data.field_factories.items():
            if callable(value):
                value = invoke_sync(value)
            kwargs[name] = value

        instance = self._create(**kwargs)
        self._prev = Maybe(_current_context.get(None))
        _current_context.set(self)
        self._parent = _context_storage.get_last(type(instance))
        _context_storage.add(type(instance), self)

        return instance

    def _switch_to_idle(self, instance: T, exc_type, exc_value, traceback):
        _context_storage.remove(type(instance), self)

        try:
            self._destroy(instance)
        except Exception:
            pass

        try:
            self._sync_stack.__exit__(exc_type, exc_value, traceback)
        except Exception:
            pass

        for finalizer in self._data.finalizers:
            try:
                invoke_sync(finalizer)
            except Exception:
                pass

        _current_context.set(self._prev.unwrap_or_none())
        self._prev = self._parent = Nothing

    def _create(self, **kwargs) -> T:
        return self._data.factory(**kwargs)

    def _destroy(self, instance: T):
        del instance

    def _enter(self, instance: T):
        pass

    def _exit(self, instance: T, exc_type, exc_value, traceback):
        pass

    def _nested_enter(self, instance: T):
        pass

    def _nested_exit(self, instance: T, exc_type, exc_value, traceback):
        pass

    @override
    def __enter__(self) -> T:
        with self._lock:
            match self._state:
                case ContextState.Idle:
                    value = self._switch_to_use()
                    self._enter(value)
                    self._state = ContextState[type(value)].InUse(count=1, value=value)
                    return value

                case ContextState.InUse(count, value):
                    self._nested_enter(value)
                    self._state = ContextState[type(value)].InUse(count=count + 1, value=value)
                    return value

                case ContextState.Applied(count, value):
                    self._nested_enter(value)
                    self._state = ContextState[type(value)].InUse(count=count + 1, value=value)
                    return value

                case ContextState.Cancelled(count, value):
                    self._nested_enter(value)
                    self._state = ContextState[type(value)].InUse(count=count + 1, value=value)
                    return value

    @override
    def __exit__(self, exc_type, exc_value, traceback):
        with self._lock:
            match self._state:
                case ContextState.Idle:
                    raise InvalidContextState('Context exit on idle state')

                case ContextState.InUse(count, value) \
                        | ContextState.Applied(count, value) \
                        | ContextState.Cancelled(count, value):
                    if count > 1:
                        self._nested_exit(value, exc_type, exc_value, traceback)
                        self._state = self._state.__class__(count=count - 1, value=value)
                    else:
                        self._exit(value, exc_type, exc_value, traceback)
                        self._switch_to_idle(value, exc_type, exc_value, traceback)
                        self._state = ContextState[type(value)].Idle


class SyncMutContext[T](SyncContext[T], MutContext, ABC):
    __slots__ = (
        '_mut_children', '_force_rollback', '_auto_apply',
    )

    def __init__(
        self, factory: Callable[[...], T],
        fields: dict[str, FieldFactory[T]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
        contexts: list[ContextManagerLike[T]] | None = None,
        force_rollback: bool = False, auto_apply: bool = False,
    ):
        super().__init__(factory, fields, finalizers, contexts)
        self._mut_children = []
        self._force_rollback = force_rollback
        self._auto_apply = auto_apply

        for child in self._children:
            if isinstance(child, SyncMutContext):
                self._mut_children.append(child)

    @override
    def mutable_children(self) -> list[MutContext]:
        return self._mut_children.copy()

    def _apply(self, instance: T):
        pass

    def _cancel(self, instance: T):
        pass

    @override
    def apply(self) -> None:
        with self._lock:
            match self._state:
                case ContextState.Idle:
                    raise InvalidContextState('MutContext apply on idle state')

                case ContextState.InUse(count, value):
                    for child in self._mut_children:
                        child.apply()
                    self._apply(value)
                    self._state = ContextState[type(value)].Applied(count=count, value=value)

                case ContextState.Applied(_, _):
                    pass

                case ContextState.Cancelled(_, _):
                    raise InvalidContextState('MutContext apply on cancelled state')

    @override
    def cancel(self) -> None:
        with self._lock:
            match self._state:
                case ContextState.Idle:
                    raise InvalidContextState('MutContext cancel on idle state')

                case ContextState.InUse(count, value):
                    for child in self._mut_children:
                        child.cancel()
                    self._cancel(value)
                    self._state = ContextState[type(value)].Cancelled(count=count, value=value)

                case ContextState.Applied(_, _):
                    raise InvalidContextState('MutContext cancel on applied state')

                case ContextState.Cancelled(_, _):
                    pass

    @override
    def _exit(self, *args):
        if self._force_rollback or args[0] is not None:
            self.cancel()
        elif self._auto_apply:
            self.apply()


class AsyncContext[T](Context, AsyncContextManager):
    __slots__ = (
        '_sync_stack', '_async_stack',
        '_sync_sub_contexts', '_async_sub_contexts',
        '_sync_children', '_async_children', '_lock',
    )

    def __init__(
        self, factory: Callable[[...], T],
        fields: dict[str, FieldFactory[T]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
        contexts: list[ContextManagerLike[T]] | None = None,
    ):
        fields = fields.copy() if fields else {}
        sync_children: list[SyncContext] = []
        async_children: list[AsyncContext] = []
        sync_sub_contexts: list[tuple[ContextManagerLike[T], str | None]] = []
        async_sub_contexts: list[tuple[ContextManagerLike[T], str | None]] = []

        if contexts:
            for ctx in contexts:
                if is_like_async_context_manager(ctx):
                    async_sub_contexts.append((ctx, None))
                elif is_like_sync_context_manager(ctx):
                    sync_sub_contexts.append((ctx, None))

        names_to_remove = set()

        for name, value in fields.items():
            if isinstance(value, AsyncContext):
                async_children.append(value)
                names_to_remove.add(name)
            elif isinstance(value, SyncContext):
                sync_children.append(value)
                names_to_remove.add(name)
            if is_like_async_context_manager(value):
                async_sub_contexts.append((value, name))
                names_to_remove.add(name)
            elif is_like_sync_context_manager(value):
                sync_sub_contexts.append((value, name))
                names_to_remove.add(name)

        for name in names_to_remove:
            fields.pop(name)

        super().__init__(factory, fields, finalizers)
        self._sync_stack = ExitStack()
        self._async_stack = AsyncExitStack()
        self._sync_sub_contexts = sync_sub_contexts
        self._async_sub_contexts = async_sub_contexts
        self._sync_children = sync_children
        self._async_children = async_children
        self._lock = asyncio.Lock()

    @override
    def children(self) -> list[Context]:
        return self._sync_children.copy() + self._async_children.copy()

    async def _switch_to_use(self):
        self._sync_stack.__enter__()
        await self._async_stack.__aenter__()
        kwargs: dict[str, Any] = {}

        for ctx, field in self._sync_sub_contexts:
            if callable(ctx):
                ctx = ctx()
            if value := self._sync_stack.enter_context(ctx):
                if field is not None:
                    kwargs[field] = value

        for ctx, field in self._async_sub_contexts:
            if callable(ctx):
                ctx = ctx()
            if value := await self._async_stack.enter_async_context(ctx):
                if field is not None:
                    kwargs[field] = value

        for name, value in self._data.field_factories.items():
            if callable(value):
                value = await invoke_async(value)
            kwargs[name] = value

        instance = await self._create(**kwargs)
        self._prev = Maybe(_current_context.get(None))
        _current_context.set(self)
        self._parent = _context_storage.get_last(type(instance))
        _context_storage.add(type(instance), self)

        return instance

    async def _switch_to_idle(self, instance: T, exc_type, exc_value, traceback):
        _context_storage.remove(type(instance), self)

        try:
            await self._destroy(instance)
        except Exception:
            pass

        try:
            await self._async_stack.__aexit__(exc_type, exc_value, traceback)
        except Exception:
            pass

        try:
            self._sync_stack.__exit__(exc_type, exc_value, traceback)
        except Exception:
            pass

        for finalizer in self._data.finalizers:
            try:
                await invoke_async(finalizer)
            except Exception:
                pass

        _current_context.set(self._prev.unwrap_or_none())
        self._prev = self._parent = Nothing

    async def _create(self, **kwargs) -> T:
        return self._data.factory(**kwargs)

    async def _destroy(self, instance: T):
        del instance

    async def _enter(self, instance: T):
        pass

    async def _exit(self, instance: T, exc_type, exc_value, traceback):
        pass

    async def _nested_enter(self, instance: T):
        pass

    async def _nested_exit(self, instance: T, exc_type, exc_value, traceback):
        pass

    @override
    async def __aenter__(self) -> T:
        async with self._lock:
            match self._state:
                case ContextState.Idle:
                    value = await self._switch_to_use()
                    await self._enter(value)
                    self._state = ContextState[type(value)].InUse(count=1, value=value)
                    return value

                case ContextState.InUse(count, value):
                    await self._nested_enter(value)
                    self._state = ContextState[type(value)].InUse(count=count + 1, value=value)
                    return value

                case ContextState.Applied(count, value):
                    await self._nested_enter(value)
                    self._state = ContextState[type(value)].InUse(count=count + 1, value=value)
                    return value

                case ContextState.Cancelled(count, value):
                    await self._nested_enter(value)
                    self._state = ContextState[type(value)].InUse(count=count + 1, value=value)
                    return value

    @override
    async def __aexit__(self, exc_type, exc_value, traceback):
        async with self._lock:
            match self._state:
                case ContextState.Idle:
                    raise InvalidContextState('Context exit on idle state')

                case ContextState.InUse(count, value) \
                        | ContextState.Applied(count, value) \
                        | ContextState.Cancelled(count, value):
                    if count > 1:
                        await self._nested_exit(value, exc_type, exc_value, traceback)
                        self._state = self._state.__class__(count=count - 1, value=value)
                    else:
                        await self._exit(value, exc_type, exc_value, traceback)
                        await self._switch_to_idle(value, exc_type, exc_value, traceback)
                        self._state = ContextState[type(value)].Idle


class AsyncMutContext[T](AsyncContext[T], MutContext, ABC):
    __slots__ = (
        '_sync_mut_children', '_async_mut_children', '_force_rollback', '_auto_apply',
    )

    def __init__(
        self, factory: Callable[[...], T],
        fields: dict[str, FieldFactory[T]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
        contexts: list[ContextManagerLike[T]] | None = None,
        force_rollback: bool = False, auto_apply: bool = False,
    ):
        super().__init__(factory, fields, finalizers, contexts)
        self._sync_mut_children = []
        self._async_mut_children = []
        self._force_rollback = force_rollback
        self._auto_apply = auto_apply

        for child in self._sync_children:
            if isinstance(child, SyncMutContext):
                self._sync_mut_children.append(child)

        for child in self._async_children:
            if isinstance(child, AsyncMutContext):
                self._async_mut_children.append(child)

    @override
    def mutable_children(self) -> list[MutContext]:
        return self._sync_mut_children.copy() + self._async_mut_children.copy()

    async def _apply(self, instance: T):
        pass

    async def _cancel(self, instance: T):
        pass

    @override
    async def apply(self) -> None:
        async with self._lock:
            match self._state:
                case ContextState.Idle:
                    raise InvalidContextState('MutContext apply on idle state')

                case ContextState.InUse(count, value):
                    for child in self._sync_mut_children:
                        child.apply()
                    for child in self._async_mut_children:
                        await child.apply()
                    await self._apply(value)
                    self._state = ContextState[type(value)].Applied(count=count, value=value)

                case ContextState.Applied(_, _):
                    pass

                case ContextState.Cancelled(_, _):
                    raise InvalidContextState('MutContext apply on cancelled state')

    @override
    async def cancel(self) -> None:
        async with self._lock:
            match self._state:
                case ContextState.Idle:
                    raise InvalidContextState('MutContext cancel on idle state')

                case ContextState.InUse(count, value):
                    for child in self._sync_mut_children:
                        child.cancel()
                    for child in self._async_mut_children:
                        await child.cancel()
                    await self._cancel(value)
                    self._state = ContextState[type(value)].Cancelled(count=count, value=value)

                case ContextState.Applied(_, _):
                    raise InvalidContextState('MutContext cancel on applied state')

                case ContextState.Cancelled(_, _):
                    pass

    @override
    async def _exit(self, *args):
        if self._force_rollback or args[0] is not None:
            await self.cancel()
        elif self._auto_apply:
            await self.apply()


class ContextBuilder[T]:
    def __init__(
        self, factory: Callable[[...], T],
        class_: type[SyncContext[T] | AsyncContext[T] | SyncMutContext[T] | AsyncMutContext[T]],
        **kwargs: dict[str, Any],
    ):
        self._factory = factory
        self._fields = {}
        self._finalizers = []
        self._contexts = []
        self._class = class_
        self._kwargs = kwargs

    def add_param(self, name: str, value: FieldFactory[T]):
        self._fields[name] = value

    def add_context(self, context: ContextManagerLike[T]):
        self._contexts.append(context)

    def add_finalizer(self, finalizer: Callable[[], Awaitable[None] | None]):
        self._finalizers.append(finalizer)

    def build(self):
        return self._class(
            factory=self._factory, fields=self._fields,
            finalizers=self._finalizers, contexts=self._contexts,
            **self._kwargs,
        )


def context_builder[T](
    class_: type[SyncContext[T] | AsyncContext[T] | SyncMutContext[T] | AsyncMutContext[T]],
    type_: type[T], factory: Callable[[...], T] | T, **kwargs: dict[str, Any],
):
    return ContextBuilder[type_](factory, class_[type_], **kwargs)
