import asyncio
import inspect
from asyncio import Future, get_running_loop, iscoroutine, iscoroutinefunction, run as run_main
from functools import partial
from typing import Callable


def is_awaitable(f):
    while isinstance(f, partial):
        f = f.func
    return iscoroutinefunction(f) or inspect.isawaitable(f)


def get_asyncio_loop():
    try:
        return get_running_loop()
    except RuntimeError:
        return None


def invoke_sync[T, **P](func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    if is_awaitable(func):
        if loop := get_asyncio_loop():
            return loop.run_until_complete(func(*args, **kwargs))
        else:
            return run_main(func(*args, **kwargs))
    elif callable(func):
        return func(*args, **kwargs)
    else:
        return func


async def invoke_async[T, **P](
    func: Callable[P, T], to_thread: bool = False,
    *args: P.args, **kwargs: P.kwargs,
) -> T:
    if is_awaitable(func):
        if iscoroutine(func):
            return await func
        return await func(*args, **kwargs)
    elif callable(func):
        if to_thread:
            return await asyncio.to_thread(func, *args, **kwargs)
        else:
            return func(*args, **kwargs)
    else:
        future = Future()
        future.set_result(func)
        return future


def caller_path(depth: int) -> list[str]:
    import inspect

    frame = inspect.currentframe()

    for _ in range(depth, 0, -1):
        frame = frame.f_back

    path = inspect.getmodule(frame).__name__.split('.')[:-1]
    return path
