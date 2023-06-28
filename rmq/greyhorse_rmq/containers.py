from dependency_injector import containers, providers

from greyhorse_core.utils.confs import default_value
from greyhorse_rmq.config import EngineConfig
from greyhorse_rmq.contexts import RmqAsyncContext
from greyhorse_rmq.factory import RmqAsyncEngineFactory
from greyhorse_rmq.resources import RmqAsyncResource


def _prepare_single_engine_config(config, factory):
    if isinstance(config.engine_config(), EngineConfig):
        engine_config = config.engine_config()
    else:
        engine_config = EngineConfig(
            dsn=config.engine_config.dsn(),
            virtualhost=config.engine_config.virtualhost.
                as_(default_value(str))(default='/'),
            timeout_seconds=config.engine_config.
                timeout_seconds.as_(default_value(int))(default=5),
            pool_max_connections=config.engine_config.
                pool_max_connections.as_(default_value(int))(default=4),
            pool_max_channels_per_connection=config.engine_config.
                pool_max_channels_per_connection.as_(default_value(int))(default=100),
        )
    return factory(name=config.name(), config=engine_config)


def _prepare_multiple_engine_config(name: str, config, factory):
    if conf := config.get(name):
        if isinstance(conf['engine_config'], EngineConfig):
            engine_config = conf['engine_config']
        else:
            engine_config = EngineConfig(
                dsn=conf['engine_config']['dsn'],
                virtualhost=conf['engine_config'].get('virtualhost', '/'),
                timeout_seconds=int(conf['engine_config'].get('timeout_seconds', 5)),
                pool_max_connections=int(conf['engine_config'].get('pool_max_connections', 4)),
                pool_max_channels_per_connection=int(conf['engine_config'].get(
                    'pool_max_channels_per_connection', 100)),
            )
        return factory(name=name, config=engine_config)

    return None


class RmqAsyncContainer(containers.DeclarativeContainer):
    __self__ = providers.Self()
    engine_factory = providers.Singleton(RmqAsyncEngineFactory)
    context_factory = providers.Dependency(default=RmqAsyncContext)

    def _create_engine(self, name: str, config: EngineConfig):
        return self.engine_factory()(name, config)

    create_engine = providers.Factory(_create_engine, __self__)
    instance = providers.Singleton(
        RmqAsyncResource,
        engine_factory=engine_factory,
        context_factory=context_factory,
    )


class SingleRmqAsyncContainer(RmqAsyncContainer):
    __self__ = providers.Self()
    config = providers.Configuration()

    create_engine = providers.Factory(
        _prepare_single_engine_config, config.provider,
        providers.Factory(RmqAsyncContainer._create_engine, __self__).provider,
    )


class MultipleRmqAsyncContainer(RmqAsyncContainer):
    __self__ = providers.Self()
    config = providers.Configuration()

    create_engine = providers.Factory(
        _prepare_multiple_engine_config, config=config.provider,
        factory=providers.Factory(RmqAsyncContainer._create_engine, __self__).provider,
    )
