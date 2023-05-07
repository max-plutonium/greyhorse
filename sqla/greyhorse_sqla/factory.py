import re
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import timedelta
from typing import Mapping

from orjson import orjson
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.ext.asyncio import create_async_engine

from greyhorse_core.engines.factory import SyncEngineFactory, AsyncEngineFactory
from greyhorse_core.i18n import tr
from greyhorse_core.logging import logger
from greyhorse_sqla.config import SqlEngineType, EngineConfig
from greyhorse_sqla.engine import SqlaSyncEngine, SqlaAsyncEngine


def _prepare_params(db_type: SqlEngineType, config: EngineConfig) -> dict:
    params = dict(
        echo=config.echo,
        echo_pool=config.echo,
        pool_pre_ping=True,
        pool_recycle=config.pool_expire_seconds,
        json_serializer=orjson.dumps,
        json_deserializer=orjson.loads,
    )

    if db_type in (SqlEngineType.POSTGRES, SqlEngineType.MYSQL):
        params.update(dict(
            pool_size=config.pool_min_size,
            max_overflow=config.pool_max_size - config.pool_min_size,
            pool_timeout=config.pool_timeout_seconds,
        ))

    return params


class SqlaSyncEngineFactory(SyncEngineFactory):
    def __init__(self):
        self._engines: dict[str, SqlaSyncEngine] = dict()
        self._engines_by_type: dict[SqlEngineType, set[str]] = defaultdict(set)

    def get_engine_names(self) -> list[str]:
        return list(self._engines.keys())

    def get_engine(self, name: str) -> SqlaSyncEngine | None:
        return self._engines.get(name)

    def get_engines(self, names: list[str] | None = None) -> Mapping[str, SqlaSyncEngine]:
        engines = dict()

        if not names:
            names = self.get_engine_names()

        for name in names:
            if engine := self.get_engine(name):
                engines[name] = engine

        return engines

    def get_engines_for_type(self, db_type: SqlEngineType) -> list[SqlaSyncEngine]:
        engine_names = self._engines_by_type[db_type]
        return [self.get_engine(name) for name in engine_names]

    # noinspection PyMethodOverriding
    def __call__(self, name: str, config: EngineConfig,
                 db_type: SqlEngineType, *args, **kwargs) -> SqlaSyncEngine:
        if engine := self._engines.get(name):
            return engine

        dsn = config.dsn

        if db_type == SqlEngineType.MYSQL:
            dsn = re.sub(r'^mysql://', lambda _: 'mysql+pymysql://', dsn)

        config = replace(config, dsn=dsn)
        params = _prepare_params(db_type, config)
        engine = create_sync_engine(config.dsn, **params)

        logger.info(tr('greyhorse.engines.sql.engine.created')
                    .format(name=name, db_type=db_type.value, async_='sync'))

        engine = SqlaSyncEngine(
            name, engine, db_type, timedelta(seconds=config.pool_timeout_seconds),
        )

        self._engines[name] = engine
        self._engines_by_type[db_type].add(name)
        return engine


class SqlaAsyncEngineFactory(AsyncEngineFactory):
    def __init__(self):
        self._engines: dict[str, SqlaAsyncEngine] = dict()
        self._engines_by_type: dict[SqlEngineType, set[str]] = defaultdict(set)

    def get_engine_names(self) -> list[str]:
        return list(self._engines.keys())

    def get_engine(self, name: str) -> SqlaAsyncEngine | None:
        return self._engines.get(name)

    def get_engines(self, names: list[str] | None = None) -> Mapping[str, SqlaAsyncEngine]:
        engines = dict()

        if not names:
            names = self.get_engine_names()

        for name in names:
            if engine := self.get_engine(name):
                engines[name] = engine

        return engines

    def get_engines_for_type(self, db_type: SqlEngineType) -> list[SqlaAsyncEngine]:
        engine_names = self._engines_by_type[db_type]
        return [self.get_engine(name) for name in engine_names]

    # noinspection PyMethodOverriding
    def __call__(self, name: str, config: EngineConfig,
                 db_type: SqlEngineType, *args, **kwargs) -> SqlaAsyncEngine:
        if engine := self._engines.get(name):
            return engine

        dsn = config.dsn

        if db_type == SqlEngineType.SQLITE:
            dsn = re.sub(r'^sqlite://', lambda _: 'sqlite+aiosqlite://', dsn)
        elif db_type == SqlEngineType.POSTGRES:
            dsn = re.sub(r'^postgresql://', lambda _: 'postgresql+asyncpg://', dsn)
        elif db_type == SqlEngineType.MYSQL:
            dsn = re.sub(r'^mysql://', lambda _: 'mysql+aiomysql://', dsn)

        config = replace(config, dsn=dsn)
        params = _prepare_params(db_type, config)
        engine = create_async_engine(config.dsn, **params)

        logger.info(tr('greyhorse.engines.sql.engine.created')
                    .format(name=name, db_type=db_type.value, async_='async'))

        engine = SqlaAsyncEngine(
            name, engine, db_type, timedelta(seconds=config.pool_timeout_seconds),
        )

        self._engines[name] = engine
        self._engines_by_type[db_type].add(name)
        return engine
