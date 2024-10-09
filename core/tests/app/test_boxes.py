from collections.abc import Generator
from copy import deepcopy
from functools import partial
from unittest.mock import Mock

from faker import Faker
from greyhorse.app.abc.providers import BorrowError, BorrowMutError, ForwardError
from greyhorse.app.boxes import (
    FactoryGenBox,
    ForwardBox,
    ForwardGenBox,
    MutCtxRefBox,
    MutGenBox,
    MutRefBox,
    OwnerCtxRefBox,
    OwnerRefBox,
    SharedCtxRefBox,
    SharedGenBox,
    SharedRefBox,
)
from greyhorse.app.contexts import (
    MutCtxCallbacks,
    SyncContext,
    SyncMutContext,
    SyncMutContextWithCallbacks,
)
from greyhorse.maybe import Just


def test_shared() -> None:
    instance = SharedRefBox[int](lambda: 123)

    res = instance.borrow()
    assert res.is_ok()

    res = instance.borrow()
    assert res.is_ok()

    unwrapped = res.unwrap()
    assert unwrapped == 123
    instance.reclaim(unwrapped)


def test_mut() -> None:
    instance = MutRefBox[int](lambda: 123)

    res = instance.acquire()
    assert res.is_ok()
    unwrapped = res.unwrap()

    res = instance.acquire()
    assert res.is_err()
    assert res.unwrap_err() == BorrowMutError.AlreadyBorrowed(name='int')

    instance.release(unwrapped)

    res = instance.acquire()
    assert res.is_ok()

    assert res.unwrap() == 123


def test_owner() -> None:
    instance = OwnerRefBox[int, str](lambda: 123, lambda: '123')

    res = instance.borrow()
    assert res.is_ok()

    res = instance.borrow()
    assert res.is_ok()

    unwrapped = res.unwrap()
    assert unwrapped == 123

    res = instance.acquire()
    assert res.is_err()
    assert res.unwrap_err() == BorrowMutError.BorrowedAsImmutable(name='str')

    instance.reclaim(unwrapped)
    instance.reclaim(unwrapped)

    res = instance.acquire()
    assert res.is_ok()

    unwrapped = res.unwrap()
    assert unwrapped == '123'

    res = instance.borrow()
    assert res.is_err()
    assert res.unwrap_err() == BorrowError.BorrowedAsMutable(name='int')

    instance.release(unwrapped)

    res = instance.borrow()
    assert res.is_ok()

    unwrapped = res.unwrap()
    assert unwrapped == 123


def test_shared_context() -> None:
    instance = SharedCtxRefBox[int](SyncContext, lambda: 123)

    res = instance.borrow()
    assert res.is_ok()

    res = instance.borrow()
    assert res.is_ok()

    ctx = res.unwrap()
    assert isinstance(ctx, SyncContext)

    with ctx as data:
        assert data == 123


def test_mut_context() -> None:
    instance = MutCtxRefBox[int](SyncMutContext, lambda: 123)

    res = instance.acquire()
    assert res.is_ok()
    unwrapped = res.unwrap()

    res = instance.acquire()
    assert res.is_err()
    assert res.unwrap_err() == BorrowMutError.AlreadyBorrowed(name='int')

    instance.release(unwrapped)

    res = instance.acquire()
    assert res.is_ok()

    ctx = res.unwrap()
    assert isinstance(ctx, SyncMutContext)

    with ctx as data:
        assert data == 123


def test_owner_context() -> None:
    instance = OwnerCtxRefBox[int, str](SyncContext, SyncMutContext, lambda: 123, lambda: '123')

    res = instance.borrow()
    assert res.is_ok()

    res = instance.borrow()
    assert res.is_ok()

    ctx = res.unwrap()
    assert isinstance(ctx, SyncContext)

    with ctx as data:
        assert data == 123

    res = instance.acquire()
    assert res.is_err()
    assert res.unwrap_err() == BorrowMutError.BorrowedAsImmutable(name='str')

    instance.reclaim(ctx)
    instance.reclaim(ctx)

    res = instance.acquire()
    assert res.is_ok()

    mut_ctx = res.unwrap()
    assert isinstance(mut_ctx, SyncMutContext)

    with mut_ctx as data:
        assert data == '123'

    res = instance.borrow()
    assert res.is_err()
    assert res.unwrap_err() == BorrowError.BorrowedAsMutable(name='int')

    instance.release(mut_ctx)

    res = instance.borrow()
    assert res.is_ok()

    ctx = res.unwrap()
    assert isinstance(ctx, SyncContext)

    with ctx as data:
        assert data == 123


def test_owning_context_read_write() -> None:
    value = {'counter': 1}

    instance = OwnerCtxRefBox[dict, dict](
        SyncContext,
        SyncMutContextWithCallbacks,
        partial(deepcopy, value),
        partial(deepcopy, value),
        mut_params=dict(callbacks=MutCtxCallbacks(on_apply=Just(lambda v: value.update(v)))),
    )

    res = instance.borrow()
    assert res.is_ok()

    ctx = res.unwrap()
    assert isinstance(ctx, SyncContext)

    with ctx as data:
        assert data == {'counter': 1}

    instance.reclaim(ctx)

    res = instance.acquire()
    assert res.is_ok()

    mut_ctx = res.unwrap()
    assert isinstance(mut_ctx, SyncMutContext)

    with mut_ctx as data:
        assert data == {'counter': 1}
        data['counter'] += 1

    instance.release(mut_ctx)

    res = instance.borrow()
    assert res.is_ok()

    ctx = res.unwrap()
    assert isinstance(ctx, SyncContext)

    with ctx as data:
        assert data == {'counter': 1}

    instance.reclaim(ctx)

    res = instance.acquire()
    assert res.is_ok()

    mut_ctx = res.unwrap()
    assert isinstance(mut_ctx, SyncMutContext)

    with mut_ctx as data:
        assert data == {'counter': 1}
        data['counter'] += 1
        mut_ctx.apply()

    instance.release(mut_ctx)

    res = instance.borrow()
    assert res.is_ok()

    ctx = res.unwrap()
    assert isinstance(ctx, SyncContext)

    with ctx as data:
        assert data == {'counter': 2}


def test_forward() -> None:
    instance = ForwardBox[int]()

    assert not instance

    res = instance.take()
    assert res.is_err()
    assert res.unwrap_err() == ForwardError.Empty(name='int')

    instance.accept(123)

    assert instance

    res = instance.take()
    assert res.is_ok()

    assert not instance

    unwrapped = res.unwrap()
    assert unwrapped == 123

    res = instance.take()
    assert res.is_err()
    assert res.unwrap_err() == ForwardError.Empty(name='int')

    instance.drop(unwrapped)


def test_shared_gen(faker: Faker) -> None:
    gen_mock = Mock()

    def gen() -> Generator[str, str, None]:
        gen_mock()
        yield faker.pystr()
        gen_mock()

    instance = SharedGenBox[str](gen)

    res = instance.borrow()
    assert res.is_ok()

    gen_mock.assert_called_once()
    gen_mock.reset_mock()

    unwrapped = res.unwrap()
    assert isinstance(unwrapped, str)

    res = instance.borrow()
    assert res.is_ok()

    gen_mock.assert_called_once()
    gen_mock.reset_mock()

    instance.reclaim(unwrapped)
    instance.reclaim(res.unwrap())

    assert gen_mock.call_count == 2


def test_mut_gen(faker: Faker) -> None:
    gen_mock = Mock()

    def gen() -> Generator[str, str, None]:
        gen_mock()
        yield faker.pystr()
        gen_mock()

    instance = MutGenBox[str](gen)

    res = instance.acquire()
    assert res.is_ok()

    gen_mock.assert_called_once()
    gen_mock.reset_mock()

    unwrapped = res.unwrap()
    assert isinstance(unwrapped, str)

    res = instance.acquire()
    assert res.is_ok()

    gen_mock.assert_called_once()
    gen_mock.reset_mock()

    instance.release(unwrapped)
    instance.release(res.unwrap())

    assert gen_mock.call_count == 2


def test_factory_gen(faker: Faker) -> None:
    gen_mock = Mock()

    def gen() -> Generator[str, str, None]:
        gen_mock()
        yield faker.pystr()
        gen_mock()

    instance = FactoryGenBox[str](gen)

    res = instance.create()
    assert res.is_ok()

    gen_mock.assert_called_once()
    gen_mock.reset_mock()

    unwrapped = res.unwrap()
    assert isinstance(unwrapped, str)

    res = instance.create()
    assert res.is_ok()

    gen_mock.assert_called_once()
    gen_mock.reset_mock()

    instance.destroy(unwrapped)
    instance.destroy(res.unwrap())

    assert gen_mock.call_count == 2


def test_forward_gen() -> None:
    gen_mock = Mock()

    def gen() -> Generator[int, int, None]:
        gen_mock()
        yield 123
        gen_mock()

    instance = ForwardGenBox[int](gen())

    assert instance

    res = instance.take()
    assert res.is_ok()

    gen_mock.assert_called_once()
    gen_mock.reset_mock()

    assert not instance

    unwrapped = res.unwrap()
    assert unwrapped == 123

    res = instance.take()
    assert res.is_err()
    assert res.unwrap_err() == ForwardError.MovedOut(name='int')

    gen_mock.assert_not_called()
    gen_mock.reset_mock()

    instance.drop(unwrapped)

    gen_mock.assert_called_once()
    gen_mock.reset_mock()

    assert not instance

    res = instance.take()
    assert res.is_err()
    assert res.unwrap_err() == ForwardError.MovedOut(name='int')

    gen_mock.assert_not_called()
