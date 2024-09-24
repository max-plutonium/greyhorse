from collections.abc import Mapping
from typing import override

from greyhorse.app.abc.services import ServiceError, ServiceState
from greyhorse.app.entities.services import AsyncService, SyncService
from greyhorse.data.storage import ConnectionProviderRegistry, SessionProviderRegistry
from greyhorse.maybe import Maybe, Nothing
from greyhorse.result import Result

from .config import EngineConf
from .factory import AsyncSqlaEngineFactory, SyncSqlaEngineFactory
from .providers import (
    SqlaAsyncConnProvider,
    SqlaAsyncSessionProvider,
    SqlaSyncConnProvider,
    SqlaSyncSessionProvider,
)


class SyncSqlaService(SyncService):
    def __init__(self, configs: Mapping[str, EngineConf]) -> None:
        super().__init__()
        self._configs = configs
        self._engine_factory = SyncSqlaEngineFactory()
        self._conn_registry: Maybe[ConnectionProviderRegistry] = Nothing
        self._session_registry: Maybe[SessionProviderRegistry] = Nothing

    @override
    def setup(
        self,
        conn_registry: Maybe[ConnectionProviderRegistry],
        session_registry: Maybe[SessionProviderRegistry],
    ) -> Result[ServiceState, ServiceError]:
        for engine_name, conf in self._configs.items():
            self._engine_factory.create_engine(engine_name, conf)
        self._conn_registry = conn_registry
        self._session_registry = session_registry
        return super().setup()

    @override
    def teardown(self) -> Result[ServiceState, ServiceError]:
        for engine_name in self._configs:
            self._engine_factory.destroy_engine(engine_name)
        self._conn_registry = Nothing
        self._session_registry = Nothing
        return super().teardown()

    def start(self) -> None:
        conn_prov_type = SqlaSyncConnProvider
        session_prov_type = SqlaSyncSessionProvider

        for engine_name in self._configs:
            if engine := self._engine_factory.get_engine(engine_name).unwrap_or_none():
                engine.start()
                engine.get_provider(conn_prov_type).and_then(
                    lambda prov: self._conn_registry.map(
                        lambda registry: registry.add(conn_prov_type, engine_name, prov)
                    )
                )
                engine.get_provider(session_prov_type).and_then(
                    lambda prov: self._session_registry.map(
                        lambda registry: registry.add(session_prov_type, engine_name, prov)
                    )
                )

        self._switch_to_active(True)

    def stop(self) -> None:
        conn_prov_type = SqlaSyncConnProvider
        session_prov_type = SqlaSyncSessionProvider

        for engine_name in self._configs:
            if engine := self._engine_factory.get_engine(engine_name).unwrap_or_none():
                engine.stop()
                self._conn_registry.map(
                    lambda registry: registry.remove(conn_prov_type, engine_name)
                )
                self._session_registry.map(
                    lambda registry: registry.remove(session_prov_type, engine_name)
                )

        self._switch_to_active(False)


class AsyncSqlaService(AsyncService):
    def __init__(self, configs: Mapping[str, EngineConf]) -> None:
        super().__init__()
        self._configs = configs
        self._engine_factory = AsyncSqlaEngineFactory()
        self._conn_registry: Maybe[ConnectionProviderRegistry] = Nothing
        self._session_registry: Maybe[SessionProviderRegistry] = Nothing

    @override
    async def setup(
        self,
        conn_registry: Maybe[ConnectionProviderRegistry],
        session_registry: Maybe[SessionProviderRegistry],
    ) -> Result[ServiceState, ServiceError]:
        for engine_name, conf in self._configs.items():
            self._engine_factory.create_engine(engine_name, conf)
        self._conn_registry = conn_registry
        self._session_registry = session_registry
        return await super().setup()

    @override
    async def teardown(self) -> Result[ServiceState, ServiceError]:
        for engine_name in self._configs:
            self._engine_factory.destroy_engine(engine_name)
        self._conn_registry = Nothing
        self._session_registry = Nothing
        return await super().teardown()

    async def start(self) -> None:
        conn_prov_type = SqlaAsyncConnProvider
        session_prov_type = SqlaAsyncSessionProvider

        for engine_name in self._configs:
            if engine := self._engine_factory.get_engine(engine_name).unwrap_or_none():
                await engine.start()
                engine.get_provider(conn_prov_type).and_then(
                    lambda prov: self._conn_registry.map(
                        lambda registry: registry.add(conn_prov_type, engine_name, prov)
                    )
                )
                engine.get_provider(session_prov_type).and_then(
                    lambda prov: self._session_registry.map(
                        lambda registry: registry.add(session_prov_type, engine_name, prov)
                    )
                )

        await self._switch_to_active(True)

    async def stop(self) -> None:
        conn_prov_type = SqlaAsyncConnProvider
        session_prov_type = SqlaAsyncSessionProvider

        for engine_name in self._configs:
            if engine := self._engine_factory.get_engine(engine_name).unwrap_or_none():
                await engine.stop()
                self._conn_registry.map(
                    lambda registry: registry.remove(conn_prov_type, engine_name)
                )
                self._session_registry.map(
                    lambda registry: registry.remove(session_prov_type, engine_name)
                )

        await self._switch_to_active(False)
