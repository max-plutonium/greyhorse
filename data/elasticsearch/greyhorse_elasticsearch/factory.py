from typing import override

from greyhorse.data.storage import SimpleDataStorageFactory
from greyhorse.i18n import tr
from greyhorse.logging import logger
from .config import EngineConf
from .engine import ElasticSearchAsyncEngine


class ESAsyncEngineFactory(SimpleDataStorageFactory[ElasticSearchAsyncEngine]):
    # noinspection PyMethodOverriding
    @override
    def create_engine(self, name: str, config: EngineConf, *args, **kwargs) -> ElasticSearchAsyncEngine:
        if engine := self._engines.get(name):
            return engine

        engine = ElasticSearchAsyncEngine(name, config)
        self._engines[name] = engine
        logger.info(tr('greyhorse.engines.es.engine.created').format(name=name))
        return engine
