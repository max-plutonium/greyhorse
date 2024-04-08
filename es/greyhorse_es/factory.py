from typing import Mapping

from greyhorse.engines.factory import AsyncEngineFactory
from greyhorse.i18n import tr
from greyhorse.logging import logger
from greyhorse_es.config import EngineConfig
from greyhorse_es.engine import ESAsyncEngine


class ESAsyncEngineFactory(AsyncEngineFactory):
    def __init__(self):
        self._engines: dict[str, ESAsyncEngine] = dict()

    def get_engine_names(self) -> list[str]:
        return list(self._engines.keys())

    def get_engine(self, name: str) -> ESAsyncEngine | None:
        return self._engines.get(name)

    def get_engines(self, names: list[str] | None = None) -> Mapping[str, ESAsyncEngine]:
        engines = dict()

        if not names:
            names = self.get_engine_names()

        for name in names:
            if engine := self.get_engine(name):
                engines[name] = engine

        return engines

    # noinspection PyMethodOverriding
    def __call__(self, name: str, config: EngineConfig, *args, **kwargs) -> ESAsyncEngine:
        if engine := self._engines.get(name):
            return engine

        engine = ESAsyncEngine(name, config)
        self._engines[name] = engine
        logger.info(tr('greyhorse.engines.es.engine.created').format(name=name))
        return engine
