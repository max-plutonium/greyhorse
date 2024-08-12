from greyhorse.app.abc.providers import BorrowError, BorrowMutError
from greyhorse.app.boxes import SharedResourceBox, MutResourceBox, OwnerResourceBox, SyncContextOwnerResourceBox
from greyhorse.app.contexts import SyncContext, SyncMutContext


def test_shared():
    instance = SharedResourceBox[int](123)

    res = instance.borrow()
    assert res.is_ok()

    res = instance.borrow()
    assert res.is_ok()

    assert res.unwrap() == 123


def test_mut():
    instance = MutResourceBox[int](123)

    res = instance.acquire()
    assert res.is_ok()
    unwrapped = res.unwrap()

    res = instance.acquire()
    assert res.is_err()
    assert res.unwrap_err() == BorrowMutError.AlreadyBorrowed(name='int')

    instance.release(unwrapped)

    res = instance.acquire()
    assert res.is_ok()


def test_owning():
    instance = OwnerResourceBox[int](123)

    res = instance.borrow()
    assert res.is_ok()

    res = instance.borrow()
    assert res.is_ok()

    unwrapped = res.unwrap()
    assert unwrapped == 123

    res = instance.acquire()
    assert res.is_err()
    assert res.unwrap_err() == BorrowMutError.BorrowedAsImmutable(name='int')

    instance.reclaim(unwrapped)
    instance.reclaim(unwrapped)

    res = instance.acquire()
    assert res.is_ok()

    unwrapped = res.unwrap()
    assert unwrapped == 123

    res = instance.borrow()
    assert res.unwrap_err() == BorrowError.BorrowedAsMutable(name='int')

    instance.release(unwrapped)

    res = instance.borrow()
    assert res.is_ok()

    unwrapped = res.unwrap()
    assert unwrapped == 123


def test_shared_context():
    instance = SharedResourceBox[SyncContext[int]](123)

    res = instance.borrow()
    assert res.is_ok()

    res = instance.borrow()
    assert res.is_ok()

    ctx = res.unwrap()
    assert isinstance(ctx, SyncContext)
    with ctx as data:
        assert data == 123


def test_mut_context():
    instance = MutResourceBox[SyncMutContext[int]](123)

    res = instance.acquire()
    assert res.is_ok()
    unwrapped = res.unwrap()

    res = instance.acquire()
    assert res.is_err()
    assert res.unwrap_err() == BorrowMutError.AlreadyBorrowed(name='IntSyncMutContext')

    instance.release(unwrapped)

    res = instance.acquire()
    assert res.is_ok()


def test_owning_context():
    instance = SyncContextOwnerResourceBox[int](123)

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
    assert res.unwrap_err() == BorrowMutError.BorrowedAsImmutable(name='int')

    instance.reclaim(ctx)
    instance.reclaim(ctx)

    res = instance.acquire()
    assert res.is_ok()

    mut_ctx = res.unwrap()
    assert isinstance(mut_ctx, SyncContext)
    with mut_ctx as data:
        assert data == 123

    res = instance.borrow()
    assert res.unwrap_err() == BorrowError.BorrowedAsMutable(name='int')

    instance.release(mut_ctx)

    res = instance.borrow()
    assert res.is_ok()

    ctx = res.unwrap()
    assert isinstance(ctx, SyncContext)
    with ctx as data:
        assert data == 123


def test_owning_context_read_write():
    instance = SyncContextOwnerResourceBox[dict]({'data': 1})

    res = instance.borrow()
    assert res.is_ok()
    ctx = res.unwrap()
    assert isinstance(ctx, SyncContext)
    with ctx as data:
        assert data == {'data': 1}

    instance.reclaim(ctx)

    res = instance.acquire()
    assert res.is_ok()
    mut_ctx = res.unwrap()
    assert isinstance(mut_ctx, SyncContext)
    with mut_ctx as data:
        assert data == {'data': 1}
        data['data'] += 1

    instance.release(mut_ctx)

    res = instance.borrow()
    assert res.is_ok()
    ctx = res.unwrap()
    assert isinstance(ctx, SyncContext)
    with ctx as data:
        assert data == {'data': 1}

    instance.reclaim(ctx)

    res = instance.acquire()
    assert res.is_ok()
    mut_ctx = res.unwrap()
    assert isinstance(mut_ctx, SyncContext)
    with mut_ctx as data:
        assert data == {'data': 1}
        data['data'] += 1
        mut_ctx.apply()

    instance.release(mut_ctx)

    res = instance.borrow()
    assert res.is_ok()
    ctx = res.unwrap()
    assert isinstance(ctx, SyncContext)
    with ctx as data:
        assert data == {'data': 2}
