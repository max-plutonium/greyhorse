from greyhorse_clickhouse.config import EngineConfig
from greyhorse_clickhouse.containers import CHAsyncContainer, MultipleCHAsyncContainer, SingleCHAsyncContainer
from greyhorse_clickhouse.engine import CHAsyncEngine
from greyhorse_clickhouse.resources import CHAsyncResource
from .conf import CH_URI


def test_base_async_container():
    config = EngineConfig(dsn=CH_URI)

    container = CHAsyncContainer()
    engine = container.create_engine('test', config)

    assert isinstance(engine, CHAsyncEngine)
    assert engine.name == 'test'

    resource = container.instance(container=container)
    assert isinstance(resource, CHAsyncResource)

    container.unwire()


def test_single_async_container():
    container = SingleCHAsyncContainer()

    container.config.from_dict({
        'name': 'test_single_async',
        'engine_config': {'dsn': CH_URI},
    })

    engine = container.create_engine()

    assert isinstance(engine, CHAsyncEngine)
    assert engine.name == 'test_single_async'
    assert engine is container.create_engine()

    resource = container.instance(container=container)
    assert isinstance(resource, CHAsyncResource)

    container.unwire()


def test_multiple_async_container():
    container = MultipleCHAsyncContainer()

    container.config.from_dict({
        'one': {
            'engine_config': {'dsn': CH_URI},
        },
        'two': {
            'engine_config': {'dsn': CH_URI},
        },
    })

    assert container.create_engine('_') is None
    engine1 = container.create_engine('one')
    engine2 = container.create_engine('two')

    assert isinstance(engine1, CHAsyncEngine)
    assert isinstance(engine2, CHAsyncEngine)
    assert engine1 is not engine2
    assert engine1.name == 'one'
    assert engine2.name == 'two'

    resource = container.instance(container=container)
    assert isinstance(resource, CHAsyncResource)

    container.unwire()
