import asyncio
import threading
from typing import Any, Mapping

from greyhorse.app.context import current_scope_id
from greyhorse.app.entities.service import Service
from greyhorse.app.utils.registry import DictRegistry, ScopedRegistry
from greyhorse.result import Result
from .config import EngineConf
from .contexts import (
    SqlaAsyncContext, SqlaAsyncContextProvider, SqlaAsyncSessionContext,
    SqlaAsyncSessionProvider, SqlaSyncContext, SqlaSyncContextProvider,
    SqlaSyncSessionContext, SqlaSyncSessionProvider,
)
from .factory import SqlaAsyncEngineFactory, SqlaSyncEngineFactory


class SyncSqlaService(Service):
    def __init__(self, name: str, configs: Mapping[str, EngineConf]):
        super().__init__(name)
        self._configs = configs
        self._engine_factory = SqlaSyncEngineFactory()
        self._active = False
        self._event: threading.Event = threading.Event()
        self._registry = ScopedRegistry[Any, Any](
            factory=lambda: DictRegistry(),
            scope_func=lambda: current_scope_id(SqlaSyncContext),
        )

        for name in self._configs.keys():
            self._provider_factories.set(
                SqlaSyncContextProvider,
                lambda: SqlaSyncContextProvider(self.create_conn_context(name)),
                name=name,
            )
            self._provider_factories.set(
                SqlaSyncSessionProvider,
                lambda: SqlaSyncSessionProvider(self.create_session_context(name)),
                name=name,
            )

    def create_conn_context(self, name: str):
        if instance := self._registry.get(SqlaSyncContext, name=name):
            return instance

        engine = self._engine_factory.get_engine(name)
        instance = engine.get_context(SqlaSyncContext)
        self._registry.set(SqlaSyncContext, instance, name=name)
        return instance

    def create_session_context(self, name: str):
        if instance := self._registry.get(SqlaSyncSessionContext, name=name):
            return instance

        engine = self._engine_factory.get_engine(name)
        instance = engine.get_context(SqlaSyncSessionContext)
        self._registry.set(SqlaSyncSessionContext, instance, name=name)
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

    def start(self):
        for name in self._configs.keys():
            engine = self._engine_factory.get_engine(name)
            engine.start()
        self._active = True
        self._event.clear()

    def stop(self):
        self._registry.clear()
        for name in self._configs.keys():
            engine = self._engine_factory.get_engine(name)
            engine.stop()
        self._active = False
        self._event.set()

    def wait(self):
        return self._event


class AsyncSqlaService(Service):
    def __init__(self, name: str, configs: Mapping[str, EngineConf]):
        super().__init__(name)
        self._configs = configs
        self._engine_factory = SqlaAsyncEngineFactory()
        self._active = False
        self._event: asyncio.Event = asyncio.Event()
        self._registry = ScopedRegistry[Any, Any](
            factory=lambda: DictRegistry(),
            scope_func=lambda: current_scope_id(SqlaAsyncContext),
        )

        for name in self._configs.keys():
            self._provider_factories.set(
                SqlaAsyncContextProvider,
                lambda: SqlaAsyncContextProvider(self.create_conn_context(name)),
                name=name,
            )
            self._provider_factories.set(
                SqlaAsyncSessionProvider,
                lambda: SqlaAsyncSessionProvider(self.create_session_context(name)),
                name=name,
            )

    def create_conn_context(self, name: str):
        if instance := self._registry.get(SqlaAsyncContext, name=name):
            return instance

        engine = self._engine_factory.get_engine(name)
        instance = engine.get_context(SqlaAsyncContext)
        self._registry.set(SqlaAsyncContext, instance, name=name)
        return instance

    def create_session_context(self, name: str):
        if instance := self._registry.get(SqlaAsyncSessionContext, name=name):
            return instance

        engine = self._engine_factory.get_engine(name)
        instance = engine.get_context(SqlaAsyncSessionContext)
        self._registry.set(SqlaAsyncSessionContext, instance, name=name)
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
