from functools import partial
from typing import override

from fastapi import FastAPI
from greyhorse.app.abc.providers import SharedProvider
from greyhorse.app.abc.resources import Lifetime
from greyhorse.app.abc.services import ServiceError, ServiceState
from greyhorse.app.boxes import SharedRefBox
from greyhorse.app.entities.services import AsyncService, provide
from greyhorse.result import Result

from greyhorse_web.common import ASGIApp

from .factory import create_fastapi


class FastAPIService(AsyncService):
    def __init__(
        self,
        title: str,
        debug: bool = False,
        root_path: str = '',
        version: str | None = None,
        cors: list[str] | None = None,
    ) -> None:
        super().__init__()
        self._factory = partial(create_fastapi, title, debug, root_path, version, cors)
        self._app: FastAPI | None = None
        self._app_box = SharedRefBox[FastAPI](lambda: self._app, lambda v: v)

    @override
    async def setup(self) -> Result[ServiceState, ServiceError]:
        self._app = self._factory()
        return await super().setup()

    @override
    async def teardown(self) -> Result[ServiceState, ServiceError]:
        self._app = None
        return await super().teardown()

    @provide(lifetime=Lifetime.COMPONENT())
    def create_fastapi(self) -> SharedProvider[FastAPI]:
        return self._app_box

    @provide(lifetime=Lifetime.COMPONENT())
    def create_asgi(self) -> ASGIApp:
        return self._app
