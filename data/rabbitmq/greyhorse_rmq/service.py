import asyncio
from typing import Any, Mapping

from greyhorse.app.contexts import current_scope_id
from greyhorse.app.entities.service import Service
from greyhorse.app.utils.registry import DictRegistry, ScopedMutableRegistry
from greyhorse.result import Result
from .config import EngineConf
from .contexts import RmqAsyncContext, RmqAsyncContextProvider
from .factory import RmqAsyncEngineFactory


class RmqAsyncService(Service):
    def __init__(self, name: str, configs: Mapping[str, EngineConf]):
        super().__init__(name)
        self._configs = configs
        self._engine_factory = RmqAsyncEngineFactory()
        self._active = False
        self._event: asyncio.Event = asyncio.Event()
        self._registry = ScopedMutableRegistry[Any, Any](
            factory=lambda: DictRegistry(),
            scope_func=lambda: current_scope_id(RmqAsyncContext),
        )

        for name in self._configs.keys():
            self._provider_factories.set(
                RmqAsyncContextProvider,
                lambda: RmqAsyncContextProvider(self.create_context(name)),
                name=name,
            )

    def create_context(self, name: str):
        if instance := self._registry.get(RmqAsyncContext, name=name):
            return instance

        engine = self._engine_factory.get_engine(name)
        instance = engine.get_context(RmqAsyncContext)
        self._registry.set(RmqAsyncContext, instance, name=name)
        return instance

    @property
    def active(self) -> bool:
        return self._active

    def create(self) -> Result:
        for name, conf in self._configs.items():
            self._engine_factory.create_engine(name, conf)
        return Result.from_ok()

    def destroy(self) -> Result:
        for name in self._configs.keys():
            self._engine_factory.destroy_engine(name)
        return Result.from_ok()

    async def start(self):
        for name in self._configs.keys():
            engine = self._engine_factory.get_engine(name)
            await engine.start()
        self._active = True
        self._event.clear()

    async def stop(self):
        self._registry.clear()
        for name in self._configs.keys():
            engine = self._engine_factory.get_engine(name)
            await engine.stop()
        self._active = False
        self._event.set()

    def wait(self):
        return self._event
