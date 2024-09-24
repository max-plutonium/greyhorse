import pytest
from greyhorse.enum import Enum, Struct, Tuple, Unit


class Result[T, E](Enum):
    Ok = Tuple(T)
    Err = Tuple(E)
    Val = Struct(msg='message', value=int)
    Uno = Unit()


class ResultAllowInit[T, E](Enum, allow_init=True):
    pass


def test_enum() -> None:
    with pytest.raises(NotImplementedError):
        Result()

    ResultAllowInit()

    r1 = Result.Ok(1)
    r2 = Result.Err('1')
    r3 = Result.Val(value=123)
    r4 = Result.Uno

    res = 0

    for r in (r1, r2, r3, r4):
        match r:
            case Result.Ok(a):
                assert a == 1
                res += 1
            case Result.Err(b):
                assert b == '1'
                res += 1
            case Result.Val(c):
                assert c == 123
                res += 1
            case Result.Uno:
                res += 1

    assert res == 4
