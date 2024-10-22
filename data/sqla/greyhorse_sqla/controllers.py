from functools import partial
from typing import Any, override

from greyhorse.app.abc.collectors import MutNamedCollector, NamedCollector
from greyhorse.app.abc.controllers import ControllerError
from greyhorse.app.abc.operators import AssignOperator, Operator
from greyhorse.app.entities.controllers import AsyncController, SyncController, operator
from greyhorse.data.storage import EngineReader
from greyhorse.maybe import Maybe, Nothing
from greyhorse.result import Ok, Result

from .contexts import SqlaAsyncConnCtx, SqlaAsyncSessionCtx, SqlaSyncConnCtx, SqlaSyncSessionCtx
from .engine_async import AsyncSqlaEngine
from .engine_sync import SyncSqlaEngine


class SyncSqlaController(SyncController):
    def __init__(self, engine_name: str) -> None:
        super().__init__()
        self._engine_name = engine_name
        self._reader: Maybe[EngineReader[SyncSqlaEngine]] = Nothing

    def _setter(self, value: Maybe[EngineReader[SyncSqlaEngine]]) -> None:
        self._reader = value

    @operator(EngineReader[SyncSqlaEngine])
    def create_engine_operator(self) -> Operator[EngineReader[SyncSqlaEngine]]:
        return AssignOperator[EngineReader[SyncSqlaEngine]](lambda: self._reader, self._setter)

    @override
    def setup(self, collector: NamedCollector[type, Any]) -> Result[bool, ControllerError]:
        if not self._reader:
            return ControllerError.NoSuchResource(
                name='EngineReader[SyncSqlaEngine]'
            ).to_result()

        reader = self._reader.unwrap()

        if not (engine := reader.get_engine(self._engine_name).unwrap_or_none()):
            return ControllerError.NoSuchResource(
                name=f'SyncSqlaEngine(name={self._engine_name})'
            ).to_result()

        engine.start()

        res = (
            engine.get_context(SqlaSyncConnCtx)
            .map(partial(collector.add, SqlaSyncConnCtx, name=self._engine_name))
            .unwrap_or(False)
        )
        res &= (
            engine.get_context(SqlaSyncSessionCtx)
            .map(partial(collector.add, SqlaSyncSessionCtx, name=self._engine_name))
            .unwrap_or(False)
        )

        return Ok(res)

    @override
    def teardown(
        self, collector: MutNamedCollector[type, Any]
    ) -> Result[bool, ControllerError]:
        if not self._reader:
            return ControllerError.NoSuchResource(
                name='EngineReader[SyncSqlaEngine]'
            ).to_result()

        reader = self._reader.unwrap()

        if not (engine := reader.get_engine(self._engine_name).unwrap_or_none()):
            return ControllerError.NoSuchResource(
                name=f'SyncSqlaEngine(name={self._engine_name})'
            ).to_result()

        engine.stop()

        res = collector.remove(SqlaSyncConnCtx, name=self._engine_name)
        res &= collector.remove(SqlaSyncSessionCtx, name=self._engine_name)
        return Ok(res)


class AsyncSqlaController(AsyncController):
    def __init__(self, engine_name: str) -> None:
        super().__init__()
        self._engine_name = engine_name
        self._reader: Maybe[EngineReader[AsyncSqlaEngine]] = Nothing

    def _setter(self, value: Maybe[EngineReader[AsyncSqlaEngine]]) -> None:
        self._reader = value

    @operator(EngineReader[AsyncSqlaEngine])
    def create_engine_operator(self) -> Operator[EngineReader[AsyncSqlaEngine]]:
        return AssignOperator[EngineReader[AsyncSqlaEngine]](lambda: self._reader, self._setter)

    @override
    async def setup(
        self, collector: NamedCollector[type, Any]
    ) -> Result[bool, ControllerError]:
        if not self._reader:
            return ControllerError.NoSuchResource(
                name='EngineReader[AsyncSqlaEngine]'
            ).to_result()

        reader = self._reader.unwrap()

        if not (engine := reader.get_engine(self._engine_name).unwrap_or_none()):
            return ControllerError.NoSuchResource(
                name=f'AsyncSqlaEngine(name={self._engine_name})'
            ).to_result()

        await engine.start()

        res = (
            engine.get_context(SqlaAsyncConnCtx)
            .map(partial(collector.add, SqlaAsyncConnCtx, name=self._engine_name))
            .unwrap_or(False)
        )
        res &= (
            engine.get_context(SqlaAsyncSessionCtx)
            .map(partial(collector.add, SqlaAsyncSessionCtx, name=self._engine_name))
            .unwrap_or(False)
        )

        return Ok(res)

    @override
    async def teardown(
        self, collector: MutNamedCollector[type, Any]
    ) -> Result[bool, ControllerError]:
        if not self._reader:
            return ControllerError.NoSuchResource(
                name='EngineReader[AsyncSqlaEngine]'
            ).to_result()

        reader = self._reader.unwrap()

        if not (engine := reader.get_engine(self._engine_name).unwrap_or_none()):
            return ControllerError.NoSuchResource(
                name=f'AsyncSqlaEngine(name={self._engine_name})'
            ).to_result()

        await engine.stop()

        res = collector.remove(SqlaAsyncConnCtx, name=self._engine_name)
        res &= collector.remove(SqlaAsyncSessionCtx, name=self._engine_name)
        return Ok(res)
