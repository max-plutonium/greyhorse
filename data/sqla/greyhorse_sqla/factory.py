import re
from typing import override

from greyhorse.data.storage import SimpleEngineFactory
from greyhorse.i18n import tr
from greyhorse.logging import logger
from greyhorse.utils import json
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.ext.asyncio import create_async_engine

from .config import EngineConf, SqlEngineType
from .engine_async import AsyncSqlaEngine
from .engine_sync import SyncSqlaEngine


def _prepare_params(config: EngineConf) -> dict:
    params = dict(
        echo=config.echo,
        echo_pool=config.echo,
        pool_pre_ping=True,
        pool_recycle=config.pool_expire_seconds,
        json_serializer=json.dumps,
        json_deserializer=json.loads,
    )

    if config.type in (SqlEngineType.POSTGRES, SqlEngineType.MYSQL):
        params.update(
            dict(
                pool_size=config.pool_min_size,
                max_overflow=config.pool_max_size - config.pool_min_size,
                pool_timeout=config.pool_timeout_seconds,
            )
        )

    return params


class SyncSqlaEngineFactory(SimpleEngineFactory[SyncSqlaEngine]):
    @override
    def create_engine(self, name: str, config: EngineConf) -> SyncSqlaEngine:
        if engine := self._engines.get(name).unwrap_or_none():
            return engine

        dsn = str(config.dsn)

        if config.type == SqlEngineType.MYSQL:
            config.dsn = re.sub(r'^mysql://', lambda _: 'mysql+pymysql://', dsn)

        params = _prepare_params(config)
        engine = create_sync_engine(str(config.dsn), **params).execution_options(
            timeout=config.pool_timeout_seconds
        )

        logger.info(
            tr(
                'greyhorse.engines.sqla.engine.created',
                name=name,
                db_type=config.type.value,
                async_='sync',
            )
        )

        engine = SyncSqlaEngine(name, config, engine)
        self._engines.add(name, engine)
        return engine


class AsyncSqlaEngineFactory(SimpleEngineFactory[AsyncSqlaEngine]):
    @override
    def create_engine(self, name: str, config: EngineConf) -> AsyncSqlaEngine:
        if engine := self._engines.get(name).unwrap_or_none():
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
            timeout=config.pool_timeout_seconds
        )

        logger.info(
            tr(
                'greyhorse.engines.sqla.engine.created',
                name=name,
                db_type=config.type.value,
                async_='async',
            )
        )

        engine = AsyncSqlaEngine(name, config, engine)
        self._engines.add(name, engine)
        return engine
