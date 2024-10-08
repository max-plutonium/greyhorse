# mypy: warn_no_return=false,disable_error_code="arg-type,has-type,misc,return-value"
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypeGuard, TypeVar

from .enum import Enum, Tuple, Unit

if TYPE_CHECKING:
    from .result import Result


ExcType = TypeVar('ExcType', bound=BaseException)


class Maybe[T](Enum):
    Just = Tuple(T)
    Nothing = Unit()

    def __new__(cls, value: T | None = None) -> Maybe:
        match cls.__name__:
            case 'Maybe':
                if value is None:
                    return cls.Nothing
                return cls.__new_just__(value)
            case 'Just':
                return cls.__new_just__(value)
            case 'Nothing':
                return super().__new__(cls)

        raise AssertionError()

    @classmethod
    def __new_just__(cls, value: T | None) -> Maybe:
        return super().__new__(Maybe[type(value)].Just)

    def __bool__(self) -> bool:
        return self.is_just()

    def __hash__(self) -> int:
        match self:
            case Maybe.Just(v):
                return hash((True, v))
            case Maybe.Nothing:
                # A large random number is used here to avoid a hash collision with
                # something else since there is no real inner value for us to hash.
                return hash((False, 969048543980197075614658413455))

    def is_just(self) -> bool:
        """Returns true if the `Maybe` is a `Just` value."""
        return isinstance(self, Maybe[T].Just)

    is_some = is_just

    def is_just_and(self, f: Callable[[T], bool]) -> bool:
        """
        Returns true if the `Maybe` is a `Just` and the value inside of it matches a predicate.
        """
        match self:
            case Maybe.Just(v):
                return f(v)
            case Maybe.Nothing:
                return False

    is_some_and = is_just_and

    def is_nothing(self) -> bool:
        """Returns true if the `Maybe` is a `Nothing` value."""
        return self is Maybe[T].Nothing

    is_none = is_nothing

    def ok_or[E](self, err: E) -> Result[T, E]:
        """
        Transforms the `Maybe[T]` into a `Result[T, E]`, mapping `Just(v)` to `Ok(v)`
        and `Nothing` to `Err(err)`.
        """
        from .result import Err, Ok

        match self:
            case Maybe.Just(v):
                return Ok(v)
            case Maybe.Nothing:
                return Err(err)

    def ok_or_else[E](self, err: Callable[[], E]) -> Result[T, E]:
        """
        Transforms the `Maybe[T]` into a `Result[T, E]`, mapping `Just(v)` to `Ok(v)`
        and `Nothing` to `Err(err())`.
        """
        from .result import Err, Ok

        match self:
            case Maybe.Just(v):
                return Ok(v)
            case Maybe.Nothing:
                return Err(err())

    def inspect(self, f: Callable[[T], Any]) -> Maybe[T]:
        """
        Calls a function with the contained value if `Just`.
        Returns the original `Maybe`.
        """
        match self:
            case Maybe.Just(v):
                f(v)
            case Maybe.Nothing:
                pass
        return self

    def expect(self, message: str) -> T:
        """
        Returns the contained `Just` value if the `Maybe` is a `Just` or raises a
        `MaybeUnwrapError`.
        """
        match self:
            case Maybe.Just(v):
                return v
            case Maybe.Nothing:
                raise MaybeUnwrapError(message)

    def unwrap(self) -> T:
        """
        Returns the contained value if the `Maybe` is a `Just` or raises a
        `MaybeUnwrapError`.
        """
        match self:
            case Maybe.Just(v):
                return v
            case Maybe.Nothing:
                raise MaybeUnwrapError('Called `Maybe.unwrap()` on a `Nothing` value')

    def unwrap_or(self, default: T) -> T:
        """
        Returns the contained `Just` value or a provided default.
        """
        match self:
            case Maybe.Just(v):
                return v
            case Maybe.Nothing:
                return default

    def unwrap_or_none(self) -> T | None:
        """
        Returns the contained `Just` value or `None`.
        """
        match self:
            case Maybe.Just(v):
                return v
            case Maybe.Nothing:
                return None

    def unwrap_or_else(self, f: Callable[[], T]) -> T:
        """
        Returns the contained `Just` value or computes it from a closure.
        """
        match self:
            case Maybe.Just(v):
                return v
            case Maybe.Nothing:
                return f()

    def unwrap_or_raise(self, exc: Callable[[], ExcType]) -> T:
        """
        Returns the contained `Just` value or raise the provided exception.
        """
        match self:
            case Maybe.Just(v):
                return v
            case Maybe.Nothing:
                raise exc()

    def map[U](self, f: Callable[[T], U]) -> Maybe[U]:
        """
        Maps a `Maybe[T]` to `Maybe[U]` by applying a function to a contained value (if `Just`)
        or returns `Nothing` (if `Nothing`).
        """
        match self:
            case Maybe.Just(v):
                return Maybe[U].Just(f(v))
            case Maybe.Nothing:
                return self

    async def map_async[U](self, f: Callable[[T], Awaitable[U]]) -> Maybe[U]:
        """
        Maps a `Maybe[T]` to `Maybe[U]` by applying a function to a contained value (if `Just`)
        or returns `Nothing` (if `Nothing`).
        """
        match self:
            case Maybe.Just(v):
                return Maybe[U].Just(await f(v))
            case Maybe.Nothing:
                return self

    def map_or[U](self, default: U, f: Callable[[T], U]) -> U:
        """
        Returns the provided default result (if `Nothing`), or applies a function
        to the contained value (if `Just`).
        """
        match self:
            case Maybe.Just(v):
                return f(v)
            case Maybe.Nothing:
                return default

    def map_or_else[U](self, default_f: Callable[[], U], f: Callable[[T], U]) -> U:
        """
        Computes a default function result (if `Nothing`), or applies a different function
        to the contained value (if `Just`).
        """
        match self:
            case Maybe.Just(v):
                return f(v)
            case Maybe.Nothing:
                return default_f()

    def and_[U](self, other: Maybe[U]) -> Maybe[U]:
        """
        Returns `Nothing` if the Maybe is `Nothing`, otherwise returns `other`.
        """
        match self:
            case Maybe.Just(_):
                return other
            case Maybe.Nothing:
                return self

    def and_then[U](self, f: Callable[[T], Maybe[U]]) -> Maybe[U]:
        """
        Returns `Nothing` if the Maybe is `Nothing`, otherwise calls `f` with the
        wrapped value and returns the result. Some languages call this operation flatmap.
        """
        match self:
            case Maybe.Just(v):
                return f(v)
            case Maybe.Nothing:
                return self

    async def and_then_async[U](self, f: Callable[[T], Awaitable[Maybe[U]]]) -> Maybe[U]:
        """
        Returns `Nothing` if the Maybe is `Nothing`, otherwise calls `f` with the
        wrapped value and returns the result. Some languages call this operation flatmap.
        """
        match self:
            case Maybe.Just(v):
                return await f(v)
            case Maybe.Nothing:
                return self

    def filter(self, predicate: Callable[[T], bool]) -> Maybe[T]:
        """
        Returns `Nothing` if the Maybe is `Nothing`, otherwise calls `predicate` with the
        wrapped value and returns:
        * `Just(t)` if predicate returns true (where t is the wrapped value), and
        * `Nothing` if predicate returns false.
        """
        match self:
            case Maybe.Just(v):
                if predicate(v):
                    return self
                return Maybe[T].Nothing
            case Maybe.Nothing:
                return self

    def or_(self, other: Maybe[T]) -> Maybe[T]:
        """
        Returns the Maybe if it contains a value, otherwise returns `other`.
        """
        match self:
            case Maybe.Just(_):
                return self
            case Maybe.Nothing:
                return other

    def or_else(self, f: Callable[[], Maybe[T]]) -> Maybe[T]:
        """
        Returns the Maybe if it contains a value, otherwise calls `f` and returns the result.
        """
        match self:
            case Maybe.Just(_):
                return self
            case Maybe.Nothing:
                return f()

    def xor(self, other: Maybe[T]) -> Maybe[T]:
        """
        Returns `Just` if exactly one of `self`, `other` is `Just`, otherwise returns `Nothing`.
        """
        match (self, other):
            case (Maybe.Just(_), Maybe.Nothing):
                return self
            case (Maybe.Nothing, Maybe.Just(_)):
                return other
            case _:
                return Maybe[T].Nothing

    def flatten(self) -> Maybe[T]:
        """
        Converts from `Maybe[Maybe[T]]` to `Maybe[T]`.
        """
        match self:
            case Maybe.Just(v):
                match v:
                    case Maybe.Just(_):
                        return v
                    case Maybe.Nothing:
                        return Maybe[T].Nothing
                    case _:
                        return self
            case Maybe.Nothing:
                return self

    def to_result(self) -> Result[Maybe[T], Any]:
        """
        Transposes a `Maybe` of a `Result` into an `Result` of a `Maybe`.

        `Nothing` will be mapped to `Ok(Nothing)`.
        `Just(Ok(_))` and `Just(Err(_))` will be mapped to `Ok(Just(_))` and `Err(_)`.
        """
        from .result import Err, Ok, Result

        match self:
            case Maybe.Just(v):
                match v:
                    case Result.Ok(x):
                        return Ok(Just(x))
                    case Result.Err(e):
                        return Err(e)
                    case _:
                        return Ok(self)

            case Maybe.Nothing:
                return Result[Maybe[T], Any].Ok(Nothing)


Just = Maybe.Just
Nothing = Maybe.Nothing


class MaybeUnwrapError(Exception):
    """
    Exception raised from ``.unwrap_<...>`` and ``.expect_<...>`` calls.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


def is_just[T](maybe: Maybe[T]) -> TypeGuard[Maybe[T].Just]:  # type: ignore
    """A typeguard to check if a Maybe is a Just

    Usage:
    >>> r: Maybe[int] = get_a_maybe()
    >>> if is_just(r):
    >>>     r   # r is of type Just[int]
    >>> elif is_nothing(r):
    >>>     r   # r is of type Nothing
    """
    return maybe.is_just()


def is_nothing[T](maybe: Maybe[T]) -> TypeGuard[Maybe[T].Nothing]:  # type: ignore
    """A typeguard to check if a Maybe is a Nothing

    Usage:
    >>> r: Maybe[int] = get_a_maybe()
    >>> if is_just(r):
    >>>     r   # r is of type Just[int]
    >>> elif is_nothing(r):
    >>>     r   # r is of type Nothing
    """
    return maybe.is_nothing()
