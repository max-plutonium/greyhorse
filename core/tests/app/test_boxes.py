from greyhorse.app.abc.providers import BorrowError, BorrowMutError, ForwardError
from greyhorse.app.boxes import SharedRefBox, MutRefBox, OwnerRefBox, SharedCtxRefBox, MutCtxRefBox, OwnerCtxRefBox, \
    ForwardBox
from greyhorse.app.contexts import SyncContext, SyncMutContext, SyncMutContextWithCallbacks
from greyhorse.maybe import Just


def test_shared():
    value = Just(123)

    instance = SharedRefBox[int](lambda: value)

    res = instance.borrow()
    assert res.is_ok()

    res = instance.borrow()
    assert res.is_ok()

    unwrapped = res.unwrap()
    assert unwrapped == 123
    instance.reclaim(unwrapped)


def test_mut():
    value = Just(123)

    instance = MutRefBox[int](lambda: value)

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
    value = Just(123)
    mut_value = Just('123')

    instance = OwnerRefBox[int, str](lambda: value, lambda: mut_value)

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
    value = Just(123)

    instance = SharedCtxRefBox[int](SyncContext, lambda: value)

    res = instance.borrow()
    assert res.is_ok()

    res = instance.borrow()
    assert res.is_ok()

    ctx = res.unwrap()
    assert isinstance(ctx, SyncContext)

    with ctx as data:
        assert data == 123


def test_mut_context():
    value = Just(123)

    instance = MutCtxRefBox[int](SyncMutContext, lambda: value)

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
    value = Just(123)
    mut_value = Just('123')

    instance = OwnerCtxRefBox[int, str](SyncContext, SyncMutContext, lambda: value, lambda: mut_value)

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
        lambda: Just(value), lambda: Just(value),
        mut_params=dict(on_apply=lambda v: value.update(v)),
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
