from typing import override

from greyhorse.data.storage import SimpleDataStorageFactory
from greyhorse.i18n import tr
from greyhorse.logging import logger
from .config import EngineConf
from .engine import RmqAsyncEngine


class RmqAsyncEngineFactory(SimpleDataStorageFactory[RmqAsyncEngine]):
    # noinspection PyMethodOverriding
    @override
    def create_engine(self, name: str, config: EngineConf, *args, **kwargs) -> RmqAsyncEngine:
        if engine := self._engines.get(name):
            return engine

        engine = RmqAsyncEngine(name, config)
        self._engines[name] = engine
        logger.info(tr('greyhorse.engines.rmq.engine.created').format(name=name))
        return engine
