from copy import deepcopy
from functools import partial
from typing import override, Callable, Any

from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import BorrowError, BorrowMutError, SharedProvider, MutProvider, ForwardProvider, \
    ForwardError
from greyhorse.app.contexts import SyncContext, ContextBuilder, AsyncContext, SyncMutContext, AsyncMutContext
from greyhorse.maybe import Maybe, Nothing
from greyhorse.result import Result, Ok


class _BasicRefBox:
    __slots__ = ('_shared_counter', '_acq_counter')

    allow_borrow_when_acquired = False
    allow_acq_when_borrowed = False
    allow_multiple_acquisition = False

    def __init__(self):
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


class SharedRefBox[T](_BasicRefBox, SharedProvider[T]):
    __slots__ = ('_getter', '_copy_maker')

    def __init__(
        self, getter: Callable[[], Maybe[T]], copy_maker: Callable[[T], T] = deepcopy,
    ):
        super().__init__()
        self._getter = getter
        self._copy_maker = copy_maker

    @override
    def borrow(self) -> Result[T, BorrowError]:
        return self._getter().map_or_else(
            lambda: BorrowError.Empty(name=self.wrapped_type.__name__).to_result(),
            self._borrow,
        ).map(self._copy_maker)

    @override
    def reclaim(self, instance: T):
        self._shared_counter -= 1
        del instance


class MutRefBox[T](_BasicRefBox, MutProvider[T]):
    __slots__ = ('_getter', '_copy_maker')

    def __init__(
        self, getter: Callable[[], Maybe[T]], copy_maker: Callable[[T], T] = deepcopy,
    ):
        super().__init__()
        self._getter = getter
        self._copy_maker = copy_maker

    @override
    def acquire(self) -> Result[T, BorrowMutError]:
        return self._getter().map_or_else(
            lambda: BorrowError.Empty(name=self.wrapped_type.__name__).to_result(),
            self._borrow_mut,
        ).map(self._copy_maker)

    @override
    def release(self, instance: T):
        self._acq_counter -= 1
        del instance


class OwnerRefBox[TS, TM](_BasicRefBox, SharedProvider[TS], MutProvider[TM]):
    __slots__ = ('_getter', '_mut_getter', '_copy_maker', '_mut_copy_maker')

    def __init__(
        self,
        getter: Callable[[], Maybe[TS]], mut_getter: Callable[[], Maybe[TM]],
        copy_maker: Callable[[TS], TS] = deepcopy, mut_copy_maker: Callable[[TM], TM] = deepcopy,
    ):
        super().__init__()
        self._getter = getter
        self._mut_getter = mut_getter
        self._copy_maker = copy_maker
        self._mut_copy_maker = mut_copy_maker

    @override
    def borrow(self) -> Result[TS, BorrowError]:
        return self._getter().map_or_else(
            lambda: BorrowError.Empty(name=self.wrapped_type[0].__name__).to_result(),
            self._borrow,
        ).map(self._copy_maker)

    @override
    def reclaim(self, instance: TS):
        self._shared_counter -= 1
        del instance

    @override
    def acquire(self) -> Result[TM, BorrowMutError]:
        return self._mut_getter().map_or_else(
            lambda: BorrowError.Empty(name=self.wrapped_type[1].__name__).to_result(),
            self._borrow_mut,
        ).map(self._mut_copy_maker)

    @override
    def release(self, instance: TM):
        self._acq_counter -= 1
        del instance


class SharedCtxRefBox[T](SharedRefBox[T]):
    __slots__ = ('_kind', '_params')

    def __init__(
        self,
        kind: type[SyncContext[T] | AsyncContext[T]],
        getter: Callable[[], Maybe[T]], copy_maker: Callable[[T], T] = deepcopy,
        **params,
    ):
        super().__init__(getter, copy_maker)
        self._kind = kind
        self._params = params

    @override
    def borrow(self) -> Result[SyncContext[T] | AsyncContext[T], BorrowError]:
        return self._getter().map_or_else(
            lambda: BorrowError.Empty(name=self.wrapped_type.__name__).to_result(),
            self._borrow,
        )

    @override
    def _borrow(self, value: T) -> Result[SyncContext[T] | AsyncContext[T], BorrowError]:
        if not (res := super()._borrow(value)):
            return res

        ctx_builder = ContextBuilder[self._kind, self.wrapped_type](
            partial(self._copy_maker, value), **self._params,
        )
        return Ok(ctx_builder.build())


class MutCtxRefBox[T](MutRefBox[T]):
    __slots__ = ('_mut_kind', '_params')

    def __init__(
        self,
        mut_kind: type[SyncMutContext[T] | AsyncMutContext[T]],
        getter: Callable[[], Maybe[T]], copy_maker: Callable[[T], T] = deepcopy,
        **params,
    ):
        super().__init__(getter, copy_maker)
        self._mut_kind = mut_kind
        self._params = params

    @override
    def acquire(self) -> Result[SyncMutContext[T] | AsyncMutContext[T], BorrowMutError]:
        return self._getter().map_or_else(
            lambda: BorrowError.Empty(name=self.wrapped_type.__name__).to_result(),
            self._borrow_mut,
        )

    @override
    def _borrow_mut(self, value: T) -> Result[SyncMutContext[T] | AsyncMutContext[T], BorrowMutError]:
        if not (res := super()._borrow_mut(value)):
            return res

        ctx_builder = ContextBuilder[self._mut_kind, self.wrapped_type](
            partial(self._copy_maker, value), **self._params,
        )
        return Ok(ctx_builder.build())


class OwnerCtxRefBox[TS, TM](OwnerRefBox[TS, TM]):
    __slots__ = ('_kind', '_mut_kind', '_params', '_mut_params')

    def __init__(
        self,
        kind: type[SyncContext[TS] | AsyncContext[TS]],
        mut_kind: type[SyncMutContext[TM] | AsyncMutContext[TM]],
        getter: Callable[[], Maybe[TS]], mut_getter: Callable[[], Maybe[TM]],
        copy_maker: Callable[[TS], TS] = deepcopy, mut_copy_maker: Callable[[TM], TM] = deepcopy,
        params: dict[str, Any] | None = None, mut_params: dict[str, Any] | None = None,
    ):
        super().__init__(getter, mut_getter, copy_maker, mut_copy_maker)
        self._kind = kind
        self._mut_kind = mut_kind
        self._params = params or {}
        self._mut_params = mut_params or {}

    @override
    def borrow(self) -> Result[TS, BorrowError]:
        return self._getter().map_or_else(
            lambda: BorrowError.Empty(name=self.wrapped_type[0].__name__).to_result(),
            self._borrow,
        )

    @override
    def acquire(self) -> Result[TM, BorrowMutError]:
        return self._mut_getter().map_or_else(
            lambda: BorrowError.Empty(name=self.wrapped_type[1].__name__).to_result(),
            self._borrow_mut,
        )

    @override
    def _borrow(self, value: TS) -> Result[SyncContext[TS] | AsyncContext[TS], BorrowError]:
        if not (res := super()._borrow(value)):
            return res

        ctx_builder = ContextBuilder[self._kind, self.wrapped_type[0]](
            partial(self._copy_maker, value), **self._params,
        )
        return Ok(ctx_builder.build())

    @override
    def _borrow_mut(self, value: TM) -> Result[SyncMutContext[TM] | AsyncMutContext[TM], BorrowMutError]:
        if not (res := super()._borrow_mut(value)):
            return res

        ctx_builder = ContextBuilder[self._mut_kind, self.wrapped_type[1]](
            partial(self._copy_maker, value), **self._mut_params,
        )
        return Ok(ctx_builder.build())


class ForwardBox[T](Operator[T], ForwardProvider[T]):
    __slots__ = ('_value',)

    def __init__(self, value: Maybe[T] = Nothing):
        self._value = value

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
    def drop(self, instance: T):
        del instance

    @override
    def __bool__(self) -> bool:
        return self._value.is_just()
