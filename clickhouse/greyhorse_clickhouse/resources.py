from typing import Mapping

from dependency_injector.containers import Container

from greyhorse_clickhouse.contexts import CHAsyncContext, CHAsyncContextFactory
from greyhorse_clickhouse.engine import CHAsyncEngine
from greyhorse_clickhouse.factory import CHAsyncEngineFactory
from greyhorse_core.app import base
from greyhorse_core.app.context import get_context


class CHAsyncResource(base.Resource, base.HasContainer):
    def __init__(
        self, container: Container,
        engine_factory: CHAsyncEngineFactory,
        context_factory: CHAsyncContextFactory,
        engine_names: list[str] | None = None,
    ):
        base.Resource.__init__(self)
        base.HasContainer.__init__(self, container)

        self._engine_factory = engine_factory
        self._context_factory = context_factory
        self._engine_names = engine_names or list()

    @property
    def engines(self) -> Mapping[str, CHAsyncEngine]:
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
            ctx = self._context_factory(engine)

            if 'ch' not in ctx_storage:
                ctx_storage.ch = ctx
            elif isinstance(ctx_storage.ch, CHAsyncContext):
                prev_ctx = ctx_storage.ch
                ctx_storage.ch = {prev_ctx.name: prev_ctx, name: ctx}
            else:
                ctx_storage.ch[name] = ctx

            await ctx.__aenter__()

    async def release(
        self, application: base.Application,
        module: base.Module | None = None,
        service: base.Service | None = None,
    ):
        ctx_storage = get_context()

        for name, engine in self.engines.items():
            if 'ch' not in ctx_storage:
                break
            elif isinstance(ctx_storage.ch, CHAsyncContext):
                ctx = ctx_storage.ch
                del ctx_storage.ch
            else:
                ctx = ctx_storage.ch.pop(name, None)

            if ctx:
                await ctx.__aexit__(None, None, None)

    def get_engine(self, name: str) -> CHAsyncEngine | None:
        return self._engine_factory.get_engine(name)
