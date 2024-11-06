import contextlib
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from typing import Any, Self, override

from greyhorse.maybe import Just, Maybe, Nothing
from greyhorse.utils.types import TypeWrapper


class TypeFactory[T](TypeWrapper[T], ABC):
    scoped: bool = False
    cache: bool = False

    @abstractmethod
    def create(self, key: type[T]) -> Maybe[T] | Awaitable[Maybe[T]]: ...

    def destroy(self, instance: T) -> None | Awaitable[None]: ...

    def has(self, key: type[T]) -> bool:
        if Any is self.wrapped_type:
            return True
        return issubclass(self.wrapped_type, key)

    @classmethod
    def from_fn(cls, fn: Callable[[T], T]) -> Self:
        return _FnTypeFactory[cls.__wrapped_type__](fn)

    @classmethod
    def from_class(cls, cls_: type[T]) -> Self:
        return _ClassTypeFactory[cls.__wrapped_type__](cls_)

    @classmethod
    def from_instance(cls, instance: T) -> Self:
        return _InstanceTypeFactory[cls.__wrapped_type__](instance)

    @classmethod
    def from_syncgen(cls, gen_fn: Callable[[], Generator[T, T, None]]) -> Self:
        return _SyncGenTypeFactory[cls.__wrapped_type__](gen_fn)

    @classmethod
    def from_asyncgen(cls, gen_fn: Callable[[], AsyncGenerator[T, T]]) -> Self:
        return _AsyncGenTypeFactory[cls.__wrapped_type__](gen_fn)


class _FnTypeFactory[T](TypeFactory[T]):
    __slots__ = ('_fn',)

    def __init__(self, fn: Callable[[T], T]) -> None:
        self._fn = fn

    @override
    def create(self, key: type[T]) -> Maybe[T]:
        return Maybe(self._fn(key))


class _ClassTypeFactory[T](TypeFactory[T]):
    __slots__ = ('_cls',)

    def __init__(self, cls: type[T]) -> None:
        self._cls = cls

    @override
    def create(self, _: type[T]) -> Maybe[T]:
        return Just(self._cls())


class _InstanceTypeFactory[T](TypeFactory[T]):
    __slots__ = ('_instance',)

    cache = True

    def __init__(self, instance: T) -> None:
        self._instance = instance

    @override
    def create(self, _: type[T]) -> Maybe[T]:
        return Just(self._instance)


class _SyncGenTypeFactory[T](TypeFactory[T]):
    __slots__ = ('_gen_fn', '_gens')

    scoped = True

    def __init__(self, generator_fn: Callable[[], Generator[T, T, None]]) -> None:
        self._gen_fn = generator_fn
        self._gens: dict[int, Generator[T, T, None]] = {}

    @override
    def create(self, _: type[T]) -> Maybe[T]:
        gen = self._gen_fn()

        try:
            instance = next(gen)

        except StopIteration as e:
            instance = e.value

        if instance is None:
            return Nothing

        self._gens[id(instance)] = gen
        return Just(instance)

    @override
    def destroy(self, instance: T) -> None:
        key = id(instance)
        if not (gen := self._gens.pop(key, None)):
            return

        with contextlib.suppress(StopIteration):
            gen.send(instance)


class _AsyncGenTypeFactory[T](TypeFactory[T]):
    __slots__ = ('_gen_fn', '_gens')

    scoped = True

    def __init__(self, generator_fn: Callable[[], AsyncGenerator[T, T]]) -> None:
        self._gen_fn = generator_fn
        self._gens: dict[int, AsyncGenerator[T, T]] = {}

    @override
    async def create(self, _: type[T]) -> Maybe[T]:
        gen = self._gen_fn()

        try:
            instance = await anext(gen)

        except StopAsyncIteration:
            instance = None

        if instance is None:
            return Nothing

        self._gens[id(instance)] = gen
        return Just(instance)

    @override
    async def destroy(self, instance: T) -> None:
        key = id(instance)
        if not (gen := self._gens.pop(key, None)):
            return

        with contextlib.suppress(StopAsyncIteration):
            await gen.asend(instance)
