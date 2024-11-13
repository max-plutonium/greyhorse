from collections.abc import Mapping
from typing import override

from greyhorse.app.abc.providers import SharedProvider
from greyhorse.app.abc.resources import Lifetime
from greyhorse.app.abc.services import ServiceError, ServiceState
from greyhorse.app.boxes import SharedRefBox
from greyhorse.app.entities.services import AsyncService, SyncService, provide
from greyhorse.app.registries import MutDictRegistry
from greyhorse.data.storage import EngineSelector
from greyhorse.result import Result

from .config import EngineConf
from .engine_async import AsyncSqlaEngine
from .engine_sync import SyncSqlaEngine
from .factory import AsyncSqlaEngineFactory, SyncSqlaEngineFactory


class SyncSqlaService(SyncService):
    def __init__(self, configs: Mapping[str, EngineConf]) -> None:
        super().__init__()
        self._configs = configs
        self._factory = SyncSqlaEngineFactory()
        self._engines = MutDictRegistry[str, SyncSqlaEngine]()
        self._box = SharedRefBox[EngineSelector[SyncSqlaEngine]](
            lambda: self._engines, lambda v: v
        )

    @override
    def setup(self) -> Result[ServiceState, ServiceError]:
        for engine_name, conf in self._configs.items():
            engine = self._factory.create_engine(engine_name, conf)
            engine.start()
            self._engines.add(engine_name, engine, type=conf.type)

        return super().setup()

    @override
    def teardown(self) -> Result[ServiceState, ServiceError]:
        for engine_name in reversed(self._configs.keys()):
            self._engines.remove(engine_name)
            self._factory.get_engine(engine_name).map(lambda engine: engine.stop()).map(
                lambda _, engine_name=engine_name: self._factory.destroy_engine(engine_name)
            )

        return super().teardown()

    @provide(lifetime=Lifetime.COMPONENT())
    def create_engine_selector(self) -> SharedProvider[EngineSelector[SyncSqlaEngine]]:
        return self._box


class AsyncSqlaService(AsyncService):
    def __init__(self, configs: Mapping[str, EngineConf]) -> None:
        super().__init__()
        self._configs = configs
        self._factory = AsyncSqlaEngineFactory()
        self._engines = MutDictRegistry[str, AsyncSqlaEngine]()
        self._box = SharedRefBox[EngineSelector[AsyncSqlaEngine]](
            lambda: self._engines, lambda v: v
        )

    @override
    async def setup(self) -> Result[ServiceState, ServiceError]:
        for engine_name, conf in self._configs.items():
            engine = self._factory.create_engine(engine_name, conf)
            await engine.start()
            self._engines.add(engine_name, engine, type=conf.type)

        return await super().setup()

    @override
    async def teardown(self) -> Result[ServiceState, ServiceError]:
        for engine_name in reversed(self._configs.keys()):
            self._engines.remove(engine_name)
            (
                await self._factory.get_engine(engine_name).map_async(
                    lambda engine: engine.stop()
                )
            ).map(lambda _, engine_name=engine_name: self._factory.destroy_engine(engine_name))

        return await super().teardown()

    @provide(lifetime=Lifetime.COMPONENT())
    def create_engine_selector(self) -> SharedProvider[EngineSelector[AsyncSqlaEngine]]:
        return self._box
