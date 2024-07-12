import asyncio
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import AbstractAsyncContextManager, AbstractContextManager, AsyncExitStack, ExitStack
from contextvars import ContextVar
from typing import Any, AsyncContextManager, Awaitable, Callable, ContextManager, Mapping, override
from uuid import uuid4

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


class Context(object):
    __slots__ = (
        '_factory', '_field_factories', '_finalizers',
        '_params', '_object', '_ident', '_parent', '_prev',
    )

    def __init__(
        self, factory: Callable[[...], Any] | None = None,
        fields: Mapping[str, FieldFactory[Any]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
    ):
        self._factory = factory
        self._field_factories = fields or {}
        self._finalizers = finalizers or []
        self._params: dict[str, Any] = {}
        self._object = None
        self._ident = str(uuid4())
        self._parent: Context | None = None
        self._prev: Context | None = None

    @property
    def ident(self) -> str:
        return self._ident

    def __enter__(self) -> Any:
        raise NotImplementedError

    def __exit__(self, exc_type, exc_value, traceback):
        raise NotImplementedError

    async def __aenter__(self) -> Any:
        raise NotImplementedError

    async def __aexit__(self, exc_type, exc_value, traceback):
        raise NotImplementedError


class MutContext(Context, ABC):
    @abstractmethod
    def apply(self) -> Awaitable[None] | None:
        ...

    @abstractmethod
    def cancel(self) -> Awaitable[None] | None:
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
        if res := _current_context.get(None):
            return Just(res)
    else:
        return _context_storage.get_last(kind)

    return Nothing


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
        '_sync_stack', '_sub_contexts', '_counter', '_lock',
    )

    def __init__(
        self, factory: Callable[[...], T] | None = None,
        fields: Mapping[str, FieldFactory[T]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
        contexts: list[ContextManagerLike[T]] | None = None,
    ):
        super().__init__(factory, fields, finalizers)
        self._sync_stack = ExitStack()
        self._sub_contexts: list[tuple[ContextManagerLike, str | None]] = []
        self._counter = 0
        self._lock = threading.Lock()

        if contexts:
            for ctx in contexts:
                if is_like_sync_context_manager(ctx):
                    self._sub_contexts.append((ctx, None))

        names_to_remove = []

        for name, factory in self._field_factories.items():
            if is_like_sync_context_manager(factory):
                self._sub_contexts.append((factory, name))
                names_to_remove.append(name)
            elif is_like_async_context_manager(factory):
                names_to_remove.append(name)

        for name in names_to_remove:
            self._field_factories.pop(name)

    def _create(self):
        if self._factory is not None:
            self._object = self._factory(**self._params)

    def _destroy(self):
        del self._object
        self._object = None

    def _enter(self):
        pass

    def _exit(self, *args):
        pass

    def _nested_enter(self):
        pass

    def _nested_exit(self):
        pass

    @override
    def __enter__(self) -> T:
        with self._lock:
            self._counter += 1
            if 1 != self._counter:
                self._nested_enter()
                return self._object

        self._sync_stack.__enter__()

        for ctx, field in self._sub_contexts:
            if callable(ctx):
                ctx = ctx()
            if value := self._sync_stack.enter_context(ctx):
                if field is not None:
                    self._params[field] = value

        for name, value in self._field_factories.items():
            if callable(value):
                value = invoke_sync(value)
            self._params[name] = value

        self._create()
        self._enter()

        self._prev = _current_context.get(None)
        _current_context.set(self)
        self._parent = _context_storage.get_last(type(self._object))
        _context_storage.add(type(self._object), self)
        return self._object

    @override
    def __exit__(self, exc_type, exc_value, traceback):
        with self._lock:
            self._counter = max(self._counter - 1, 0)
            if 0 != self._counter:
                self._nested_exit()
                return

        self._exit(exc_type, exc_value, traceback)
        _context_storage.remove(type(self._object), self)

        try:
            self._destroy()
        except Exception:
            pass

        for name, value in self._field_factories.items():
            self._params.pop(name, None)

        for _, field in self._sub_contexts:
            if field is not None:
                self._params.pop(field, None)

        try:
            self._sync_stack.__exit__(exc_type, exc_value, traceback)
        except Exception:
            pass

        for finalizer in self._finalizers:
            try:
                invoke_sync(finalizer)
            except Exception:
                pass

        _current_context.set(self._prev)
        self._prev = self._parent = None


class SyncMutContext[T](SyncContext[T], MutContext, ABC):
    __slots__ = (
        '_force_rollback', '_auto_apply',
    )

    def __init__(
        self, factory: Callable[[...], T] | None = None,
        fields: Mapping[str, FieldFactory[T]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
        contexts: list[ContextManagerLike[T]] | None = None,
        force_rollback: bool = False, auto_apply: bool = False,
    ):
        super().__init__(factory, fields, finalizers, contexts)
        self._force_rollback = force_rollback
        self._auto_apply = auto_apply

    @override
    def _exit(self, *args):
        if self._force_rollback or args[0] is not None:
            self.cancel()
        elif self._auto_apply:
            self.apply()


class AsyncContext[T](Context, AsyncContextManager):
    __slots__ = (
        '_sync_stack', '_async_stack', '_sync_sub_contexts',
        '_async_sub_contexts', '_counter', '_lock',
    )

    def __init__(
        self, factory: Callable[[...], T] | None = None,
        fields: Mapping[str, FieldFactory[T]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
        contexts: list[ContextManagerLike[T]] | None = None,
    ):
        super().__init__(factory, fields, finalizers)
        self._sync_stack = ExitStack()
        self._async_stack = AsyncExitStack()
        self._sync_sub_contexts: list[tuple[ContextManagerLike[T], str | None]] = []
        self._async_sub_contexts: list[tuple[ContextManagerLike[T], str | None]] = []
        self._counter = 0
        self._lock = asyncio.Lock()

        if contexts:
            for ctx in contexts:
                if is_like_async_context_manager(ctx):
                    self._async_sub_contexts.append((ctx, None))
                elif is_like_sync_context_manager(ctx):
                    self._sync_sub_contexts.append((ctx, None))

        names_to_remove = []

        for name, factory in self._field_factories.items():
            if is_like_async_context_manager(factory):
                self._async_sub_contexts.append((factory, name))
                names_to_remove.append(name)
            elif is_like_sync_context_manager(factory):
                self._sync_sub_contexts.append((factory, name))
                names_to_remove.append(name)

        for name in names_to_remove:
            self._field_factories.pop(name)

    async def _create(self):
        if self._factory is not None:
            self._object = self._factory(**self._params)

    async def _destroy(self):
        del self._object
        self._object = None

    async def _enter(self):
        pass

    async def _exit(self, *args):
        pass

    async def _nested_enter(self):
        pass

    async def _nested_exit(self):
        pass

    @override
    async def __aenter__(self) -> T:
        async with self._lock:
            self._counter += 1
            if 1 != self._counter:
                await self._nested_enter()
                return self._object

        self._sync_stack.__enter__()
        await self._async_stack.__aenter__()

        for ctx, field in self._sync_sub_contexts:
            if callable(ctx):
                ctx = ctx()
            if value := self._sync_stack.enter_context(ctx):
                if field is not None:
                    self._params[field] = value

        for ctx, field in self._async_sub_contexts:
            if callable(ctx):
                ctx = ctx()
            if value := await self._async_stack.enter_async_context(ctx):
                if field is not None:
                    self._params[field] = value

        for name, value in self._field_factories.items():
            if callable(value):
                value = await invoke_async(value)
            self._params[name] = value

        await self._create()
        await self._enter()

        self._prev = _current_context.get(None)
        _current_context.set(self)
        self._parent = _context_storage.get_last(type(self._object))
        _context_storage.add(type(self._object), self)
        return self._object

    @override
    async def __aexit__(self, exc_type, exc_value, traceback):
        async with self._lock:
            self._counter = max(self._counter - 1, 0)
            if 0 != self._counter:
                await self._nested_exit()
                return

        await self._exit(exc_type, exc_value, traceback)
        _context_storage.remove(type(self._object), self)

        try:
            await self._destroy()
        except Exception:
            pass

        for name, value in self._field_factories.items():
            self._params.pop(name, None)

        for _, field in self._async_sub_contexts:
            if field is not None:
                self._params.pop(field, None)

        for _, field in self._sync_sub_contexts:
            if field is not None:
                self._params.pop(field, None)

        try:
            await self._async_stack.__aexit__(exc_type, exc_value, traceback)
        except Exception:
            pass

        try:
            self._sync_stack.__exit__(exc_type, exc_value, traceback)
        except Exception:
            pass

        for finalizer in self._finalizers:
            try:
                await invoke_async(finalizer)
            except Exception:
                pass

        _current_context.set(self._prev)
        self._prev = self._parent = None


class AsyncMutContext[T](AsyncContext[T], MutContext, ABC):
    __slots__ = (
        '_force_rollback', '_auto_apply',
    )

    def __init__(
        self, factory: Callable[[...], T] | None = None,
        fields: Mapping[str, FieldFactory[T]] | None = None,
        finalizers: list[Callable[[], Awaitable[None] | None]] | None = None,
        contexts: list[ContextManagerLike[T]] | None = None,
        force_rollback: bool = False, auto_apply: bool = False,
    ):
        super().__init__(factory, fields, finalizers, contexts)
        self._force_rollback = force_rollback
        self._auto_apply = auto_apply

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
