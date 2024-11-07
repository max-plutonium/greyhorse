import contextlib
from asyncio import CancelledError, Task

from greyhorse.app.abc.providers import SharedProvider
from greyhorse.app.abc.resources import Lifetime
from greyhorse.app.entities.services import AsyncService, provide
from greyhorse.utils.invoke import get_asyncio_loop
from grpclib.server import Server

from greyhorse_web.common import GRPCHandler


class GRPCHandlerCollector:
    __slots__ = ('_handlers',)

    def __init__(self, handlers: list[GRPCHandler]) -> None:
        self._handlers = handlers

    def add_handler(self, handler: GRPCHandler) -> None:
        self._handlers.append(handler)


class GRPCService(AsyncService):
    def __init__(self, host: str, port: int) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._server: Server | None = None
        self._task: Task | None = None
        self._handlers: list[GRPCHandler] = []

    @provide(lifetime=Lifetime.COMPONENT())
    def create_collector(self) -> SharedProvider[GRPCHandlerCollector]:
        yield GRPCHandlerCollector(self._handlers)

    async def start(self) -> None:
        if self._task is not None:
            return

        self._server = Server(self._handlers)
        await self._server.start(self._host, self._port)
        self._task = get_asyncio_loop().create_task(self._server.wait_closed())
        await self._switch_to_active(True)

    async def stop(self) -> None:
        if self._task is None:
            return

        self._server.close()
        self._task.cancel()

        with contextlib.suppress(CancelledError):
            await self._task

        self._task = None
        self._server = None
        await self._switch_to_active(False)
