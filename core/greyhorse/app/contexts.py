from __future__ import annotations

import asyncio
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Awaitable, Callable, Mapping
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    AsyncExitStack,
    ExitStack,
    suppress,
)
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, AsyncContextManager, ContextManager, override
from uuid import uuid4

from greyhorse.enum import Enum, Struct, Unit
from greyhorse.maybe import Just, Maybe, Nothing
from greyhorse.utils.invoke import (
    get_asyncio_loop,
    invoke_async,
    invoke_sync,
    is_like_async_context_manager,
    is_like_sync_context_manager,
)
from greyhorse.utils.types import TypeWrapper

type FieldFactory[T] = (
    T
    | Callable[[], Awaitable[T] | T]
    | AbstractContextManager[T]
    | AbstractAsyncContextManager[T]
    | Callable[[], AbstractContextManager[T]]
    | Callable[[], AbstractAsyncContextManager[T]]
)


type ContextManagerLike[T] = (
    AbstractContextManager[T]
    | AbstractAsyncContextManager[T]
    | Callable[[], AbstractContextManager[T]]
    | Callable[[], AbstractAsyncContextManager[T]]
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


class Context:
    __slots__ = ('_state', '_data', '_parent', '_prev')

    def __init__(
        self,
        factory: Callable[[...], Any],
        fields: Mapping[str, FieldFactory[Any]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
    ) -> None:
        self._state = ContextState[Any].Idle
        self._data = ContextData(
            factory=factory, field_factories=fields or {}, finalizers=finalizers or []
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
    def apply(self) -> Awaitable[None] | None: ...

    @abstractmethod
    def cancel(self) -> Awaitable[None] | None: ...

    @abstractmethod
    def mutable_children(self) -> list[MutContext]: ...


class _ContextStorage(threading.local):
    __slots__ = ('_storage',)

    def __init__(self) -> None:
        self._storage: dict[type, list[Context]] = defaultdict(list)

    def add(self, kind: type, instance: Context) -> None:
        self._storage[kind].append(instance)

    def remove(self, kind: type, instance: Context) -> None:
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
    return _context_storage.get_last(kind)


def current_scope_id(kind: type | None = None) -> str:
    if kind is None:
        if ctx := _current_context.get(None):
            return ctx.ident
    elif ctx := _context_storage.get_last(kind):
        return ctx.unwrap().ident

    if loop := get_asyncio_loop():
        return f'asyncio:{id(asyncio.current_task(loop))}'
    return f'thread:{threading.current_thread().ident}'


class SyncContext[T](Context, TypeWrapper[T], ContextManager):
    __slots__ = ('_sync_stack', '_context_managers', '_children', '_lock')

    def __init__(
        self,
        factory: Callable[[...], T],
        fields: dict[str, FieldFactory[T]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
        sub_contexts: list[ContextManagerLike[T]] | None = None,
    ) -> None:
        fields = fields.copy() if fields else {}
        self._sync_stack = ExitStack()
        self._lock = threading.Lock()
        self._children: list[SyncContext] = []
        self._sub_contexts: list[tuple[ContextManagerLike, str | None]] = []

        if sub_contexts:
            for ctx in sub_contexts:
                if isinstance(ctx, SyncContext):
                    self._children.append(ctx)
                if is_like_sync_context_manager(ctx):
                    self._sub_contexts.append((ctx, None))

        names_to_remove = set()

        for name, value in fields.items():
            if isinstance(value, SyncContext):
                self._children.append(value)
                names_to_remove.add(name)
            if is_like_sync_context_manager(value):
                self._sub_contexts.append((value, name))
                names_to_remove.add(name)
            elif is_like_async_context_manager(value):
                names_to_remove.add(name)

        for name in names_to_remove:
            fields.pop(name)

        super().__init__(factory, fields, finalizers)

    @override
    def children(self) -> list[Context]:
        return self._children.copy()

    def _switch_to_use(self):
        self._sync_stack.__enter__()
        kwargs: dict[str, Any] = {}

        for ctx, field in self._sub_contexts:
            if callable(ctx):
                ctx = ctx()
            if (value := self._sync_stack.enter_context(ctx)) and field is not None:
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

    def _switch_to_idle(self, instance: T, exc_type, exc_value, traceback) -> None:
        _context_storage.remove(type(instance), self)

        with suppress(Exception):
            self._destroy(instance)

        with suppress(Exception):
            self._sync_stack.__exit__(exc_type, exc_value, traceback)

        for finalizer in self._data.finalizers:
            with suppress(Exception):
                invoke_sync(finalizer)

        _current_context.set(self._prev.unwrap_or_none())
        self._prev = self._parent = Nothing

    def _create(self, **kwargs) -> T:
        return self._data.factory(**kwargs)

    def _destroy(self, instance: T) -> None:
        del instance

    def _enter(self, instance: T) -> None:
        pass

    def _exit(self, instance: T, exc_type, exc_value, traceback) -> None:
        pass

    def _nested_enter(self, instance: T) -> None:
        pass

    def _nested_exit(self, instance: T, exc_type, exc_value, traceback) -> None:
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

                case (
                    ContextState.InUse(count, value)
                    | ContextState.Applied(count, value)
                    | ContextState.Cancelled(count, value)
                ):
                    if count > 1:
                        self._nested_exit(value, exc_type, exc_value, traceback)
                        self._state = self._state.__class__(count=count - 1, value=value)
                    else:
                        self._exit(value, exc_type, exc_value, traceback)
                        self._switch_to_idle(value, exc_type, exc_value, traceback)
                        self._state = ContextState[type(value)].Idle


class SyncMutContext[T](SyncContext[T], MutContext):
    __slots__ = ('_mut_children', '_force_rollback', '_auto_apply')

    def __init__(
        self,
        factory: Callable[[...], T],
        fields: dict[str, FieldFactory[T]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
        sub_contexts: list[ContextManagerLike[T]] | None = None,
        force_rollback: bool = False,
        auto_apply: bool = False,
    ) -> None:
        super().__init__(factory, fields, finalizers, sub_contexts)
        self._mut_children = []
        self._force_rollback = force_rollback
        self._auto_apply = auto_apply

        for child in self._children:
            if isinstance(child, SyncMutContext):
                self._mut_children.append(child)

    @override
    def mutable_children(self) -> list[MutContext]:
        return self._mut_children.copy()

    def _apply(self, instance: T) -> None:
        pass

    def _cancel(self, instance: T) -> None:
        pass

    @override
    def apply(self) -> None:
        with self._lock:
            self._do_apply()

    @override
    def cancel(self) -> None:
        with self._lock:
            self._do_cancel()

    @override
    def _exit(self, instance: T, exc_type, exc_value, traceback) -> None:
        if self._force_rollback or exc_type is not None:
            self._do_cancel()
        elif self._auto_apply:
            self._do_apply()

    def _do_apply(self) -> None:
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

    def _do_cancel(self) -> None:
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


class AsyncContext[T](Context, TypeWrapper[T], AsyncContextManager):
    __slots__ = (
        '_sync_stack',
        '_async_stack',
        '_sync_sub_contexts',
        '_async_sub_contexts',
        '_sync_children',
        '_async_children',
        '_lock',
    )

    def __init__(
        self,
        factory: Callable[[...], T],
        fields: dict[str, FieldFactory[T]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
        sub_contexts: list[ContextManagerLike[T]] | None = None,
    ) -> None:
        fields = fields.copy() if fields else {}
        self._sync_stack = ExitStack()
        self._async_stack = AsyncExitStack()
        self._lock = asyncio.Lock()
        self._sync_children: list[SyncContext] = []
        self._async_children: list[AsyncContext] = []
        self._sync_sub_contexts: list[tuple[ContextManagerLike[T], str | None]] = []
        self._async_sub_contexts: list[tuple[ContextManagerLike[T], str | None]] = []

        if sub_contexts:
            for ctx in sub_contexts:
                if isinstance(ctx, SyncContext):
                    self._sync_children.append(ctx)
                elif isinstance(ctx, AsyncContext):
                    self._async_children.append(ctx)
                if is_like_async_context_manager(ctx):
                    self._async_sub_contexts.append((ctx, None))
                elif is_like_sync_context_manager(ctx):
                    self._sync_sub_contexts.append((ctx, None))

        names_to_remove = set()

        for name, value in fields.items():
            if isinstance(value, SyncContext):
                self._sync_children.append(value)
                names_to_remove.add(name)
            elif isinstance(value, AsyncContext):
                self._async_children.append(value)
                names_to_remove.add(name)
            if is_like_async_context_manager(value):
                self._async_sub_contexts.append((value, name))
                names_to_remove.add(name)
            elif is_like_sync_context_manager(value):
                self._sync_sub_contexts.append((value, name))
                names_to_remove.add(name)

        for name in names_to_remove:
            fields.pop(name)

        super().__init__(factory, fields, finalizers)

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
            if (value := self._sync_stack.enter_context(ctx)) and field is not None:
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

    async def _switch_to_idle(self, instance: T, exc_type, exc_value, traceback) -> None:
        _context_storage.remove(type(instance), self)

        with suppress(Exception):
            await self._destroy(instance)

        with suppress(Exception):
            await self._async_stack.__aexit__(exc_type, exc_value, traceback)

        with suppress(Exception):
            self._sync_stack.__exit__(exc_type, exc_value, traceback)

        for finalizer in self._data.finalizers:
            with suppress(Exception):
                await invoke_async(finalizer)

        _current_context.set(self._prev.unwrap_or_none())
        self._prev = self._parent = Nothing

    async def _create(self, **kwargs) -> T:
        return self._data.factory(**kwargs)

    async def _destroy(self, instance: T) -> None:
        del instance

    async def _enter(self, instance: T) -> None:
        pass

    async def _exit(self, instance: T, exc_type, exc_value, traceback) -> None:
        pass

    async def _nested_enter(self, instance: T) -> None:
        pass

    async def _nested_exit(self, instance: T, exc_type, exc_value, traceback) -> None:
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

                case (
                    ContextState.InUse(count, value)
                    | ContextState.Applied(count, value)
                    | ContextState.Cancelled(count, value)
                ):
                    if count > 1:
                        await self._nested_exit(value, exc_type, exc_value, traceback)
                        self._state = self._state.__class__(count=count - 1, value=value)
                    else:
                        await self._exit(value, exc_type, exc_value, traceback)
                        await self._switch_to_idle(value, exc_type, exc_value, traceback)
                        self._state = ContextState[type(value)].Idle


class AsyncMutContext[T](AsyncContext[T], MutContext):
    __slots__ = ('_sync_mut_children', '_async_mut_children', '_force_rollback', '_auto_apply')

    def __init__(
        self,
        factory: Callable[[...], T],
        fields: dict[str, FieldFactory[T]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
        sub_contexts: list[ContextManagerLike[T]] | None = None,
        force_rollback: bool = False,
        auto_apply: bool = False,
    ) -> None:
        super().__init__(factory, fields, finalizers, sub_contexts)
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

    async def _apply(self, instance: T) -> None:
        pass

    async def _cancel(self, instance: T) -> None:
        pass

    @override
    async def apply(self) -> None:
        async with self._lock:
            await self._do_apply()

    @override
    async def cancel(self) -> None:
        async with self._lock:
            await self._do_cancel()

    @override
    async def _exit(self, instance: T, exc_type, exc_value, traceback) -> None:
        if self._force_rollback or exc_type is not None:
            await self._do_cancel()
        elif self._auto_apply:
            await self._do_apply()

    async def _do_apply(self) -> None:
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

    async def _do_cancel(self) -> None:
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


@dataclass
class CtxCallbacks:
    before_create: Maybe[Callable[[...], Any | Awaitable[Any]]] = Nothing
    after_create: Maybe[Callable[[...], Any | Awaitable[Any]]] = Nothing
    on_destroy: Maybe[Callable[[], Any | Awaitable[Any]]] = Nothing
    on_enter: Maybe[Callable[[...], Any | Awaitable[Any]]] = Nothing
    on_exit: Maybe[Callable[[...], Any | Awaitable[Any]]] = Nothing
    on_nested_enter: Maybe[Callable[[...], Any | Awaitable[Any]]] = Nothing
    on_nested_exit: Maybe[Callable[[...], Any | Awaitable[Any]]] = Nothing


@dataclass
class MutCtxCallbacks(CtxCallbacks):
    on_apply: Maybe[Callable[[...], Any | Awaitable[Any]]] = Nothing
    on_cancel: Maybe[Callable[[...], Any | Awaitable[Any]]] = Nothing


class SyncContextWithCallbacks[T](SyncContext[T]):
    __slots__ = ('_callbacks',)

    def __init__(self, callbacks: CtxCallbacks, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._callbacks = callbacks

    @override
    def _create(self, **kwargs) -> T:
        self._callbacks.before_create.map(lambda f: invoke_sync(f, **kwargs))
        res = self._data.factory(**kwargs)
        self._callbacks.after_create.map(lambda f: invoke_sync(f, res))
        return res

    @override
    def _destroy(self, instance: T) -> None:
        self._callbacks.on_destroy.map(lambda f: invoke_sync(f, instance))  # noqa: F821
        del instance

    @override
    def _enter(self, instance: T) -> None:
        self._callbacks.on_enter.map(lambda f: invoke_sync(f, instance))

    @override
    def _exit(self, instance: T, exc_type, exc_value, traceback) -> None:
        self._callbacks.on_exit.map(
            lambda f: invoke_sync(f, instance, exc_type, exc_value, traceback)
        )

    @override
    def _nested_enter(self, instance: T) -> None:
        self._callbacks.on_nested_enter.map(lambda f: invoke_sync(f, instance))

    @override
    def _nested_exit(self, instance: T, exc_type, exc_value, traceback) -> None:
        self._callbacks.on_nested_exit.map(
            lambda f: invoke_sync(f, instance, exc_type, exc_value, traceback)
        )


class SyncMutContextWithCallbacks[T](SyncMutContext[T]):
    def __init__(self, callbacks: MutCtxCallbacks, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._callbacks = callbacks

    @override
    def _create(self, **kwargs) -> T:
        self._callbacks.before_create.map(lambda f: invoke_sync(f, **kwargs))
        res = self._data.factory(**kwargs)
        self._callbacks.after_create.map(lambda f: invoke_sync(res))
        return res

    @override
    def _destroy(self, instance: T) -> None:
        self._callbacks.on_destroy.map(lambda f: invoke_sync(f, instance))  # noqa: F821
        del instance

    @override
    def _enter(self, instance: T) -> None:
        self._callbacks.on_enter.map(lambda f: invoke_sync(f, instance))

    @override
    def _exit(self, instance: T, exc_type, exc_value, traceback) -> None:
        self._callbacks.on_exit.map(
            lambda f: invoke_sync(f, instance, exc_type, exc_value, traceback)
        )

    @override
    def _nested_enter(self, instance: T) -> None:
        self._callbacks.on_nested_enter.map(lambda f: invoke_sync(f, instance))

    @override
    def _nested_exit(self, instance: T, exc_type, exc_value, traceback) -> None:
        self._callbacks.on_nested_exit.map(
            lambda f: invoke_sync(f, instance, exc_type, exc_value, traceback)
        )

    @override
    def _apply(self, instance: T) -> None:
        self._callbacks.on_apply.map(lambda f: invoke_sync(f, instance))

    @override
    def _cancel(self, instance: T) -> None:
        self._callbacks.on_cancel.map(lambda f: invoke_sync(f, instance))


class AsyncContextWithCallbacks[T](AsyncContext[T]):
    __slots__ = ('_callbacks',)

    def __init__(self, callbacks: CtxCallbacks, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._callbacks = callbacks

    @override
    async def _create(self, **kwargs) -> T:
        await self._callbacks.before_create.map_async(lambda f: invoke_async(f, **kwargs))
        res = self._data.factory(**kwargs)
        await self._callbacks.after_create.map_async(lambda f: invoke_async(f, **kwargs))
        return res

    @override
    async def _destroy(self, instance: T) -> None:
        await self._callbacks.on_destroy.map_async(lambda f: invoke_async(f, instance))  # noqa: F821
        del instance

    @override
    async def _enter(self, instance: T) -> None:
        await self._callbacks.on_enter.map_async(lambda f: invoke_async(f, instance))

    @override
    async def _exit(self, instance: T, exc_type, exc_value, traceback) -> None:
        await self._callbacks.on_exit.map_async(
            lambda f: invoke_async(f, instance, exc_type, exc_value, traceback)
        )

    @override
    async def _nested_enter(self, instance: T) -> None:
        await self._callbacks.on_nested_enter.map_async(lambda f: invoke_async(f, instance))

    @override
    async def _nested_exit(self, instance: T, exc_type, exc_value, traceback) -> None:
        await self._callbacks.on_nested_exit.map_async(
            lambda f: invoke_async(f, instance, exc_type, exc_value, traceback)
        )


class AsyncMutContextWithCallbacks[T](AsyncMutContext[T]):
    def __init__(self, callbacks: MutCtxCallbacks, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._callbacks = callbacks

    @override
    async def _create(self, **kwargs) -> T:
        await self._callbacks.before_create.map_async(lambda f: invoke_async(f, **kwargs))
        res = self._data.factory(**kwargs)
        await self._callbacks.after_create.map_async(lambda f: invoke_async(f, **kwargs))
        return res

    @override
    async def _destroy(self, instance: T) -> None:
        await self._callbacks.on_destroy.map_async(lambda f: invoke_async(f, instance))  # noqa: F821
        del instance

    @override
    async def _enter(self, instance: T) -> None:
        await self._callbacks.on_enter.map_async(lambda f: invoke_async(f, instance))

    @override
    async def _exit(self, instance: T, exc_type, exc_value, traceback) -> None:
        await self._callbacks.on_exit.map_async(
            lambda f: invoke_async(f, instance, exc_type, exc_value, traceback)
        )

    @override
    async def _nested_enter(self, instance: T) -> None:
        await self._callbacks.on_nested_enter.map_async(lambda f: invoke_async(f, instance))

    @override
    async def _nested_exit(self, instance: T, exc_type, exc_value, traceback) -> None:
        await self._callbacks.on_nested_exit.map_async(
            lambda f: invoke_async(f, instance, exc_type, exc_value, traceback)
        )

    @override
    async def _apply(self, instance: T) -> None:
        await self._callbacks.on_apply.map_async(lambda f: invoke_async(f, instance))

    @override
    async def _cancel(self, instance: T) -> None:
        await self._callbacks.on_cancel.map_async(lambda f: invoke_async(f, instance))


class ContextBuilder[T](TypeWrapper[T]):
    def __init__[**P](
        self,
        factory: Callable[P, T],
        fields: dict[str, FieldFactory[T]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
        sub_contexts: list[ContextManagerLike[T]] | None = None,
        **kwargs,
    ) -> None:
        self._factory = factory
        self._fields = fields or {}
        self._finalizers = finalizers or []
        self._sub_contexts = sub_contexts or []
        self._kwargs = kwargs

    def add_param(self, name: str, value: FieldFactory[T]) -> None:
        self._fields[name] = value

    def add_sub_context(self, context: ContextManagerLike[T]) -> None:
        self._sub_contexts.append(context)

    def add_finalizer(self, finalizer: Callable[[], Awaitable[None] | None]) -> None:
        self._finalizers.append(finalizer)

    def build(self):
        return self.wrapped_type(
            factory=self._factory,
            fields=self._fields,
            finalizers=self._finalizers,
            sub_contexts=self._sub_contexts,
            **self._kwargs,
        )

    def __class_getitem__[C: SyncContext | AsyncContext | SyncMutContext | AsyncMutContext](
        cls, args: tuple[type[C], type[T]]
    ) -> ContextBuilder:
        class_, type_ = args
        return super().__class_getitem__(class_[type_])
