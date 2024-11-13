from functools import partial
from typing import override

from greyhorse.app.abc.controllers import ControllerError
from greyhorse.app.abc.operators import AssignOperator, Operator
from greyhorse.app.entities.controllers import AsyncController, SyncController, operator
from greyhorse.app.resources import Container
from greyhorse.data.storage import EngineSelector
from greyhorse.maybe import Maybe, Nothing
from greyhorse.result import Ok, Result

from .contexts import SqlaAsyncConnCtx, SqlaAsyncSessionCtx, SqlaSyncConnCtx, SqlaSyncSessionCtx
from .engine_async import AsyncSqlaEngine
from .engine_sync import SyncSqlaEngine


class SyncSqlaController(SyncController):
    def __init__(self, engine_name: str) -> None:
        super().__init__()
        self._engine_name = engine_name
        self._selector: Maybe[EngineSelector[SyncSqlaEngine]] = Nothing

    def _setter(self, value: Maybe[EngineSelector[SyncSqlaEngine]]) -> None:
        self._selector = value

    @operator(EngineSelector[SyncSqlaEngine])
    def create_engine_operator(self) -> Operator[EngineSelector[SyncSqlaEngine]]:
        return AssignOperator[EngineSelector[SyncSqlaEngine]](
            lambda: self._selector, self._setter
        )

    @override
    def setup(self, container: Container) -> Result[bool, ControllerError]:
        if self._selector:
            selector = self._selector.unwrap()
        elif (
            selector := container.get(EngineSelector[SyncSqlaEngine]).unwrap_or_none()
        ) is None:
            return ControllerError.NoSuchResource(
                name='EngineSelector[SyncSqlaEngine]'
            ).to_result()

        if (engine := selector.get(self._engine_name).unwrap_or_none()) is None:
            return ControllerError.NoSuchResource(
                name=f'SyncSqlaEngine(name={self._engine_name})'
            ).to_result()

        engine.start()

        res = (
            engine.get_context(SqlaSyncConnCtx)
            .map(partial(container.registry.add_factory, SqlaSyncConnCtx))
            .unwrap_or(False)
        )
        res &= (
            engine.get_context(SqlaSyncSessionCtx)
            .map(partial(container.registry.add_factory, SqlaSyncSessionCtx))
            .unwrap_or(False)
        )

        return Ok(res)

    @override
    def teardown(self, container: Container) -> Result[bool, ControllerError]:
        if self._selector:
            selector = self._selector.unwrap()
        elif (
            selector := container.get(EngineSelector[SyncSqlaEngine]).unwrap_or_none()
        ) is None:
            return ControllerError.NoSuchResource(
                name='EngineSelector[SyncSqlaEngine]'
            ).to_result()

        if (engine := selector.get(self._engine_name).unwrap_or_none()) is None:
            return ControllerError.NoSuchResource(
                name=f'SyncSqlaEngine(name={self._engine_name})'
            ).to_result()

        engine.stop()

        res = container.registry.remove_factory(SqlaSyncConnCtx)
        res &= container.registry.remove_factory(SqlaSyncSessionCtx)
        return Ok(res)


class AsyncSqlaController(AsyncController):
    def __init__(self, engine_name: str) -> None:
        super().__init__()
        self._engine_name = engine_name
        self._selector: Maybe[EngineSelector[AsyncSqlaEngine]] = Nothing

    def _setter(self, value: Maybe[EngineSelector[AsyncSqlaEngine]]) -> None:
        self._selector = value

    @operator(EngineSelector[AsyncSqlaEngine])
    def create_engine_operator(self) -> Operator[EngineSelector[AsyncSqlaEngine]]:
        return AssignOperator[EngineSelector[AsyncSqlaEngine]](
            lambda: self._selector, self._setter
        )

    @override
    async def setup(self, container: Container) -> Result[bool, ControllerError]:
        if self._selector:
            selector = self._selector.unwrap()
        elif (
            selector := container.get(EngineSelector[AsyncSqlaEngine]).unwrap_or_none()
        ) is None:
            return ControllerError.NoSuchResource(
                name='EngineSelector[AsyncSqlaEngine]'
            ).to_result()

        if (engine := selector.get(self._engine_name).unwrap_or_none()) is None:
            return ControllerError.NoSuchResource(
                name=f'AsyncSqlaEngine(name={self._engine_name})'
            ).to_result()

        await engine.start()

        res = (
            engine.get_context(SqlaAsyncConnCtx)
            .map(partial(container.registry.add_factory, SqlaAsyncConnCtx))
            .unwrap_or(False)
        )
        res &= (
            engine.get_context(SqlaAsyncSessionCtx)
            .map(partial(container.registry.add_factory, SqlaAsyncSessionCtx))
            .unwrap_or(False)
        )

        return Ok(res)

    @override
    async def teardown(self, container: Container) -> Result[bool, ControllerError]:
        if self._selector:
            selector = self._selector.unwrap()
        elif (
            selector := container.get(EngineSelector[AsyncSqlaEngine]).unwrap_or_none()
        ) is None:
            return ControllerError.NoSuchResource(
                name='EngineSelector[AsyncSqlaEngine]'
            ).to_result()

        if (engine := selector.get(self._engine_name).unwrap_or_none()) is None:
            return ControllerError.NoSuchResource(
                name=f'AsyncSqlaEngine(name={self._engine_name})'
            ).to_result()

        await engine.stop()

        res = container.registry.remove_factory(SqlaAsyncConnCtx)
        res &= container.registry.remove_factory(SqlaAsyncSessionCtx)
        return Ok(res)
