from typing import Mapping

from dependency_injector.containers import Container

from greyhorse.app import base
from greyhorse.app.context import get_context
from greyhorse_es.contexts import ESAsyncContext, ESAsyncContextFactory
from greyhorse_es.engine import ESAsyncEngine
from greyhorse_es.factory import ESAsyncEngineFactory


class ESAsyncResource(base.Resource, base.HasContainer):
    def __init__(
        self, container: Container,
        engine_factory: ESAsyncEngineFactory,
        context_factory: ESAsyncContextFactory,
        engine_names: list[str] | None = None,
    ):
        base.Resource.__init__(self)
        base.HasContainer.__init__(self, container)

        self._engine_factory = engine_factory
        self._context_factory = context_factory
        self._engine_names = engine_names or list()

    @property
    def engines(self) -> Mapping[str, ESAsyncEngine]:
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

            if 'es' not in ctx_storage:
                ctx_storage.es = ctx
            elif isinstance(ctx_storage.es, ESAsyncContext):
                prev_ctx = ctx_storage.es
                ctx_storage.es = {prev_ctx.name: prev_ctx, name: ctx}
            else:
                ctx_storage.es[name] = ctx

            await ctx.__aenter__()

    async def release(
        self, application: base.Application,
        module: base.Module | None = None,
        service: base.Service | None = None,
    ):
        ctx_storage = get_context()

        for name, engine in self.engines.items():
            if 'es' not in ctx_storage:
                break
            elif isinstance(ctx_storage.es, ESAsyncContext):
                ctx = ctx_storage.es
                del ctx_storage.es
            else:
                ctx = ctx_storage.es.pop(name, None)

            if ctx:
                await ctx.__aexit__(None, None, None)

    def get_engine(self, name: str) -> ESAsyncEngine | None:
        return self._engine_factory.get_engine(name)
