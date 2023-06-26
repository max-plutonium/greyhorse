from typing import Mapping

from dependency_injector.containers import Container

from greyhorse_core.app import base
from greyhorse_core.app.context import get_context
from greyhorse_sqla.contexts import SqlaSyncContextFactory, SqlaSyncContext, SqlaAsyncContextFactory, SqlaAsyncContext
from greyhorse_sqla.engine import SqlaSyncEngine, SqlaAsyncEngine
from greyhorse_sqla.factory import SqlaSyncEngineFactory, SqlaAsyncEngineFactory


class SqlaSyncResource(base.Resource, base.HasContainer):
    def __init__(
        self, container: Container,
        engine_factory: SqlaSyncEngineFactory,
        context_factory: SqlaSyncContextFactory,
        force_rollback: bool = False,
        engine_names: list[str] | None = None,
    ):
        base.Resource.__init__(self)
        base.HasContainer.__init__(self, container)

        self._engine_factory = engine_factory
        self._context_factory = context_factory
        self._force_rollback = force_rollback
        self._engine_names = engine_names or list()

    @property
    def engines(self) -> Mapping[str, SqlaSyncEngine]:
        return self._engine_factory.get_engines()

    def create(
        self, application: base.Application,
        module: base.Module | None = None,
        service: base.Service | None = None,
    ):
        for name in self._engine_names:
            self.container.create_engine(name)
        else:
            self.container.create_engine()

        for engine in self.engines.values():
            engine.start()

    def destroy(
        self, application: base.Application,
        module: base.Module | None = None,
        service: base.Service | None = None,
    ):
        for engine in reversed(self.engines.values()):
            engine.stop()

    def acquire(
        self, application: base.Application,
        module: base.Module | None = None,
        service: base.Service | None = None,
    ):
        ctx_storage = get_context()

        for name, engine in self.engines.items():
            ctx = self._context_factory(engine, self._force_rollback)

            if 'sqla' not in ctx_storage:
                ctx_storage.sqla = ctx
            elif isinstance(ctx_storage.sqla, SqlaSyncContext):
                prev_ctx = ctx_storage.sqla
                ctx_storage.sqla = {prev_ctx.name: prev_ctx, name: ctx}
            else:
                ctx_storage.sqla[name] = ctx

            ctx.__enter__()

    def release(
        self, application: base.Application,
        module: base.Module | None = None,
        service: base.Service | None = None,
    ):
        ctx_storage = get_context()

        for name, engine in self.engines.items():
            if 'sqla' not in ctx_storage:
                break
            elif isinstance(ctx_storage.sqla, SqlaSyncContext):
                ctx = ctx_storage.sqla
                del ctx_storage.sqla
            else:
                ctx = ctx_storage.sqla.pop(name, None)

            if ctx:
                ctx.__exit__(None, None, None)

    def get_engine(self, name: str) -> SqlaSyncEngine | None:
        return self._engine_factory.get_engine(name)


class SqlaAsyncResource(base.Resource, base.HasContainer):
    def __init__(
        self, container: Container,
        engine_factory: SqlaAsyncEngineFactory,
        context_factory: SqlaAsyncContextFactory,
        force_rollback: bool = False,
        engine_names: list[str] | None = None,
    ):
        base.Resource.__init__(self)
        base.HasContainer.__init__(self, container)

        self._engine_factory = engine_factory
        self._context_factory = context_factory
        self._force_rollback = force_rollback
        self._engine_names = engine_names or list()

    @property
    def engines(self) -> Mapping[str, SqlaAsyncEngine]:
        return self._engine_factory.get_engines()

    async def create(
        self, application: base.Application,
        module: base.Module | None = None,
        service: base.Service | None = None,
    ):
        for name in self._engine_names:
            self.container.create_engine(name)
        else:
            self.container.create_engine()

        for engine in self.engines.values():
            await engine.start()

    async def destroy(
        self, application: base.Application,
        module: base.Module | None = None,
        service: base.Service | None = None,
    ):
        for engine in reversed(self.engines.values()):
            await engine.stop()

    async def acquire(
        self, application: base.Application,
        module: base.Module | None = None,
        service: base.Service | None = None,
    ):
        ctx_storage = get_context()

        for name, engine in self.engines.items():
            ctx = self._context_factory(engine, self._force_rollback)

            if 'sqla' not in ctx_storage:
                ctx_storage.sqla = ctx
            elif isinstance(ctx_storage.sqla, SqlaAsyncContext):
                prev_ctx = ctx_storage.sqla
                ctx_storage.sqla = {prev_ctx.name: prev_ctx, name: ctx}
            else:
                ctx_storage.sqla[name] = ctx

            await ctx.__aenter__()

    async def release(
        self, application: base.Application,
        module: base.Module | None = None,
        service: base.Service | None = None,
    ):
        ctx_storage = get_context()

        for name, engine in self.engines.items():
            if 'sqla' not in ctx_storage:
                break
            elif isinstance(ctx_storage.sqla, SqlaAsyncContext):
                ctx = ctx_storage.sqla
                del ctx_storage.sqla
            else:
                ctx = ctx_storage.sqla.pop(name, None)

            if ctx:
                await ctx.__aexit__(None, None, None)

    def get_engine(self, name: str) -> SqlaAsyncEngine | None:
        return self._engine_factory.get_engine(name)
