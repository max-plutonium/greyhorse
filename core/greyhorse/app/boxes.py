import contextlib
from collections.abc import Callable, Generator
from copy import deepcopy
from typing import Any, override

from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import (
    BorrowError,
    BorrowMutError,
    FactoryError,
    FactoryProvider,
    ForwardError,
    ForwardProvider,
    MutProvider,
    SharedProvider,
)
from greyhorse.app.contexts import (
    AsyncContext,
    AsyncMutContext,
    ContextBuilder,
    SyncContext,
    SyncMutContext,
)
from greyhorse.maybe import Maybe, Nothing
from greyhorse.result import Err, Ok, Result


class _BasicRefBox:
    __slots__ = ('_shared_counter', '_acq_counter')

    allow_borrow_when_acquired = False
    allow_acq_when_borrowed = False
    allow_multiple_acquisition = False

    def __init__(self) -> None:
        self._shared_counter = 0
        self._acq_counter = 0

    def _borrow[T](self, value: T) -> Result[T, BorrowError]:
        if not self.allow_borrow_when_acquired and self._acq_counter > 0:
            return BorrowError.BorrowedAsMutable(name=type(value).__name__).to_result()
        self._shared_counter += 1
        return Ok(value)

    def _borrow_mut[T](self, value: T) -> Result[T, BorrowMutError]:
        if not self.allow_multiple_acquisition and self._acq_counter > 0:
            return BorrowMutError.AlreadyBorrowed(name=type(value).__name__).to_result()
        if not self.allow_acq_when_borrowed and self._shared_counter > 0:
            return BorrowMutError.BorrowedAsImmutable(name=type(value).__name__).to_result()
        self._acq_counter += 1
        return Ok(value)

    @staticmethod
    def _ensure_maybe(value):
        if not isinstance(value, Maybe):
            value = Maybe(value)
        return value


class SharedRefBox[T](_BasicRefBox, SharedProvider[T]):
    __slots__ = ('_factory', '_copy_maker')

    def __init__(
        self, factory: Callable[[], Maybe[T] | T], copy_maker: Callable[[T], T] = deepcopy
    ) -> None:
        super().__init__()
        self._factory = factory
        self._copy_maker = copy_maker

    @override
    def borrow(self) -> Result[T, BorrowError]:
        return (
            self._ensure_maybe(self._factory())
            .map_or_else(
                lambda: BorrowError.Empty(name=self.wrapped_type.__name__).to_result(),
                self._borrow,
            )
            .map(self._copy_maker)
        )

    @override
    def reclaim(self, instance: T) -> None:
        self._shared_counter -= 1
        del instance


class MutRefBox[T](_BasicRefBox, MutProvider[T]):
    __slots__ = ('_factory', '_copy_maker')

    def __init__(
        self, factory: Callable[[], Maybe[T] | T], copy_maker: Callable[[T], T] = deepcopy
    ) -> None:
        super().__init__()
        self._factory = factory
        self._copy_maker = copy_maker

    @override
    def acquire(self) -> Result[T, BorrowMutError]:
        return (
            self._ensure_maybe(self._factory())
            .map_or_else(
                lambda: BorrowError.Empty(name=self.wrapped_type.__name__).to_result(),
                self._borrow_mut,
            )
            .map(self._copy_maker)
        )

    @override
    def release(self, instance: T) -> None:
        self._acq_counter -= 1
        del instance


class OwnerRefBox[TS, TM](_BasicRefBox, SharedProvider[TS], MutProvider[TM]):
    __slots__ = ('_factory', '_mut_factory', '_copy_maker', '_mut_copy_maker')

    def __init__(
        self,
        factory: Callable[[], Maybe[TS] | TS],
        mut_factory: Callable[[], Maybe[TM] | TM],
        copy_maker: Callable[[TS], TS] = deepcopy,
        mut_copy_maker: Callable[[TM], TM] = deepcopy,
    ) -> None:
        super().__init__()
        self._factory = factory
        self._mut_factory = mut_factory
        self._copy_maker = copy_maker
        self._mut_copy_maker = mut_copy_maker

    @override
    def borrow(self) -> Result[TS, BorrowError]:
        return (
            self._ensure_maybe(self._factory())
            .map_or_else(
                lambda: BorrowError.Empty(name=self.wrapped_type[0].__name__).to_result(),
                self._borrow,
            )
            .map(self._copy_maker)
        )

    @override
    def reclaim(self, instance: TS) -> None:
        self._shared_counter -= 1
        del instance

    @override
    def acquire(self) -> Result[TM, BorrowMutError]:
        return (
            self._ensure_maybe(self._mut_factory())
            .map_or_else(
                lambda: BorrowError.Empty(name=self.wrapped_type[1].__name__).to_result(),
                self._borrow_mut,
            )
            .map(self._mut_copy_maker)
        )

    @override
    def release(self, instance: TM) -> None:
        self._acq_counter -= 1
        del instance


class SharedCtxRefBox[T](_BasicRefBox, SharedProvider[T]):
    __slots__ = ('_kind', '_params', '_factory')

    def __init__(
        self, kind: type[SyncContext[T] | AsyncContext[T]], factory: Callable[[], T], **params
    ) -> None:
        super().__init__()
        self._kind = kind
        self._params = params
        self._factory = factory

    @override
    def borrow(self) -> Result[SyncContext[T] | AsyncContext[T], BorrowError]:
        if not self.allow_borrow_when_acquired and self._acq_counter > 0:
            return BorrowError.BorrowedAsMutable(name=self.wrapped_type.__name__).to_result()
        self._shared_counter += 1

        ctx_builder = ContextBuilder[self._kind, self.wrapped_type](
            self._factory, **self._params
        )
        return Ok(ctx_builder.build())

    @override
    def reclaim(self, instance: SyncContext[T] | AsyncContext[T]) -> None:
        self._shared_counter -= 1
        del instance


class MutCtxRefBox[T](_BasicRefBox, MutProvider[T]):
    __slots__ = ('_mut_kind', '_params', '_factory')

    def __init__(
        self,
        mut_kind: type[SyncMutContext[T] | AsyncMutContext[T]],
        factory: Callable[[], T],
        **params,
    ) -> None:
        super().__init__()
        self._mut_kind = mut_kind
        self._params = params
        self._factory = factory

    @override
    def acquire(self) -> Result[SyncMutContext[T] | AsyncMutContext[T], BorrowMutError]:
        if not self.allow_multiple_acquisition and self._acq_counter > 0:
            return BorrowMutError.AlreadyBorrowed(name=self.wrapped_type.__name__).to_result()
        if not self.allow_acq_when_borrowed and self._shared_counter > 0:
            return BorrowMutError.BorrowedAsImmutable(
                name=self.wrapped_type.__name__
            ).to_result()
        self._acq_counter += 1

        ctx_builder = ContextBuilder[self._mut_kind, self.wrapped_type](
            self._factory, **self._params
        )
        return Ok(ctx_builder.build())

    @override
    def release(self, instance: SyncMutContext[T] | AsyncMutContext[T]) -> None:
        self._acq_counter -= 1
        del instance


class OwnerCtxRefBox[TS, TM](_BasicRefBox, SharedProvider[TS], MutProvider[TM]):
    __slots__ = ('_kind', '_mut_kind', '_params', '_mut_params', '_factory', '_mut_factory')

    def __init__(
        self,
        kind: type[SyncContext[TS] | AsyncContext[TS]],
        mut_kind: type[SyncMutContext[TM] | AsyncMutContext[TM]],
        factory: Callable[[], TS],
        mut_factory: Callable[[], TM],
        params: dict[str, Any] | None = None,
        mut_params: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self._kind = kind
        self._mut_kind = mut_kind
        self._params = params or {}
        self._mut_params = mut_params or {}
        self._factory = factory
        self._mut_factory = mut_factory

    @override
    def borrow(self) -> Result[SyncContext[TS] | AsyncContext[TS], BorrowError]:
        if not self.allow_borrow_when_acquired and self._acq_counter > 0:
            return BorrowError.BorrowedAsMutable(name=self.wrapped_type[0].__name__).to_result()
        self._shared_counter += 1

        ctx_builder = ContextBuilder[self._kind, self.wrapped_type[0]](
            self._factory, **self._params
        )
        return Ok(ctx_builder.build())

    @override
    def reclaim(self, instance: SyncContext[TS] | AsyncContext[TS]) -> None:
        self._shared_counter -= 1
        del instance

    @override
    def acquire(self) -> Result[SyncMutContext[TM] | AsyncMutContext[TM], BorrowMutError]:
        if not self.allow_multiple_acquisition and self._acq_counter > 0:
            return BorrowMutError.AlreadyBorrowed(
                name=self.wrapped_type[1].__name__
            ).to_result()
        if not self.allow_acq_when_borrowed and self._shared_counter > 0:
            return BorrowMutError.BorrowedAsImmutable(
                name=self.wrapped_type[1].__name__
            ).to_result()
        self._acq_counter += 1

        ctx_builder = ContextBuilder[self._mut_kind, self.wrapped_type[1]](
            self._mut_factory, **self._mut_params
        )
        return Ok(ctx_builder.build())

    @override
    def release(self, instance: SyncMutContext[TM] | AsyncMutContext[TM]) -> None:
        self._acq_counter -= 1
        del instance


class ForwardBox[T](Operator[T], ForwardProvider[T]):
    __slots__ = ('_value',)

    def __init__(self, value: T | None = None) -> None:
        self._value = Maybe(value)

    @override
    def accept(self, value: T) -> bool:
        if self._value.is_just():
            return False
        self._value = Maybe(value)
        return True

    @override
    def revoke(self) -> Maybe[T]:
        value, self._value = self._value, Nothing
        return value

    @override
    def take(self) -> Result[T, ForwardError]:
        value, self._value = self._value, Nothing
        return value.map(Ok).unwrap_or(
            ForwardError.Empty(name=self.wrapped_type.__name__).to_result()
        )

    @override
    def drop(self, instance: T) -> None:
        del instance

    @override
    def __bool__(self) -> bool:
        return self._value.is_just()


class PermanentForwardBox[T](ForwardBox[T]):
    @override
    def take(self) -> Result[T, ForwardError]:
        return self._value.map(Ok).unwrap_or(
            ForwardError.Empty(name=self.wrapped_type.__name__).to_result()
        )

    @override
    def drop(self, instance: T) -> None:
        pass


class SharedGenBox[T](SharedProvider[T]):
    __slots__ = ('_gen_fn', '_gens')

    def __init__(self, generator_fn: Callable[[], Generator[T, T, None]]) -> None:
        self._gen_fn = generator_fn
        self._gens: dict[int, Generator[T, T, None]] = {}

    @override
    def borrow(self) -> Result[T, BorrowError]:
        try:
            gen = self._gen_fn()

        except Exception as e:
            return BorrowError.Unexpected(
                name=self.wrapped_type.__name__, details=str(e)
            ).to_result()

        try:
            instance = next(gen)

        except StopIteration as e:
            instance = e.value

        match instance:
            case Ok(instance):
                pass
            case Err(e):
                if isinstance(e, BorrowError):
                    return e.to_result()
                return BorrowError.Unexpected(
                    name=self.wrapped_type.__name__, details=e.message
                ).to_result()
            case None:
                return BorrowError.InsufficientDeps(name=self.wrapped_type.__name__).to_result()
            case instance:
                pass

        self._gens[id(instance)] = gen
        return Ok(instance)

    @override
    def reclaim(self, instance: T) -> None:
        key = id(instance)
        if not (gen := self._gens.pop(key, None)):
            return

        with contextlib.suppress(StopIteration):
            gen.send(instance)


class MutGenBox[T](MutProvider[T]):
    __slots__ = ('_gen_fn', '_gens')

    def __init__(self, generator_fn: Callable[[], Generator[T, T, None]]) -> None:
        self._gen_fn = generator_fn
        self._gens: dict[int, Generator[T, T, None]] = {}

    @override
    def acquire(self) -> Result[T, BorrowMutError]:
        try:
            gen = self._gen_fn()

        except Exception as e:
            return BorrowMutError.Unexpected(
                name=self.wrapped_type.__name__, details=str(e)
            ).to_result()

        try:
            instance = next(gen)

        except StopIteration as e:
            instance = e.value

        match instance:
            case Ok(instance):
                pass
            case Err(e):
                if isinstance(e, BorrowMutError):
                    return e.to_result()
                return BorrowMutError.Unexpected(
                    name=self.wrapped_type.__name__, details=e.message
                ).to_result()
            case None:
                return BorrowMutError.InsufficientDeps(
                    name=self.wrapped_type.__name__
                ).to_result()
            case instance:
                pass

        self._gens[id(instance)] = gen
        return Ok(instance)

    @override
    def release(self, instance: T) -> None:
        key = id(instance)
        if not (gen := self._gens.pop(key, None)):
            return

        with contextlib.suppress(StopIteration):
            gen.send(instance)


class FactoryGenBox[T](FactoryProvider[T]):
    __slots__ = ('_gen_fn', '_gens')

    def __init__(self, generator_fn: Callable[[], Generator[T, T, None]]) -> None:
        self._gen_fn = generator_fn
        self._gens: dict[int, Generator[T, T, None]] = {}

    @override
    def create(self) -> Result[T, FactoryError]:
        try:
            gen = self._gen_fn()

        except Exception as e:
            return FactoryError.Unexpected(
                name=self.wrapped_type.__name__, details=str(e)
            ).to_result()

        try:
            instance = next(gen)

        except StopIteration as e:
            instance = e.value

        match instance:
            case Ok(instance):
                pass
            case Err(e):
                if isinstance(e, FactoryError):
                    return e.to_result()
                return FactoryError.Unexpected(
                    name=self.wrapped_type.__name__, details=e.message
                ).to_result()
            case None:
                return FactoryError.InsufficientDeps(
                    name=self.wrapped_type.__name__
                ).to_result()
            case instance:
                pass

        self._gens[id(instance)] = gen
        return Ok(instance)

    @override
    def destroy(self, instance: T) -> None:
        key = id(instance)
        if not (gen := self._gens.pop(key, None)):
            return

        with contextlib.suppress(StopIteration):
            gen.send(instance)


class ForwardGenBox[T](ForwardProvider[T]):
    __slots__ = ('_gen', '_moved_out')

    def __init__(self, generator: Generator[T, T, None]) -> None:
        self._gen = generator
        self._moved_out = False

    @override
    def take(self) -> Result[T, ForwardError]:
        if self._moved_out:
            return ForwardError.MovedOut(name=self.wrapped_type.__name__).to_result()

        try:
            instance = next(self._gen)

        except StopIteration as e:
            instance = e.value

        match instance:
            case Ok(instance):
                pass
            case Err(e):
                if isinstance(e, ForwardError):
                    return e.to_result()
                return ForwardError.Unexpected(
                    name=self.wrapped_type.__name__, details=e.message
                ).to_result()
            case None:
                return ForwardError.InsufficientDeps(
                    name=self.wrapped_type.__name__
                ).to_result()
            case instance:
                pass

        self._moved_out = True
        return Ok(instance)

    @override
    def drop(self, instance: T) -> None:
        if not self._moved_out:
            return

        with contextlib.suppress(StopIteration):
            self._gen.send(instance)

    @override
    def __bool__(self) -> bool:
        return not self._moved_out
