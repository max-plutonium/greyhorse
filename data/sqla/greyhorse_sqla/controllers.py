from collections.abc import Mapping
from typing import Any, override

from greyhorse.app.abc.collectors import MutNamedCollector, NamedCollector
from greyhorse.app.abc.controllers import ControllerError
from greyhorse.app.entities.controllers import AsyncController, SyncController
from greyhorse.result import Ok, Result

from .config import EngineConf
from .contexts import SqlaAsyncConnCtx, SqlaAsyncSessionCtx, SqlaSyncConnCtx, SqlaSyncSessionCtx
from .factory import AsyncSqlaEngineFactory, SyncSqlaEngineFactory

_sync_engine_factory = SyncSqlaEngineFactory()
_async_engine_factory = AsyncSqlaEngineFactory()


class SyncSqlaController(SyncController):
    def __init__(self, configs: Mapping[str, EngineConf]) -> None:
        super().__init__()
        self._configs = configs

    @override
    def setup(self, collector: NamedCollector[type, Any]) -> Result[bool, ControllerError]:
        res = True

        for engine_name, conf in self._configs.items():
            engine = _sync_engine_factory.create_engine(engine_name, conf)
            engine.start()

            res &= (
                engine.get_context(SqlaSyncConnCtx)
                .map(
                    lambda ctx, engine_name=engine_name: collector.add(
                        SqlaSyncConnCtx, ctx, name=engine_name
                    )
                )
                .unwrap_or(True)
            )
            res &= (
                engine.get_context(SqlaSyncSessionCtx)
                .map(
                    lambda ctx, engine_name=engine_name: collector.add(
                        SqlaSyncSessionCtx, ctx, name=engine_name
                    )
                )
                .unwrap_or(True)
            )

        return Ok(res)

    @override
    def teardown(
        self, collector: MutNamedCollector[type, Any]
    ) -> Result[bool, ControllerError]:
        res = True

        for engine_name in self._configs:
            res &= collector.remove(SqlaSyncSessionCtx)
            res &= collector.remove(SqlaSyncConnCtx)

            _sync_engine_factory.get_engine(engine_name).map(lambda engine: engine.stop())
            res &= _sync_engine_factory.destroy_engine(engine_name)

        return Ok(res)


class AsyncSqlaController(AsyncController):
    def __init__(self, configs: Mapping[str, EngineConf]) -> None:
        super().__init__()
        self._configs = configs

    @override
    async def setup(
        self, collector: NamedCollector[type, Any]
    ) -> Result[bool, ControllerError]:
        res = True

        for engine_name, conf in self._configs.items():
            engine = _async_engine_factory.create_engine(engine_name, conf)
            await engine.start()

            res &= (
                engine.get_context(SqlaAsyncConnCtx)
                .map(
                    lambda ctx, engine_name=engine_name: collector.add(
                        SqlaAsyncConnCtx, ctx, name=engine_name
                    )
                )
                .unwrap_or(True)
            )
            res &= (
                engine.get_context(SqlaAsyncSessionCtx)
                .map(
                    lambda ctx, engine_name=engine_name: collector.add(
                        SqlaAsyncSessionCtx, ctx, name=engine_name
                    )
                )
                .unwrap_or(True)
            )

        return Ok(res)

    @override
    async def teardown(
        self, collector: MutNamedCollector[type, Any]
    ) -> Result[bool, ControllerError]:
        res = True

        for engine_name in self._configs:
            res &= collector.remove(SqlaAsyncSessionCtx)
            res &= collector.remove(SqlaAsyncConnCtx)

            await _async_engine_factory.get_engine(engine_name).map_async(
                lambda engine: engine.stop()
            )
            res &= _async_engine_factory.destroy_engine(engine_name)

        return Ok(res)
