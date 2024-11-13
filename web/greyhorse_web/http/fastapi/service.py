from functools import partial
from typing import override

from fastapi import APIRouter, FastAPI
from greyhorse.app.abc.providers import SharedProvider
from greyhorse.app.abc.resources import Lifetime
from greyhorse.app.abc.services import ServiceError, ServiceState
from greyhorse.app.entities.services import AsyncService, provide
from greyhorse.app.registries import MutDictRegistry
from greyhorse.result import Result

from greyhorse_web.common import ASGIApp

from . import FastAPIRouterCollector
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
        self._handlers = MutDictRegistry[str, APIRouter](allow_many=True)

    @override
    async def setup(self) -> Result[ServiceState, ServiceError]:
        self._app = self._factory()
        return await super().setup()

    @override
    async def teardown(self) -> Result[ServiceState, ServiceError]:
        self._app = None
        return await super().teardown()

    async def start(self) -> None:
        for path, handler, kwargs in self._handlers.list_with_metadata():
            self._app.include_router(handler, prefix=path, **kwargs)
        await self._switch_to_active(True)

    async def stop(self) -> None:
        await self._switch_to_active(False)

    @provide(lifetime=Lifetime.COMPONENT())
    def create_collector_provider(self) -> SharedProvider[FastAPIRouterCollector]:
        yield self._handlers

    @provide(lifetime=Lifetime.COMPONENT())
    def create_asgi(self) -> ASGIApp:
        return self._app
