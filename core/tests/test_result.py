from unittest import mock

import pytest

from greyhorse.error import Error, ErrorCase
from greyhorse.maybe import Just, Nothing
from greyhorse.result import ResultUnwrapError, Ok, Err, as_result_sync, as_result_async, Result, do, do_async


class TestError(Error):
    Unexpected = ErrorCase(msg='Unexpected error')


def test_result():
    result_ok = Result(123)
    result_err = Result(TestError.Unexpected())

    assert result_ok
    assert not result_err

    assert result_ok.is_ok()
    assert not result_err.is_ok()

    assert not result_ok.is_err()
    assert result_err.is_err()

    result_ok = Ok(123)
    result_err = Err('err')

    assert result_ok
    assert not result_err

    assert result_ok.is_ok()
    assert not result_err.is_ok()

    assert result_ok.is_ok_and(lambda v: v == 123)
    assert not result_ok.is_ok_and(lambda v: v != 123)
    assert not result_err.is_ok_and(lambda v: v == 123)
    assert not result_err.is_ok_and(lambda v: v != 123)

    assert not result_ok.is_err()
    assert result_err.is_err()

    assert not result_ok.is_err_and(lambda e: e == 'err')
    assert not result_ok.is_err_and(lambda e: e != 'err')
    assert result_err.is_err_and(lambda e: e == 'err')
    assert not result_err.is_err_and(lambda e: e != 'err')

    assert Just(123) == result_ok.ok()
    assert Nothing is result_err.ok()

    assert Nothing is result_ok.err()
    assert Just('err') == result_err.err()

    inspect_mock = mock.Mock()

    assert result_ok is result_ok.inspect(inspect_mock)
    assert result_err is result_err.inspect(inspect_mock)

    inspect_mock.assert_called_once_with(123)

    inspect_mock.reset_mock()

    assert result_ok is result_ok.inspect_err(inspect_mock)
    assert result_err is result_err.inspect_err(inspect_mock)

    inspect_mock.assert_called_once_with('err')

    assert 123 == result_ok.expect('exception')

    with pytest.raises(ResultUnwrapError) as excinfo:
        result_err.expect('exception')

    assert str(excinfo.value) == 'exception'
    assert excinfo.value.value == 'err'

    with pytest.raises(ResultUnwrapError) as excinfo:
        result_ok.expect_err('exception')

    assert str(excinfo.value) == 'exception'
    assert excinfo.value.value == 123

    assert 'err' == result_err.expect_err('exception')

    assert 123 == result_ok.unwrap()

    with pytest.raises(ResultUnwrapError):
        result_err.unwrap()

    with pytest.raises(ResultUnwrapError):
        result_ok.unwrap_err()

    assert 'err' == result_err.unwrap_err()

    assert 123 == result_ok.unwrap_or(456)
    assert 456 == result_err.unwrap_or(456)

    assert 123 == result_ok.unwrap_or_else(lambda e: 789)
    assert 789 == result_err.unwrap_or_else(lambda e: 789)

    assert 123 == result_ok.unwrap_or_raise(Exception)

    with pytest.raises(Exception):
        result_err.unwrap_or_raise(Exception)

    assert Ok(134) == result_ok.map(lambda i: i + 11)
    assert Err('err') == result_err.map(lambda i: i + 11)

    assert 124 == result_ok.map_or(234, lambda i: i + 1)
    assert 234 == result_err.map_or(234, lambda i: i + 1)

    assert 125 == result_ok.map_or_else(lambda e: 235, lambda i: i + 2)
    assert 235 == result_err.map_or_else(lambda e: 235, lambda i: i + 2)

    assert Ok(123) == result_ok.map_err(lambda e: e.upper())
    assert Err('ERR') == result_err.map_err(lambda e: e.upper())

    assert result_ok is result_ok.and_(result_ok)
    assert result_err is result_ok.and_(result_err)
    assert result_err is result_err.and_(result_ok)
    assert result_err is result_err.and_(result_err)

    assert Ok(456) == result_ok.and_then(lambda v: Ok(456))
    assert result_err is result_err.and_then(lambda v: Ok(456))

    assert result_ok is result_ok.or_(result_ok)
    assert result_ok is result_ok.or_(result_err)
    assert result_ok is result_err.or_(result_ok)
    assert result_err is result_err.or_(result_err)

    assert result_ok is result_ok.or_else(lambda e: Ok(456))
    assert Ok(456) == result_err.or_else(lambda e: Ok(456))

    assert result_ok is result_ok.flatten()
    assert result_ok is Ok(result_ok).flatten()
    assert result_err is result_err.flatten()
    assert result_err is Ok(result_err).flatten()

    assert Just(result_ok) == result_ok.to_maybe()
    assert Just(Ok(123)) == Ok(Just(123)).to_maybe()
    assert Just(Err('err')) == Err('err').to_maybe()
    assert Nothing is Ok(Nothing).to_maybe()


def test_as_result_sync():
    @as_result_sync(ValueError, IndexError)
    def f(value: int) -> int:
        if value == 0:
            raise ValueError  # becomes Err
        elif value == 1:
            raise IndexError  # becomes Err
        elif value == 2:
            raise KeyError  # raises Exception
        else:
            return value  # becomes Ok

    assert isinstance(f(0).unwrap_err(), ValueError)
    assert isinstance(f(1).unwrap_err(), IndexError)

    with pytest.raises(Exception):
        f(2)

    assert Ok(3) == f(3)


@pytest.mark.asyncio
async def test_as_result_async():
    @as_result_async(ValueError, IndexError)
    async def f(value: int) -> int:
        if value == 0:
            raise ValueError  # becomes Err
        elif value == 1:
            raise IndexError  # becomes Err
        elif value == 2:
            raise KeyError  # raises Exception
        else:
            return value  # becomes Ok

    assert isinstance((await f(0)).unwrap_err(), ValueError)
    assert isinstance((await f(1)).unwrap_err(), IndexError)

    with pytest.raises(Exception):
        await f(2)

    assert Ok(3) == await f(3)


def test_do_sync():
    def get_result(i: int = 1):
        if i < 3:
            return Ok(i)
        return Err(i)

    final_result: Result[int, str] = do(
        Ok(x + y)
        for x in get_result(1)
        for y in get_result(2)
    )

    assert Ok(3) == final_result

    final_result: Result[int, str] = do(
        Ok(x + y + z)
        for x in get_result(1)
        for y in get_result(2)
        for z in get_result(10)
    )

    assert Err(10) == final_result


@pytest.mark.asyncio
async def test_do_async():
    async def get_result(i: int = 1):
        if i < 3:
            return Ok(i)
        return Err(i)

    final_result: Result[int, str] = await do_async(
        Ok(x + y)
        for x in await get_result(1)
        for y in await get_result(2)
    )

    assert Ok(3) == final_result

    final_result: Result[int, str] = await do_async(
        Ok(x + y + z)
        for x in await get_result(1)
        for y in await get_result(2)
        for z in await get_result(10)
    )

    assert Err(10) == final_result