from contextlib import AbstractAsyncContextManager, asynccontextmanager

from elasticsearch import AsyncElasticsearch

from greyhorse_core.engines.base import AsyncEngine
from greyhorse_core.i18n import tr
from greyhorse_core.logging import logger
from greyhorse_es.config import EngineConfig

AsyncConnection = AsyncElasticsearch


class ESAsyncEngine(AsyncEngine[AsyncConnection]):
    def __init__(self, name: str, config: EngineConfig):
        super().__init__(name)
        self._config = config
        self._es = AsyncElasticsearch(config.dsn)

    @property
    def connection_class(self):
        return AsyncConnection

    @asynccontextmanager
    async def session(self, *args, **kwargs) -> AbstractAsyncContextManager[AsyncConnection]:
        async with self._es as conn:
            yield conn

    async def start(self):
        logger.info(tr('greyhorse.engines.es.engine.started').format(name=self.name))

    async def stop(self):
        logger.info(tr('greyhorse.engines.es.engine.stopped').format(name=self.name))
