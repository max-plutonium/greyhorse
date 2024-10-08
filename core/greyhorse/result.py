# mypy: warn_no_return=false,disable_error_code="arg-type,has-type,misc,return-value"
from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator, Iterator
from functools import wraps
from typing import TYPE_CHECKING, Any, NoReturn, TypeGuard, TypeVar

from .enum import Enum, Tuple
from .error import Error

if TYPE_CHECKING:
    from .maybe import Maybe


ExcType = TypeVar('ExcType', bound=BaseException)


class Result[T, E](Enum):
    Ok = Tuple(T)
    Err = Tuple(E)

    def __new__(cls, value: T | E | None = None) -> Result:
        match cls.__name__:
            case 'Result':
                if isinstance(value, Error):
                    return cls.__new_err__(value)
                return cls.__new_ok__(value)
            case 'Ok':
                return cls.__new_ok__(value)
            case 'Err':
                return cls.__new_err__(value)

        raise AssertionError()

    @classmethod
    def __new_ok__(cls, value: T | None) -> Result:
        return super().__new__(Result[type(value), Any].Ok)

    @classmethod
    def __new_err__(cls, value: E) -> Result:
        return super().__new__(Result[Any, type(value)].Err)

    def __bool__(self) -> bool:
        return self.is_ok()

    def __hash__(self) -> int:
        match self:
            case Result.Ok(v):
                return hash((True, v))
            case Result.Err(e):
                return hash((False, e))

    def __iter__(self) -> Iterator[T]:
        match self:
            case Result.Ok(v):
                yield v
            case Result.Err(_):

                def _iter() -> Iterator[NoReturn]:
                    # Exception will be raised when the iterator
                    # is advanced, not when it's created
                    raise DoError(self)

                return _iter()

    def is_ok(self) -> bool:
        """Returns true if the `Result` is `Ok`."""
        return isinstance(self, Result[T, E].Ok)

    def is_ok_and(self, f: Callable[[T], bool]) -> bool:
        """
        Returns true if the `Result` is `Ok` and the value inside of it matches a predicate.
        """
        match self:
            case Result.Ok(v):
                return f(v)
            case Result.Err(_):
                return False

    def is_err(self) -> bool:
        """Returns true if the `Result` is `Err`."""
        return isinstance(self, Result[T, E].Err)

    def is_err_and(self, f: Callable[[E], bool]) -> bool:
        """
        Returns true if the `Result` is `Err` and the value inside of it matches a predicate.
        """
        match self:
            case Result.Ok(_):
                return False
            case Result.Err(e):
                return f(e)

    def ok(self) -> Maybe[T]:
        """
        Converts the `Result` into a `Maybe[T]` and discarding the error, if any.
        """
        from .maybe import Just, Nothing

        match self:
            case Result.Ok(v):
                return Just(v)
            case Result.Err(_):
                return Nothing

    def err(self) -> Maybe[E]:
        """
        Converts the `Result` into a `Maybe[E]` and discarding the success value, if any.
        """
        from .maybe import Just, Nothing

        match self:
            case Result.Ok(_):
                return Nothing
            case Result.Err(e):
                return Just(e)

    def inspect(self, f: Callable[[T], Any]) -> Result[T, E]:
        """
        Calls a function with the contained value if `Ok`.
        Returns the original `Result`.
        """
        match self:
            case Result.Ok(v):
                f(v)
            case Result.Err(_):
                pass
        return self

    def inspect_err(self, f: Callable[[E], Any]) -> Result[T, E]:
        """
        Calls a function with the contained value if `Err`.
        Returns the original `Result`.
        """
        match self:
            case Result.Ok(_):
                pass
            case Result.Err(e):
                f(e)
        return self

    def expect(self, message: str) -> T:
        """
        Returns the contained `Ok` value if the `Result` is `Ok` or raises a
        `ResultUnwrapError`.
        """
        match self:
            case Result.Ok(v):
                return v
            case Result.Err(e):
                raise ResultUnwrapError(message, e)

    def expect_err(self, message: str) -> E:
        """
        Returns the contained `Err` value if the `Result` is `Err` or raises a
        `ResultUnwrapError`.
        """
        match self:
            case Result.Ok(v):
                raise ResultUnwrapError(message, v)
            case Result.Err(e):
                return e

    def unwrap(self) -> T:
        """
        Returns the contained `Ok` value if the `Result` is `Ok` or raises a
        `ResultUnwrapError`.
        """
        match self:
            case Result.Ok(v):
                return v
            case Result.Err(e):
                raise ResultUnwrapError('Called `Result.unwrap()` on an `Err` value', e)

    def unwrap_err(self) -> E:
        """
        Returns the contained `Err` value if the `Result` is `Err` or raises a
        `ResultUnwrapError`.
        """
        match self:
            case Result.Ok(v):
                raise ResultUnwrapError('Called `Result.unwrap_err()` on an `Ok` value', v)
            case Result.Err(e):
                return e

    def unwrap_or(self, default: T) -> T:
        """
        Returns the contained `Ok` value or a provided default.
        """
        match self:
            case Result.Ok(v):
                return v
            case Result.Err(_):
                return default

    def unwrap_or_none(self) -> T | None:
        """
        Returns the contained `Ok` value or `None`.
        """
        match self:
            case Result.Ok(v):
                return v
            case Result.Err(_):
                return None

    def unwrap_err_or_none(self) -> T | None:
        """
        Returns the contained `Err` value or `None`.
        """
        match self:
            case Result.Ok(_):
                return None
            case Result.Err(e):
                return e

    def unwrap_or_else(self, f: Callable[[E], T]) -> T:
        """
        Returns the contained `Ok` value or computes it from a closure.
        """
        match self:
            case Result.Ok(v):
                return v
            case Result.Err(e):
                return f(e)

    def unwrap_or_raise(self, exc: Callable[[], ExcType]) -> T:
        """
        Returns the contained `Ok` value or raise the provided exception.
        """
        match self:
            case Result.Ok(v):
                return v
            case Result.Err(e):
                if isinstance(e, BaseException):
                    raise exc() from e
                raise exc()

    def map[U](self, f: Callable[[T], U]) -> Result[U, E]:
        """
        Maps a `Result[T, E]` to `Result[U, E]` by applying a function to a
        contained `Ok` value, leaving an `Err` value untouched.

        This function can be used to compose the results of two functions.
        """
        match self:
            case Result.Ok(v):
                return Result[U, E].Ok(f(v))
            case Result.Err(e):
                return Result[U, E].Err(e)

    async def map_async[U](self, f: Callable[[T], Awaitable[U]]) -> Result[U, E]:
        """
        Maps a `Result[T, E]` to `Result[U, E]` by applying a function to a
        contained `Ok` value, leaving an `Err` value untouched.

        This function can be used to compose the results of two functions.
        """
        match self:
            case Result.Ok(v):
                return Result[U, E].Ok(await f(v))
            case Result.Err(e):
                return Result[U, E].Err(e)

    def map_or[U](self, default: U, f: Callable[[T], U]) -> U:
        """
        Returns the provided default (if `Err`), or applies a function
        to the contained value (if `Ok`).
        """
        match self:
            case Result.Ok(v):
                return f(v)
            case Result.Err(_):
                return default

    def map_or_else[U](self, default_f: Callable[[E], U], f: Callable[[T], U]) -> U:
        """
        Maps a `Result[T, E]` to `U` by applying fallback function `default` to a
        contained `Err` value, or function `f` to a contained `Ok` value.

        This function can be used to unpack a successful result while handling an error.
        """
        match self:
            case Result.Ok(v):
                return f(v)
            case Result.Err(e):
                return default_f(e)

    def map_err[F](self, f: Callable[[E], F]) -> Result[T, F]:
        """
        Maps a `Result[T, E]` to `Result[T, F]` by applying a function to a
        contained `Err` value, leaving an `Ok` value untouched.

        This function can be used to pass through a successful result while handling an error.
        """
        match self:
            case Result.Ok(v):
                return Result[T, F].Ok(v)
            case Result.Err(e):
                return Result[T, F].Err(f(e))

    def and_[U](self, other: Result[U, E]) -> Result[U, E]:
        """
        Returns `other` if the Result is `Ok`, otherwise returns the `Err` value of `self`.
        """
        match self:
            case Result.Ok(_):
                return other
            case Result.Err(_):
                return self

    def and_then[U](self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """
        Calls `f` if the result is `Ok`, otherwise returns the `Err` value of `self`.
        This function can be used for control flow based on `Result` values.
        """
        match self:
            case Result.Ok(v):
                return f(v)
            case Result.Err(_):
                return self

    async def and_then_async[U](
        self, f: Callable[[T], Awaitable[Result[U, E]]]
    ) -> Result[U, E]:
        """
        Calls `f` if the result is `Ok`, otherwise returns the `Err` value of `self`.
        This function can be used for control flow based on `Result` values.
        """
        match self:
            case Result.Ok(v):
                return await f(v)
            case Result.Err(_):
                return self

    def or_[F](self, other: Result[T, F]) -> Result[T, F]:
        """
        Returns `other` if the Result is `Err`, otherwise returns the `Ok` value of `self`.
        """
        match self:
            case Result.Ok(_):
                return self
            case Result.Err(_):
                return other

    def or_else[F](self, f: Callable[[E], Result[T, F]]) -> Result[T, F]:
        """
        Calls `f` if the result is `Err`, otherwise returns the `Ok` value of `self`.
        This function can be used for control flow based on `Result` values.
        """
        match self:
            case Result.Ok(_):
                return self
            case Result.Err(e):
                return f(e)

    def flatten(self) -> Result[T, E]:
        """
        Converts from `Result[Result[T, E], E]` to `Result[T, E]`.
        """
        match self:
            case Result.Ok(v):
                match v:
                    case Result.Ok(_):
                        return v
                    case Result.Err(_):
                        return v
                    case _:
                        return self
            case Result.Err(_):
                return self

    def to_maybe(self) -> Maybe[Result[T, E]]:
        """
        Transposes a `Result` of an `Maybe` into an `Maybe` of a `Result`.

        `Ok(Nothing)` will be mapped to `Nothing`.
        `Ok(Just(_))` and `Err(_)` will be mapped to `Just(Ok(_))` and `Just(Err(_))`.
        """
        from .maybe import Just, Maybe, Nothing

        match self:
            case Result.Ok(v):
                match v:
                    case Maybe.Just(x):
                        return Just(Ok(x))
                    case Maybe.Nothing:
                        return Nothing
                    case _:
                        return Just(self)

            case Result.Err(e):
                return Just(Result[T, E].Err(e))


Ok = Result.Ok
Err = Result.Err


class ResultUnwrapError[V](Exception):
    """
    Exception raised from ``.unwrap_<...>`` and ``.expect_<...>`` calls.

    The contained value can be accessed via the ``.value`` attribute, but
    this is not intended for regular use, as type information is lost:
    ``ResultUnwrapError`` doesn't know about both ``T`` and ``E``, since it's raised
    from ``Ok()`` or ``Err()`` which only knows about either ``T`` or ``E``,
    not both.
    """

    def __init__(self, message: str, value: V) -> None:
        super().__init__(message)
        self._value = value

    @property
    def value(self) -> V:
        """
        Returns the contained value.
        """
        return self._value


class DoError(Exception):
    """
    This is used to signal to `do()` that the result is an `Err`,
    which short-circuits the generator and returns that Err.
    Using this exception for control flow in `do()` allows us
    to simulate `and_then()` in the Err case: namely, we don't call `op`,
    we just return `self` (the Err).
    """

    def __init__[T, E](self, err: Result[T, E].Err) -> None:  # type: ignore
        self.err = err


def is_ok[T, E](result: Result[T, E]) -> TypeGuard[Result[T, E].Ok]:  # type: ignore
    """A typeguard to check if a result is an Ok

    Usage:
    >>> r: Result[int, str] = get_a_result()
    >>> if is_ok(r):
    >>>     r   # r is of type Ok[int]
    >>> elif is_err(r):
    >>>     r   # r is of type Err[str]
    """
    return result.is_ok()


def is_err[T, E](result: Result[T, E]) -> TypeGuard[Result[T, E].Err]:  # type: ignore
    """A typeguard to check if a result is an Err

    Usage:
    >>> r: Result[int, str] = get_a_result()
    >>> if is_ok(r):
    >>>     r   # r is of type Ok[int]
    >>> elif is_err(r):
    >>>     r   # r is of type Err[str]
    """
    return result.is_err()


def as_result_sync[T, E, **P](
    *exceptions: type[E],
) -> Callable[[Callable[P, T]], Callable[P, Result[T, E]]]:
    """
    Make a decorator to turn a function into one that returns a ``Result``.

    Regular return values are turned into ``Ok(return_value)``. Raised
    exceptions of the specified exception type(s) are turned into ``Err(exc)``.
    """
    if not exceptions or not all(
        inspect.isclass(exception) and issubclass(exception, BaseException)
        for exception in exceptions
    ):
        raise TypeError('as_result_sync() requires one or more exception types')

    def decorator(f: Callable[P, T]) -> Callable[P, Result[T, E]]:
        """
        Decorator to turn a function into one that returns a ``Result``.
        """

        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Result[T, E]:
            try:
                return Ok(f(*args, **kwargs))
            except exceptions as exc:
                return Err(exc)

        return wrapper

    return decorator


def as_result_async[T, E, **P](
    *exceptions: type[E],
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[Result[T, E]]]]:
    """
    Make a decorator to turn an async function into one that returns a ``Result``.
    Regular return values are turned into ``Ok(return_value)``. Raised
    exceptions of the specified exception type(s) are turned into ``Err(exc)``.
    """
    if not exceptions or not all(
        inspect.isclass(exception) and issubclass(exception, BaseException)
        for exception in exceptions
    ):
        raise TypeError('as_result_async() requires one or more exception types')

    def decorator(f: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[Result[T, E]]]:
        """
        Decorator to turn a function into one that returns a ``Result``.
        """

        @wraps(f)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Result[T, E]:
            try:
                return Ok(await f(*args, **kwargs))
            except exceptions as exc:
                return Err(exc)

        return async_wrapper

    return decorator


def do[T, E](gen: Generator[Result[T, E], None, None]) -> Result[T, E]:
    """Do notation for Result (syntactic sugar for sequence of `and_then()` calls).


    Usage:

    ``` rust
    // This is similar to
    use do_notation::m;
    let final_result = m! {
        x <- Ok("hello");
        y <- Ok(True);
        Ok(len(x) + int(y) + 0.5)
    };
    ```

    ``` rust
    final_result: Result[float, int] = do(
        Ok(len(x) + int(y) + 0.5)
        for x in Ok("hello")
        for y in Ok(True)
    )
    ```

    NOTE: If you exclude the type annotation e.g. `Result[float, int]`
    your type checker might be unable to infer the return type.
    To avoid an error, you might need to help it with the type hint.
    """
    try:
        return next(gen)
    except DoError as e:
        out: Err[E] = e.err  # type: ignore
        return out
    except TypeError as te:
        # Turn this into a more helpful error message.
        # Python has strange rules involving turning generators involving `await`
        # into async generators, so we want to make sure to help the user clearly.
        if "'async_generator' object is not an iterator" in str(te):
            raise TypeError(
                'Got async_generator but expected generator.'
                'See the section on do notation in the README.'
            ) from te
        raise te


async def do_async[T, E](
    gen: Generator[Result[T, E], None, None] | AsyncGenerator[Result[T, E], None],
) -> Result[T, E]:
    """Async version of do. Example:

    ``` python
    final_result: Result[float, int] = await do_async(
        Ok(len(x) + int(y) + z)
        for x in await get_async_result_1()
        for y in await get_async_result_2()
        for z in get_sync_result_3()
    )
    ```

    NOTE: Python makes generators async in a counter-intuitive way.

    ``` python
    # This is a regular generator:
    async def foo(): ...
        do(Ok(1) for x in await foo())
    ```

    ``` python
    # But this is an async generator:
    async def foo(): ...
    async def bar(): ...


    do(Ok(1) for x in await foo() for y in await bar())
    ```

    We let users try to use regular `do()`, which works in some cases
    of awaiting async values. If we hit a case like above, we raise
    an exception telling the user to use `do_async()` instead.
    See `do()`.

    However, for better usability, it's better for `do_async()` to also accept
    regular generators, as you get in the first case:

    ``` python
    async def foo(): ...
        do(Ok(1) for x in await foo())
    ```

    Furthermore, neither mypy nor pyright can infer that the second case is
    actually an async generator, so we cannot annotate `do_async()`
    as accepting only an async generator. This is additional motivation
    to accept either.
    """
    try:
        if isinstance(gen, AsyncGenerator):
            return await gen.__anext__()
        return next(gen)
    except DoError as e:
        out: Err[E] = e.err  # type: ignore
        return out
