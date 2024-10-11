import asyncio
from collections.abc import Callable
from functools import partial

from greyhorse.app.runtime import instance, is_awaitable


def run[T, **P](func: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs) -> T:
    asyncio.set_event_loop(instance.loop)

    try:
        instance.start()

        if is_awaitable(func):
            return asyncio.run(func(*args, **kwargs))
        return func(*args, **kwargs)

    finally:
        instance.stop()


def main[T, **P](func: Callable[P, T] | None = None) -> T:
    def decorator[T, **P](func: Callable[P, T]) -> T:
        return partial(run, func)

    if func is None:
        return decorator

    return decorator(func)
