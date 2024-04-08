from typing import Mapping

from greyhorse.engines.factory import AsyncEngineFactory
from greyhorse.i18n import tr
from greyhorse.logging import logger
from greyhorse_rmq.config import EngineConfig
from greyhorse_rmq.engine import RmqAsyncEngine


class RmqAsyncEngineFactory(AsyncEngineFactory):
    def __init__(self):
        self._engines: dict[str, RmqAsyncEngine] = dict()

    def get_engine_names(self) -> list[str]:
        return list(self._engines.keys())

    def get_engine(self, name: str) -> RmqAsyncEngine | None:
        return self._engines.get(name)

    def get_engines(self, names: list[str] | None = None) -> Mapping[str, RmqAsyncEngine]:
        engines = dict()

        if not names:
            names = self.get_engine_names()

        for name in names:
            if engine := self.get_engine(name):
                engines[name] = engine

        return engines

    # noinspection PyMethodOverriding
    def __call__(self, name: str, config: EngineConfig, *args, **kwargs) -> RmqAsyncEngine:
        if engine := self._engines.get(name):
            return engine

        engine = RmqAsyncEngine(name, config)
        self._engines[name] = engine
        logger.info(tr('greyhorse.engines.rmq.engine.created').format(name=name))
        return engine
