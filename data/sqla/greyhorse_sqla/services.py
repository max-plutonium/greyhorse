from collections.abc import Mapping
from typing import override

from greyhorse.app.abc.providers import SharedProvider
from greyhorse.app.abc.services import ServiceError, ServiceState
from greyhorse.app.boxes import SharedRefBox
from greyhorse.app.entities.services import AsyncService, SyncService, provider
from greyhorse.data.storage import EngineReader
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
        self._box = SharedRefBox[EngineReader[SyncSqlaEngine]](
            lambda: self._factory, lambda v: v
        )

    @override
    def setup(self) -> Result[ServiceState, ServiceError]:
        for engine_name, conf in self._configs.items():
            engine = self._factory.create_engine(engine_name, conf)
            engine.start()

        return super().setup()

    @override
    def teardown(self) -> Result[ServiceState, ServiceError]:
        for engine_name in reversed(self._configs.keys()):
            self._factory.get_engine(engine_name).map(lambda engine: engine.stop()).map(
                lambda _, engine_name=engine_name: self._factory.destroy_engine(engine_name)
            )

        return super().teardown()

    @provider(SharedProvider[EngineReader[SyncSqlaEngine]])
    def create_engine_reader(self) -> SharedProvider[EngineReader[SyncSqlaEngine]]:
        return self._box


class AsyncSqlaService(AsyncService):
    def __init__(self, configs: Mapping[str, EngineConf]) -> None:
        super().__init__()
        self._configs = configs
        self._factory = AsyncSqlaEngineFactory()
        self._box = SharedRefBox[EngineReader[AsyncSqlaEngine]](
            lambda: self._factory, lambda v: v
        )

    @override
    async def setup(self) -> Result[ServiceState, ServiceError]:
        for engine_name, conf in self._configs.items():
            engine = self._factory.create_engine(engine_name, conf)
            await engine.start()

        return await super().setup()

    @override
    async def teardown(self) -> Result[ServiceState, ServiceError]:
        for engine_name in reversed(self._configs.keys()):
            (
                await self._factory.get_engine(engine_name).map_async(
                    lambda engine: engine.stop()
                )
            ).map(lambda _, engine_name=engine_name: self._factory.destroy_engine(engine_name))

        return await super().teardown()

    @provider(SharedProvider[EngineReader[AsyncSqlaEngine]])
    def create_engine_reader(self) -> SharedProvider[EngineReader[AsyncSqlaEngine]]:
        return self._box
