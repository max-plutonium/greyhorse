from dependency_injector import containers, providers

from greyhorse_clickhouse.config import EngineConfig
from greyhorse_clickhouse.contexts import CHAsyncContext
from greyhorse_clickhouse.factory import CHAsyncEngineFactory
from greyhorse_clickhouse.resources import CHAsyncResource
from greyhorse_core.utils.confs import default_value


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
        )
    return factory(name=config.name(), config=engine_config)


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
            )
        return factory(name=name, config=engine_config)

    return None


class CHAsyncContainer(containers.DeclarativeContainer):
    __self__ = providers.Self()
    engine_factory = providers.Singleton(CHAsyncEngineFactory)
    context_factory = providers.Dependency(default=CHAsyncContext)
    engine_names = providers.List()

    def _create_engine(self, name: str, config: EngineConfig):
        return self.engine_factory()(name, config)

    create_engine = providers.Factory(_create_engine, __self__)
    instance = providers.Singleton(
        CHAsyncResource,
        engine_factory=engine_factory,
        context_factory=context_factory,
        engine_names=engine_names,
    )


class SingleCHAsyncContainer(CHAsyncContainer):
    __self__ = providers.Self()
    config = providers.Configuration()

    create_engine = providers.Factory(
        _prepare_single_engine_config, config.provider,
        providers.Factory(CHAsyncContainer._create_engine, __self__).provider,
    )


class MultipleCHAsyncContainer(CHAsyncContainer):
    __self__ = providers.Self()
    config = providers.Configuration()

    create_engine = providers.Factory(
        _prepare_multiple_engine_config, config=config.provider,
        factory=providers.Factory(CHAsyncContainer._create_engine, __self__).provider,
    )
