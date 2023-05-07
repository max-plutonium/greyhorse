import inspect
from asyncio import get_running_loop, iscoroutinefunction, run as run_main
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
    else:
        return func(*args, **kwargs)


async def invoke_async(func, *args, **kwargs):
    if is_awaitable(func):
        return await func(*args, **kwargs)
    else:
        loop = get_running_loop()
        func = partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, func)
