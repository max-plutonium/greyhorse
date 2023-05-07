from dependency_injector import containers, providers

from greyhorse_core.utils.confs import default_value
from greyhorse_sqla.config import EngineConfig, SqlEngineType
from greyhorse_sqla.factory import SqlaSyncEngineFactory, SqlaAsyncEngineFactory
from greyhorse_sqla.resources import SqlaSyncResource, SqlaAsyncResource


def _prepare_single_engine_config(config, factory):
    if isinstance(config.engine_config(), EngineConfig):
        engine_config = config.engine_config()
    else:
        engine_config = EngineConfig(
            dsn=config.engine_config.dsn(),
            echo=config.engine_config.echo.as_(bool)(),
            pool_min_size=config.engine_config.
                pool_min_size.as_(default_value(int))(default=1),
            pool_max_size=config.engine_config.
                pool_max_size.as_(default_value(int))(default=8),
            pool_expire_seconds=config.engine_config.
                pool_expire_seconds.as_(default_value(int))(default=60),
            pool_timeout_seconds=config.engine_config.
                pool_timeout_seconds.as_(default_value(int))(default=15)
        )
    return factory(name=config.name(), config=engine_config, db_type=config.db_type())


def _prepare_multiple_engine_config(name: str, config, factory):
    if conf := config.get(name):
        if isinstance(conf['engine_config'], EngineConfig):
            engine_config = conf['engine_config']
        else:
            engine_config = EngineConfig(
                dsn=conf['engine_config']['dsn'],
                echo=bool(conf['engine_config'].get('echo')),
                pool_min_size=int(conf['engine_config'].get('pool_min_size', 1)),
                pool_max_size=int(conf['engine_config'].get('pool_max_size', 8)),
                pool_expire_seconds=int(conf['engine_config'].get('pool_expire_seconds', 60)),
                pool_timeout_seconds=int(conf['engine_config'].get('pool_timeout_seconds', 15))
            )
        return factory(name=name, config=engine_config, db_type=conf['db_type'])

    return None


class SqlaSyncContainer(containers.DeclarativeContainer):
    __self__ = providers.Self()
    engine_factory = providers.Singleton(SqlaSyncEngineFactory)

    def _create_engine(self, name: str, config: EngineConfig, db_type: SqlEngineType, *args, **kwargs):
        return self.engine_factory()(name, config, db_type, *args, **kwargs)

    create_engine = providers.Factory(_create_engine, __self__)
    instance = providers.Singleton(SqlaSyncResource, engine_factory)


class SqlaAsyncContainer(containers.DeclarativeContainer):
    __self__ = providers.Self()
    engine_factory = providers.Singleton(SqlaAsyncEngineFactory)

    def _create_engine(self, name: str, config: EngineConfig, db_type: SqlEngineType, *args, **kwargs):
        return self.engine_factory()(name, config, db_type, *args, **kwargs)

    create_engine = providers.Factory(_create_engine, __self__)
    instance = providers.Singleton(SqlaAsyncResource, engine_factory)


class SingleSqlaSyncContainer(SqlaSyncContainer):
    __self__ = providers.Self()
    config = providers.Configuration()

    create_engine = providers.Factory(
        _prepare_single_engine_config, config.provider,
        providers.Factory(SqlaSyncContainer._create_engine, __self__).provider,
    )


class SingleSqlaAsyncContainer(SqlaAsyncContainer):
    __self__ = providers.Self()
    config = providers.Configuration()

    create_engine = providers.Factory(
        _prepare_single_engine_config, config.provider,
        providers.Factory(SqlaAsyncContainer._create_engine, __self__).provider,
    )


class MultipleSqlaSyncContainer(SqlaSyncContainer):
    __self__ = providers.Self()
    config = providers.Configuration()

    create_engine = providers.Factory(
        _prepare_multiple_engine_config, config=config.provider,
        factory=providers.Factory(SqlaSyncContainer._create_engine, __self__).provider,
    )


class MultipleSqlaAsyncContainer(SqlaAsyncContainer):
    __self__ = providers.Self()
    config = providers.Configuration()

    create_engine = providers.Factory(
        _prepare_multiple_engine_config, config=config.provider,
        factory=providers.Factory(SqlaAsyncContainer._create_engine, __self__).provider,
    )
