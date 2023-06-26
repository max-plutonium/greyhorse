import inspect
from asyncio import get_running_loop, iscoroutinefunction, run as run_main, iscoroutine, Future
from functools import partial


def is_awaitable(f):
    while isinstance(f, partial):
        f = f.func
    return iscoroutinefunction(f) or inspect.isawaitable(f)


def invoke_sync(func, *args, **kwargs):
    try:
        loop = get_running_loop()
    except RuntimeError:
        loop = None

    if is_awaitable(func):
        if loop:
            return loop.create_task(func(*args, **kwargs))
        else:
            return run_main(func(*args, **kwargs))
    elif callable(func):
        return func(*args, **kwargs)
    else:
        return func


async def invoke_async(func, *args, **kwargs):
    if is_awaitable(func):
        if iscoroutine(func):
            return await func
        return await func(*args, **kwargs)
    elif callable(func):
        loop = get_running_loop()
        func = partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, func)
    else:
        future = Future()
        future.set_result(func)
        return future
