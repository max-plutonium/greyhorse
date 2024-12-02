import asyncio
import threading
from asyncio import Future as AsyncFuture
from asyncio import iscoroutine
from collections.abc import Callable
from dataclasses import dataclass
from queue import Empty, Queue
from types import TracebackType
from typing import TYPE_CHECKING, Any

from greyhorse.utils.types import is_awaitable

if TYPE_CHECKING:
    from greyhorse.app.resources import Container


@dataclass(slots=True, frozen=True)
class _Task:
    func: Callable[[...], Any]
    args: tuple
    kwargs: dict[str, Any]
    waiter: AsyncFuture


class Runtime:
    __slots__ = ('_loop', '_thread', '_counter', '_tasks', '_sync_ctx', '_container')

    _instance: 'Runtime' = None

    def __new__(cls) -> 'Runtime':
        if not isinstance(cls._instance, cls):
            from greyhorse.app.abc.resources import Lifetime
            from greyhorse.app.resources import make_container

            container = make_container(lifetime=Lifetime.RUNTIME())
            cls._instance = object.__new__(cls)
            cls._instance._loop = asyncio.new_event_loop()  # noqa: SLF001
            cls._instance._thread = threading.Thread(  # noqa: SLF001
                name='Greyhorse runtime',
                target=cls._instance._loop.run_forever,  # noqa: SLF001
            )
            cls._instance._counter = 0  # noqa: SLF001
            cls._instance._tasks = Queue()  # noqa: SLF001
            cls._instance._sync_ctx = False  # noqa: SLF001
            cls._instance._container = container  # noqa: SLF001

        return cls._instance

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    @property
    def active(self) -> bool:
        return self._thread.is_alive()

    @property
    def container(self) -> 'Container':
        return self._container

    def start(self) -> None:
        if self._counter == 0:
            self._thread.start()
        self._counter += 1

    def stop(self) -> None:
        if self._counter == 1:
            if not self._loop.is_closed():
                self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join()
            if not self._loop.is_closed():
                self._loop.close()

        self._counter = max(self._counter - 1, 0)

    def __enter__(self) -> 'Container':
        self.start()
        return self._container.context.__enter__()

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        try:
            self._container.context.__exit__(exc_type, exc_value, traceback)
        finally:
            self.stop()

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
                while task := self._tasks.get(timeout=0.00001):
                    try:
                        res = task.func(*task.args, **task.kwargs)
                        self._loop.call_soon_threadsafe(task.waiter.set_result, res)

                    except Exception as e:
                        self._loop.call_soon_threadsafe(task.waiter.set_exception, e)

                    self._tasks.task_done()

            except Empty:
                self._sync_ctx = not future.done()
