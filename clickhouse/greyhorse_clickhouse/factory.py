from typing import Mapping

from greyhorse_clickhouse.config import EngineConfig
from greyhorse_clickhouse.engine import CHAsyncEngine
from greyhorse_core.engines.factory import AsyncEngineFactory
from greyhorse_core.i18n import tr
from greyhorse_core.logging import logger


class CHAsyncEngineFactory(AsyncEngineFactory):
    def __init__(self):
        self._engines: dict[str, CHAsyncEngine] = dict()

    def get_engine_names(self) -> list[str]:
        return list(self._engines.keys())

    def get_engine(self, name: str) -> CHAsyncEngine | None:
        return self._engines.get(name)

    def get_engines(self, names: list[str] | None = None) -> Mapping[str, CHAsyncEngine]:
        engines = dict()

        if not names:
            names = self.get_engine_names()

        for name in names:
            if engine := self.get_engine(name):
                engines[name] = engine

        return engines

    # noinspection PyMethodOverriding
    def __call__(self, name: str, config: EngineConfig, *args, **kwargs) -> CHAsyncEngine:
        if engine := self._engines.get(name):
            return engine

        engine = CHAsyncEngine(name, config)
        self._engines[name] = engine
        logger.info(tr('greyhorse.engines.ch.engine.created').format(name=name))
        return engine
