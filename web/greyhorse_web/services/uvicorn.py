import contextlib
import signal
from asyncio import CancelledError, Task
from typing import Any, override

from greyhorse.app.abc.selectors import NamedListSelector
from greyhorse.app.abc.services import ServiceError, ServiceState
from greyhorse.app.entities.services import AsyncService
from greyhorse.result import Result
from greyhorse.utils.invoke import get_asyncio_loop
from uvicorn import Config, Server


class UvicornService(AsyncService):
    def __init__(self, host: str, port: int, resource_name: str) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._resource_name = resource_name
        self._server: Server | None = None
        self._task: Task | None = None

    @override
    async def setup(
        self, list_selector: NamedListSelector[type, Any]
    ) -> Result[ServiceState, ServiceError]:
        app = None

        for _, _name, app in list_selector.items(lambda t, n: n == self._resource_name):  # noqa: B007
            break

        if app is None:
            return ServiceError.NoSuchResource(name='Application for Uvicorn').to_result()

        config = Config(app, host=self._host, port=self._port)
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
