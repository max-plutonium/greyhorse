import contextlib
import signal
from asyncio import CancelledError, Task
from typing import Any, override

from greyhorse.app.abc.services import ServiceError, ServiceState
from greyhorse.app.entities.services import AsyncService
from greyhorse.app.resources import inject
from greyhorse.result import Result
from greyhorse.utils.invoke import get_asyncio_loop
from uvicorn import Config, Server

from greyhorse_web.common import ASGIApp


class UvicornService(AsyncService):
    def __init__(self, host: str, port: int, config: dict[str, Any] | None = None) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._conf = config or {}
        self._server: Server | None = None
        self._task: Task | None = None

    @override
    @inject
    async def setup(self, app: ASGIApp | None) -> Result[ServiceState, ServiceError]:
        if app is None:
            return ServiceError.NoSuchResource(name='Application for Uvicorn').to_result()

        config = Config(app, host=self._host, port=self._port, **self._conf)
        self._server = Server(config)
        return await super().setup()

    @override
    async def teardown(self) -> Result[ServiceState, ServiceError]:
        self._server = None
        return await super().teardown()

    async def start(self) -> None:
        if self._task is not None:
            return

        self._task = get_asyncio_loop().create_task(self._server.serve())
        await self._switch_to_active(True)

    async def stop(self) -> None:
        if self._task is None:
            return

        self._server.handle_exit(signal.SIGINT, None)

        with contextlib.suppress(CancelledError):
            await self._task

        self._task = None
        await self._switch_to_active(False)
