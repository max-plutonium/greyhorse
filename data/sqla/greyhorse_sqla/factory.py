import re
from typing import override

from orjson import orjson
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.ext.asyncio import create_async_engine

from greyhorse.data.storage import SimpleDataStorageFactory
from greyhorse.i18n import tr
from greyhorse.logging import logger
from .config import EngineConf, SqlEngineType
from .engine import SqlaAsyncEngine, SqlaSyncEngine


def _prepare_params(config: EngineConf) -> dict:
    params = dict(
        echo=config.echo,
        echo_pool=config.echo,
        pool_pre_ping=True,
        pool_recycle=config.pool_expire_seconds,
        json_serializer=orjson.dumps,
        json_deserializer=orjson.loads,
    )

    if config.type in (SqlEngineType.POSTGRES, SqlEngineType.MYSQL):
        params.update(dict(
            pool_size=config.pool_min_size,
            max_overflow=config.pool_max_size - config.pool_min_size,
            pool_timeout=config.pool_timeout_seconds,
        ))

    return params


class SqlaSyncEngineFactory(SimpleDataStorageFactory[SqlaSyncEngine]):
    # noinspection PyMethodOverriding
    @override
    def create_engine(self, name: str, config: EngineConf, *args, **kwargs) -> SqlaSyncEngine:
        if engine := self._engines.get(name):
            return engine

        dsn = str(config.dsn)

        if config.type == SqlEngineType.MYSQL:
            config.dsn = re.sub(r'^mysql://', lambda _: 'mysql+pymysql://', dsn)

        params = _prepare_params(config)
        engine = create_sync_engine(str(config.dsn), **params).execution_options(
            timeout=config.pool_timeout_seconds,
        )

        logger.info(
            tr('greyhorse.engines.sqla.engine.created')
            .format(name=name, db_type=config.type.value, async_='sync')
        )

        engine = SqlaSyncEngine(name, config, engine)
        self._engines[name] = engine
        return engine


class SqlaAsyncEngineFactory(SimpleDataStorageFactory[SqlaAsyncEngine]):
    # noinspection PyMethodOverriding
    @override
    def create_engine(self, name: str, config: EngineConf, *args, **kwargs) -> SqlaAsyncEngine:
        if engine := self._engines.get(name):
            return engine

        dsn = str(config.dsn)

        match config.type:
            case SqlEngineType.SQLITE:
                config.dsn = re.sub(r'^(sqlite|file)://', lambda _: 'sqlite+aiosqlite://', dsn)
            case SqlEngineType.POSTGRES:
                config.dsn = re.sub(r'^postgresql://', lambda _: 'postgresql+asyncpg://', dsn)
            case SqlEngineType.MYSQL:
                config.dsn = re.sub(r'^mysql://', lambda _: 'mysql+aiomysql://', dsn)

        params = _prepare_params(config)
        engine = create_async_engine(str(config.dsn), **params).execution_options(
            timeout=config.pool_timeout_seconds,
        )

        logger.info(
            tr('greyhorse.engines.sqla.engine.created')
            .format(name=name, db_type=config.type.value, async_='async')
        )

        engine = SqlaAsyncEngine(name, config, engine)
        self._engines[name] = engine
        return engine
