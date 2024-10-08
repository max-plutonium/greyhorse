import asyncio
import inspect
from asyncio import (
    AbstractEventLoop,
    Future,
    get_running_loop,
    iscoroutine,
    iscoroutinefunction,
)
from asyncio import run as run_main
from collections.abc import Callable
from functools import partial


def is_awaitable(f: object) -> bool:
    while isinstance(f, partial):
        f = f.func
    return iscoroutinefunction(f) or inspect.isawaitable(f)


def is_like_sync_context_manager(instance: object) -> bool:
    if callable(instance) and inspect.isgeneratorfunction(inspect.unwrap(instance)):
        instance = instance()
    return hasattr(instance, '__enter__') and hasattr(instance, '__exit__')


def is_like_async_context_manager(instance: object) -> bool:
    if callable(instance) and inspect.isasyncgenfunction(inspect.unwrap(instance)):
        instance = instance()
    return hasattr(instance, '__aenter__') and hasattr(instance, '__aexit__')


def get_asyncio_loop() -> AbstractEventLoop | None:
    try:
        return get_running_loop()
    except RuntimeError:
        return None


def invoke_sync[T, **P](func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    if is_awaitable(func):
        if loop := get_asyncio_loop():
            return loop.run_until_complete(func(*args, **kwargs))
        return run_main(func(*args, **kwargs))
    if callable(func):
        return func(*args, **kwargs)
    return func


async def invoke_async[T, **P](
    func: Callable[P, T], *args: P.args, to_thread: bool = False, **kwargs: P.kwargs
) -> T:
    if is_awaitable(func):
        if iscoroutine(func):
            return await func
        return await func(*args, **kwargs)
    if callable(func):
        if to_thread:
            return await asyncio.to_thread(func, *args, **kwargs)
        return func(*args, **kwargs)
    future = Future()
    future.set_result(func)
    return future


def caller_path(depth: int) -> list[str]:
    import inspect

    frame = inspect.currentframe()

    for _ in range(depth, 0, -1):
        frame = frame.f_back

    return inspect.getmodule(frame).__name__.split('.')
