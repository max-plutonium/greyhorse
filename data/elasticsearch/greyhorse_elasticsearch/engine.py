from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import override

from elasticsearch import AsyncElasticsearch

from greyhorse.app.context import AsyncContextBuilder, Context
from greyhorse.data.storage import DataStorageEngine
from greyhorse.i18n import tr
from greyhorse.logging import logger
from .config import EngineConf
from .contexts import ElasticSearchContext

type AsyncChannel = AsyncElasticsearch


class ElasticSearchAsyncEngine(DataStorageEngine):
    def __init__(self, name: str, config: EngineConf):
        super().__init__(name)
        self._es = AsyncElasticsearch(str(config.dsn))
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    @override
    async def start(self):
        logger.info(tr('greyhorse.engines.es.engine.started').format(name=self.name))
        self._active = True

    @override
    async def stop(self):
        logger.info(tr('greyhorse.engines.es.engine.stopped').format(name=self.name))
        self._active = False

    @asynccontextmanager
    async def session(self) -> AbstractAsyncContextManager[AsyncChannel]:
        async with self._es as conn:
            yield conn

    @override
    def get_context[T: Context](self, kind: type[ElasticSearchContext]) -> T | None:
        if kind is ElasticSearchContext:
            builder = AsyncContextBuilder[ElasticSearchContext](kind)
            builder.add_param('name', self.name)
            builder.add_param('connection', self.session)
            return builder.build()
        else:
            return None
