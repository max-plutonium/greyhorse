import inspect
import types
from asyncio import AbstractEventLoop, get_running_loop
from collections.abc import Callable

from ..app.runtime import Runtime


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
    return Runtime().invoke_sync(func, *args, **kwargs)


async def invoke_async[T, **P](func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    return await Runtime().invoke_async(func, *args, **kwargs)


def caller_module(depth: int) -> types.ModuleType:
    import inspect

    frame = inspect.currentframe()

    for _ in range(depth, 0, -1):
        frame = frame.f_back

    return inspect.getmodule(frame)


def caller_path(depth: int) -> list[str]:
    return caller_module(depth + 1).__name__.split('.')
