from unittest import mock

import pytest

from greyhorse.maybe import MaybeUnwrapError, Just, Nothing
from greyhorse.result import Ok, Err


def test_maybe():
    maybe_just = Just(123)
    maybe_none = Nothing

    assert maybe_just.is_just()
    assert not maybe_none.is_just()

    assert maybe_just.is_just_and(lambda v: v == 123)
    assert not maybe_just.is_just_and(lambda v: v == 456)
    assert not maybe_none.is_just_and(lambda v: v == 123)
    assert not maybe_none.is_just_and(lambda v: v == 456)

    assert not maybe_just.is_nothing()
    assert maybe_none.is_nothing()

    assert Ok(123) == maybe_just.ok_or('err')
    assert Err('err') == maybe_none.ok_or('err')

    assert Ok(123) == maybe_just.ok_or_else(lambda: 'err')
    assert Err('err') == maybe_none.ok_or_else(lambda: 'err')

    inspect_mock = mock.Mock()

    assert maybe_just is maybe_just.inspect(inspect_mock)
    assert maybe_none is maybe_none.inspect(inspect_mock)

    inspect_mock.assert_called_once_with(123)

    assert 123 == maybe_just.expect('exception')

    with pytest.raises(MaybeUnwrapError) as excinfo:
        maybe_none.expect('exception')

    assert str(excinfo.value) == 'exception'

    assert 123 == maybe_just.unwrap()

    with pytest.raises(MaybeUnwrapError):
        maybe_none.unwrap()

    assert 123 == maybe_just.unwrap_or(456)
    assert 456 == maybe_none.unwrap_or(456)

    assert 123 == maybe_just.unwrap_or_else(lambda: 789)
    assert 789 == maybe_none.unwrap_or_else(lambda: 789)

    assert 123 == maybe_just.unwrap_or_raise(Exception)

    with pytest.raises(Exception):
        maybe_none.unwrap_or_raise(Exception)

    assert Just(134) == maybe_just.map(lambda i: i + 11)
    assert Nothing is maybe_none.map(lambda i: i + 11)

    assert 124 == maybe_just.map_or(234, lambda i: i + 1)
    assert 234 == maybe_none.map_or(234, lambda i: i + 1)

    assert 125 == maybe_just.map_or_else(lambda: 235, lambda i: i + 2)
    assert 235 == maybe_none.map_or_else(lambda: 235, lambda i: i + 2)

    assert maybe_just is maybe_just.and_(maybe_just)
    assert maybe_none is maybe_just.and_(maybe_none)
    assert maybe_none is maybe_none.and_(maybe_just)
    assert maybe_none is maybe_none.and_(maybe_none)

    assert Just(456) == maybe_just.and_then(lambda v: Just(456))
    assert Nothing is maybe_none.and_then(lambda v: Just(456))

    assert maybe_just is maybe_just.filter(lambda v: v == 123)
    assert Nothing is maybe_just.filter(lambda v: v != 123)
    assert Nothing is maybe_none.filter(lambda v: v == 123)

    assert maybe_just is maybe_just.or_(maybe_just)
    assert maybe_just is maybe_just.or_(maybe_none)
    assert maybe_just is maybe_none.or_(maybe_just)
    assert maybe_none is maybe_none.or_(maybe_none)

    assert maybe_just is maybe_just.or_else(lambda: Just(456))
    assert Just(456) == maybe_none.or_else(lambda: Just(456))

    assert Nothing is maybe_just.xor(maybe_just)
    assert maybe_just is maybe_just.xor(maybe_none)
    assert maybe_just is maybe_none.xor(maybe_just)
    assert Nothing is maybe_none.xor(maybe_none)

    assert maybe_just is maybe_just.flatten()
    assert maybe_just is Just(maybe_just).flatten()
    assert maybe_none is maybe_none.flatten()
    assert maybe_none is Just(maybe_none).flatten()

    assert Ok(maybe_just) == maybe_just.to_result()
    assert Ok(Just(123)) == Just(Ok(123)).to_result()
    assert Err('err') == Just(Err('err')).to_result()
    assert Ok(Nothing) == Nothing.to_result()
