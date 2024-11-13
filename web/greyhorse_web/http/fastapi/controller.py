from typing import override

from fastapi import APIRouter, FastAPI
from greyhorse.app.abc.controllers import ControllerError
from greyhorse.app.entities.controllers import ResConf, ResourceController
from greyhorse.app.registries import MutDictRegistry
from greyhorse.app.resources import Container
from greyhorse.result import Ok, Result

from . import FastAPIRouterCollector


class FastAPIController(ResourceController):
    def __init__(self, prefix: str = '') -> None:
        super().__init__(
            resources=[
                ResConf(type=FastAPIRouterCollector, required=False),
                ResConf(type=FastAPI, required=False),
            ]
        )
        self._prefix = prefix
        self._router: FastAPI | APIRouter | None = None
        self._parent: FastAPIRouterCollector | None = None
        self._children = MutDictRegistry[str, APIRouter](allow_many=True)

    @override
    def setup(self, container: Container) -> Result[bool, ControllerError]:
        if not (res := super().setup(container)):
            return res

        if (parent := container.get(FastAPIRouterCollector).unwrap_or_none()) is not None:
            self._parent = parent
        elif app := container.get(FastAPI).unwrap_or_none():
            self._router = app
        else:
            return ControllerError.NoSuchResource(
                name='FastAPIRouterCollector/FastAPI'
            ).to_result()

        if self._router is None:
            self._router = APIRouter(prefix=self._prefix)
        if self._parent is not None:
            self._parent.add(self._prefix, self._router)

        res = True
        if self._parent is not None:
            res &= container.registry.remove_factory(FastAPIRouterCollector)
        res &= container.registry.add_factory(FastAPIRouterCollector, self._children)
        return Ok(res)

    @override
    def teardown(self, container: Container) -> Result[bool, ControllerError]:
        if self._parent is not None:
            self._parent.remove(self._prefix, self._router)

        container.registry.remove_factory(FastAPIRouterCollector)
        if self._parent is not None:
            container.registry.add_factory(FastAPIRouterCollector, self._parent)

        self._parent = self._router = None
        return super().teardown(container)

    def start(self) -> None:
        for path, handler, kwargs in self._children.list_with_metadata():
            self._router.include_router(handler, prefix=path, **kwargs)
