from copy import deepcopy
from typing import override

from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import BorrowError, BorrowMutError, SharedProvider, MutProvider
from greyhorse.app.contexts import SyncContext, ContextBuilder, AsyncContext, SyncMutContext, AsyncMutContext, Context, \
    SyncMutContextWithCallbacks, AsyncMutContextWithCallbacks
from greyhorse.maybe import Maybe, Nothing, Just
from greyhorse.result import Result, Ok


class ResourceBox[T](Operator[T]):
    __slots__ = ('_instance',)

    def __init__(self, value: T | None = None):
        self._instance: Maybe[T] = Maybe(value)

    @override
    def accept(self, instance: T) -> bool:
        if self._instance.is_just():
            return False
        self._instance = Just(instance)
        return True

    @override
    def revoke(self) -> Maybe[T]:
        res, self._instance = self._instance, Nothing
        return res


class _SharableResourceBox[T](ResourceBox[T]):
    __slots__ = ('_shared_counter', '_acq_counter')

    allow_borrow_when_acquired = False
    allow_acq_when_borrowed = False
    allow_multiple_acquisition = False

    def __init__(self, value: T | None = None):
        super().__init__(value)
        self._shared_counter = 0
        self._acq_counter = 0

    def _make_copy(self) -> T:
        return deepcopy(self._instance.unwrap())

    def _borrow(self, value: T) -> Result[T, BorrowError]:
        if not self.allow_borrow_when_acquired and self._acq_counter > 0:
            return BorrowError.BorrowedAsMutable(name=self.wrapped_type.__name__).to_result()
        self._shared_counter += 1
        return Ok(self._make_copy())

    def _borrow_mut(self, value: T) -> Result[T, BorrowMutError]:
        if not self.allow_multiple_acquisition and self._acq_counter > 0:
            return BorrowMutError.AlreadyBorrowed(name=self.wrapped_type.__name__).to_result()
        if not self.allow_acq_when_borrowed and self._shared_counter > 0:
            return BorrowMutError.BorrowedAsImmutable(name=self.wrapped_type.__name__).to_result()
        self._acq_counter += 1
        return Ok(value)


class _SyncContextSharableResourceBox[T](_SharableResourceBox[T]):
    def _setter(self, value: T):
        self._instance = Maybe(value)

    @override
    def _borrow(self, value: T) -> Result[SyncContext[T], BorrowError]:
        if not (res := super()._borrow(value)):
            return res

        wrapped_type = self.__wrapped_type__
        while issubclass(wrapped_type, Context):
            wrapped_type = wrapped_type.__wrapped_type__

        ctx_builder = ContextBuilder[SyncContext, wrapped_type](self._make_copy)
        return Ok(ctx_builder.build())

    @override
    def _borrow_mut(self, value: T) -> Result[SyncMutContext[T], BorrowMutError]:
        if not (res := super()._borrow_mut(value)):
            return res

        wrapped_type = self.__wrapped_type__
        while issubclass(wrapped_type, Context):
            wrapped_type = wrapped_type.__wrapped_type__

        ctx_builder = ContextBuilder[SyncMutContextWithCallbacks, wrapped_type](
            self._make_copy, on_apply=self._setter,
        )
        return Ok(ctx_builder.build())


class _AsyncContextSharableResourceBox[T](_SharableResourceBox[T]):
    def _setter(self, value: T):
        self._instance = Maybe(value)

    @override
    def _borrow(self, value: T) -> Result[AsyncContext[T], BorrowError]:
        if not (res := super()._borrow(value)):
            return res

        ctx_builder = ContextBuilder[AsyncContext, self.__wrapped_type__](self._make_copy)
        return Ok(ctx_builder.build())

    @override
    def _borrow_mut(self, value: T) -> Result[AsyncMutContext[T], BorrowMutError]:
        if not (res := super()._borrow_mut(value)):
            return res

        ctx_builder = ContextBuilder[AsyncMutContextWithCallbacks, self.__wrapped_type__](
            self._make_copy, on_apply=self._setter,
        )
        return Ok(ctx_builder.build())


class SharedResourceBox[T](SharedProvider[T], _SharableResourceBox[T]):
    @override
    def borrow(self) -> Result[T, BorrowError]:
        return self._instance.map(self._borrow).unwrap_or(
            BorrowError.Empty(name=self.wrapped_type.__name__).to_result()
        )

    @override
    def reclaim(self, instance: T):
        self._shared_counter -= 1
        del instance


class MutResourceBox[T](MutProvider[T], _SharableResourceBox[T]):
    @override
    def acquire(self) -> Result[T, BorrowMutError]:
        return self._instance.map(self._borrow_mut).unwrap_or(
            BorrowMutError.Empty(name=self.wrapped_type.__name__).to_result()
        )

    @override
    def release(self, instance: T):
        self._acq_counter -= 1
        del instance


class OwnerResourceBox[T](SharedResourceBox[T], MutResourceBox[T]):
    pass


class _SyncContextSharedResourceBox[T](
    _SyncContextSharableResourceBox[T], spec=SharedResourceBox[SyncContext[T]],
):
    pass


class _AsyncContextSharedResourceBox[T](
    _AsyncContextSharableResourceBox[T], spec=SharedResourceBox[AsyncContext[T]],
):
    pass


class _SyncContextMutResourceBox[T](
    _SyncContextSharableResourceBox[T], spec=MutResourceBox[SyncMutContext[T]],
):
    pass


class _AsyncContextMutResourceBox[T](
    _AsyncContextSharableResourceBox[T], spec=MutResourceBox[AsyncMutContext[T]],
):
    pass


class SyncContextOwnerResourceBox[T](
    _SyncContextSharableResourceBox[T], SharedResourceBox, MutResourceBox,
):
    @override
    def borrow(self) -> Result[SyncContext[T], BorrowError]:
        return SharedResourceBox[SyncContext[self.__wrapped_type__]].borrow(self)

    @override
    def reclaim(self, instance: SyncContext[T]):
        return SharedResourceBox[SyncContext[self.__wrapped_type__]].reclaim(self, instance)

    @override
    def acquire(self) -> Result[SyncMutContext[T], BorrowMutError]:
        return MutResourceBox[SyncMutContext[self.__wrapped_type__]].acquire(self)

    @override
    def release(self, instance: SyncMutContext[T]):
        return MutResourceBox[SyncMutContext[self.__wrapped_type__]].release(self, instance)


class AsyncContextOwnerResourceBox[T](
    _AsyncContextSharableResourceBox[T], SharedResourceBox, MutResourceBox,
):
    @override
    def borrow(self) -> Result[AsyncContext[T], BorrowError]:
        return SharedResourceBox[AsyncContext[self.__wrapped_type__]].borrow(self)

    @override
    def reclaim(self, instance: AsyncContext[T]):
        return SharedResourceBox[AsyncContext[self.__wrapped_type__]].reclaim(self, instance)

    @override
    def acquire(self) -> Result[AsyncMutContext[T], BorrowMutError]:
        return MutResourceBox[AsyncMutContext[self.__wrapped_type__]].acquire(self)

    @override
    def release(self, instance: AsyncMutContext[T]):
        return MutResourceBox[AsyncMutContext[self.__wrapped_type__]].release(self, instance)
