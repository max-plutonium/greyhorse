from copy import deepcopy
from functools import partial

from greyhorse.app.abc.providers import BorrowError, BorrowMutError, ForwardError
from greyhorse.app.boxes import SharedRefBox, MutRefBox, OwnerRefBox, SharedCtxRefBox, MutCtxRefBox, OwnerCtxRefBox, \
    ForwardBox
from greyhorse.app.contexts import SyncContext, SyncMutContext, SyncMutContextWithCallbacks, MutCtxCallbacks
from greyhorse.maybe import Just


def test_shared():
    instance = SharedRefBox[int](lambda: 123)

    res = instance.borrow()
    assert res.is_ok()

    res = instance.borrow()
    assert res.is_ok()

    unwrapped = res.unwrap()
    assert unwrapped == 123
    instance.reclaim(unwrapped)


def test_mut():
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


def test_owner():
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


def test_shared_context():
    instance = SharedCtxRefBox[int](SyncContext, lambda: 123)

    res = instance.borrow()
    assert res.is_ok()

    res = instance.borrow()
    assert res.is_ok()

    ctx = res.unwrap()
    assert isinstance(ctx, SyncContext)

    with ctx as data:
        assert data == 123


def test_mut_context():
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


def test_owner_context():
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


def test_owning_context_read_write():
    value = {'counter': 1}

    instance = OwnerCtxRefBox[dict, dict](
        SyncContext, SyncMutContextWithCallbacks,
        partial(deepcopy, value), partial(deepcopy, value),
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


def test_forward():
    instance = ForwardBox[int]()

    assert not instance

    res = instance.take()
    assert res.is_err()
    assert res.unwrap_err() == ForwardError.Empty(name='int')

    instance.accept(123)

    res = instance.take()
    assert res.is_ok()

    unwrapped = res.unwrap()
    assert unwrapped == 123

    res = instance.take()
    assert res.is_err()
    assert res.unwrap_err() == ForwardError.Empty(name='int')

    instance.drop(unwrapped)
