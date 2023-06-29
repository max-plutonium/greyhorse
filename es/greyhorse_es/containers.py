from dependency_injector import containers, providers

from greyhorse_es.config import EngineConfig
from greyhorse_es.contexts import ESAsyncContext
from greyhorse_es.factory import ESAsyncEngineFactory
from greyhorse_es.resources import ESAsyncResource


def _prepare_single_engine_config(config, factory):
    if isinstance(config.engine_config(), EngineConfig):
        engine_config = config.engine_config()
    else:
        engine_config = EngineConfig(
            dsn=config.engine_config.dsn(),
        )
    return factory(name=config.name(), config=engine_config)


def _prepare_multiple_engine_config(name: str, config, factory):
    if conf := config.get(name):
        if isinstance(conf['engine_config'], EngineConfig):
            engine_config = conf['engine_config']
        else:
            engine_config = EngineConfig(
                dsn=conf['engine_config']['dsn'],
            )
        return factory(name=name, config=engine_config)

    return None


class ESAsyncContainer(containers.DeclarativeContainer):
    __self__ = providers.Self()
    engine_factory = providers.Singleton(ESAsyncEngineFactory)
    context_factory = providers.Dependency(default=ESAsyncContext)
    engine_names = providers.List()

    def _create_engine(self, name: str, config: EngineConfig):
        return self.engine_factory()(name, config)

    create_engine = providers.Factory(_create_engine, __self__)
    instance = providers.Singleton(
        ESAsyncResource,
        engine_factory=engine_factory,
        context_factory=context_factory,
        engine_names=engine_names,
    )


class SingleESAsyncContainer(ESAsyncContainer):
    __self__ = providers.Self()
    config = providers.Configuration()

    create_engine = providers.Factory(
        _prepare_single_engine_config, config.provider,
        providers.Factory(ESAsyncContainer._create_engine, __self__).provider,
    )


class MultipleESAsyncContainer(ESAsyncContainer):
    __self__ = providers.Self()
    config = providers.Configuration()

    create_engine = providers.Factory(
        _prepare_multiple_engine_config, config=config.provider,
        factory=providers.Factory(ESAsyncContainer._create_engine, __self__).provider,
    )
