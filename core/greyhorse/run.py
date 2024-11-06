import asyncio
from collections.abc import Callable
from functools import partial, wraps

from greyhorse.app.runtime import Runtime
from greyhorse.utils.types import is_awaitable


def run[T, **P](func: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs) -> T:
    runtime = Runtime()
    asyncio.set_event_loop(runtime.loop)

    with runtime:
        if is_awaitable(func):
            return asyncio.run(func(*args, **kwargs))
        return func(*args, **kwargs)


def main[T, **P](func: Callable[P, T] | None = None) -> T:
    @wraps(func)
    def decorator[T, **P](func: Callable[P, T]) -> T:
        return partial(run, func)

    if func is None:
        return decorator

    return decorator(func)
