from typing import override

from greyhorse.data.storage import SimpleDataStorageFactory
from greyhorse.i18n import tr
from greyhorse.logging import logger
from .config import EngineConf
from .engine import RedisAsyncEngine, RedisSyncEngine


class RedisSyncEngineFactory(SimpleDataStorageFactory[RedisSyncEngine]):
    # noinspection PyMethodOverriding
    @override
    def create_engine(self, name: str, config: EngineConf, *args, **kwargs) -> RedisSyncEngine:
        if engine := self._engines.get(name):
            return engine

        engine = RedisSyncEngine(name, config)
        self._engines[name] = engine
        logger.info(tr('greyhorse.engines.redis.engine.created').format(name=name))
        return engine


class RedisAsyncEngineFactory(SimpleDataStorageFactory[RedisAsyncEngine]):
    # noinspection PyMethodOverriding
    @override
    def create_engine(self, name: str, config: EngineConf, *args, **kwargs) -> RedisAsyncEngine:
        if engine := self._engines.get(name):
            return engine

        engine = RedisAsyncEngine(name, config)
        self._engines[name] = engine
        logger.info(tr('greyhorse.engines.redis.engine.created').format(name=name))
        return engine
