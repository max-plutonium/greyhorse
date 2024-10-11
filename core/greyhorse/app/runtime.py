import asyncio
import inspect
import threading
from asyncio import Future as AsyncFuture
from asyncio import iscoroutine, iscoroutinefunction
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from queue import Empty, Queue
from typing import Any


def is_awaitable(f: object) -> bool:
    while isinstance(f, partial):
        f = f.func
    return iscoroutinefunction(f) or inspect.isawaitable(f)


@dataclass(slots=True, frozen=True)
class _Task:
    func: Callable[[...], Any]
    args: tuple
    kwargs: dict[str, Any]
    waiter: AsyncFuture


class Runtime:
    __slots__ = ('_loop', '_thread', '_counter', '_tasks', '_sync_ctx')

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(name='Greyhorse runtime', target=self._loop.run_forever)
        self._counter = 0
        self._tasks = Queue()
        self._sync_ctx = False

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    @property
    def active(self) -> bool:
        return self._thread.is_alive()

    def start(self) -> None:
        if self._counter == 0:
            self._thread.start()
        self._counter += 1

    def stop(self) -> None:
        if self._counter == 1:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join()
            self._loop.close()

        self._counter = max(self._counter - 1, 0)

    def invoke_sync[T, **P](
        self, func: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs
    ) -> T:
        if is_awaitable(func):
            if self.active:
                future = asyncio.run_coroutine_threadsafe(func(*args, **kwargs), self._loop)
                self._wait_for_async_future(future)
                return future.result()
            return asyncio.run(func(*args, **kwargs))

        return func(*args, **kwargs)

    async def invoke_async[T, **P](
        self, func: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs
    ) -> T:
        if is_awaitable(func):
            if iscoroutine(func):
                return await func  # type: ignore
            return await func(*args, **kwargs)

        if self._sync_ctx:
            future = self._loop.create_future()
            task = _Task(func=func, args=args, kwargs=kwargs, waiter=future)
            self._tasks.put(task)
            return await future

        return await asyncio.to_thread(func, *args, **kwargs)

    def _wait_for_async_future(self, future: AsyncFuture) -> None:
        self._sync_ctx = not future.done()
        while self._sync_ctx:
            try:
                while task := self._tasks.get(timeout=0.01):
                    try:
                        res = task.func(*task.args, **task.kwargs)
                        self._loop.call_soon_threadsafe(task.waiter.set_result, res)

                    except Exception as e:
                        self._loop.call_soon_threadsafe(task.waiter.set_exception, e)

                    self._tasks.task_done()

            except Empty:
                self._sync_ctx = not future.done()


instance = Runtime()
