from conf import RMQ_URI

from greyhorse_rmq.config import EngineConfig
from greyhorse_rmq.containers import MultipleRmqAsyncContainer, RmqAsyncContainer, SingleRmqAsyncContainer
from greyhorse_rmq.engine import RmqAsyncEngine
from greyhorse_rmq.resources import RmqAsyncResource


def test_base_async_container():
    config = EngineConfig(dsn=RMQ_URI)

    container = RmqAsyncContainer()
    engine = container.create_engine('test', config)

    assert isinstance(engine, RmqAsyncEngine)
    assert engine.name == 'test'

    resource = container.instance(container=container)
    assert isinstance(resource, RmqAsyncResource)

    container.unwire()


def test_single_async_container():
    container = SingleRmqAsyncContainer()

    container.config.from_dict({
        'name': 'test_single_async',
        'engine_config': {'dsn': RMQ_URI},
    })

    engine = container.create_engine()

    assert isinstance(engine, RmqAsyncEngine)
    assert engine.name == 'test_single_async'
    assert engine is container.create_engine()

    resource = container.instance(container=container)
    assert isinstance(resource, RmqAsyncResource)

    container.unwire()


def test_multiple_async_container():
    container = MultipleRmqAsyncContainer()

    container.config.from_dict({
        'one': {
            'engine_config': {'dsn': RMQ_URI},
        },
        'two': {
            'engine_config': {'dsn': RMQ_URI},
        },
    })

    assert container.create_engine('_') is None
    engine1 = container.create_engine('one')
    engine2 = container.create_engine('two')

    assert isinstance(engine1, RmqAsyncEngine)
    assert isinstance(engine2, RmqAsyncEngine)
    assert engine1 is not engine2
    assert engine1.name == 'one'
    assert engine2.name == 'two'

    resource = container.instance(container=container)
    assert isinstance(resource, RmqAsyncResource)

    container.unwire()
