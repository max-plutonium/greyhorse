import contextlib
from asyncio import CancelledError, Future, Task
from typing import Any, override

from greyhorse.app.abc.selectors import NamedListSelector
from greyhorse.app.abc.services import ServiceError, ServiceState
from greyhorse.app.entities.services import AsyncService
from greyhorse.result import Result
from greyhorse.utils.invoke import get_asyncio_loop
from hypercorn.asyncio import serve
from hypercorn.config import Config


class HypercornService(AsyncService):
    def __init__(self, host: str, port: int, resource_name: str) -> None:
        super().__init__()
        self._config = Config()
        self._config.bind = f'{host}:{port}'
        self._resource_name = resource_name
        self._task: Task | None = None
        self._app = None

    @override
    async def setup(
        self, list_selector: NamedListSelector[type, Any]
    ) -> Result[ServiceState, ServiceError]:
        app = None

        for _, _name, app in list_selector.items(lambda t, n: n == self._resource_name):  # noqa: B007
            break

        if app is None:
            return ServiceError.NoSuchResource(name='Application for Hypercorn').to_result()

        self._app = app
        return await super().setup()

    @override
    async def teardown(self) -> Result[ServiceState, ServiceError]:
        self._app = None
        return await super().teardown()

    async def start(self) -> None:
        if self._task is not None:
            return

        self._task = get_asyncio_loop().create_task(
            serve(self._app, self._config, shutdown_trigger=Future)
        )
        await self._switch_to_active(True)

    async def stop(self) -> None:
        if self._task is None:
            return

        self._task.cancel()

        with contextlib.suppress(CancelledError):
            await self._task

        self._task = None
        await self._switch_to_active(False)
