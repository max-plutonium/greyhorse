from greyhorse_sqla.config import EngineConfig, SqlEngineType
from greyhorse_sqla.containers import MultipleSqlaAsyncContainer, MultipleSqlaSyncContainer, SingleSqlaAsyncContainer, \
    SingleSqlaSyncContainer, SqlaAsyncContainer, SqlaSyncContainer
from greyhorse_sqla.engine import SqlaAsyncEngine, SqlaSyncEngine
from greyhorse_sqla.resources import SqlaAsyncResource, SqlaSyncResource
from .conf import SQLITE_URI


def test_base_sync_container():
    config = EngineConfig(
        dsn=SQLITE_URI,
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    container = SqlaSyncContainer()
    engine = container.create_engine('test', config, SqlEngineType.SQLITE)

    assert isinstance(engine, SqlaSyncEngine)
    assert engine.name == 'test'

    resource = container.instance(container=container)
    assert isinstance(resource, SqlaSyncResource)

    container.unwire()


def test_base_async_container():
    config = EngineConfig(
        dsn=SQLITE_URI,
        pool_min_size=1, pool_max_size=2,
        pool_expire_seconds=15, pool_timeout_seconds=15,
    )

    container = SqlaAsyncContainer()
    engine = container.create_engine('test', config, SqlEngineType.SQLITE)

    assert isinstance(engine, SqlaAsyncEngine)
    assert engine.name == 'test'

    resource = container.instance(container=container)
    assert isinstance(resource, SqlaAsyncResource)

    container.unwire()


def test_single_sync_container():
    container = SingleSqlaSyncContainer()

    container.config.from_dict({
        'name': 'test_single_sync',
        'db_type': SqlEngineType.SQLITE,
        'engine_config': {'dsn': SQLITE_URI},
    })

    engine = container.create_engine()

    assert isinstance(engine, SqlaSyncEngine)
    assert engine.name == 'test_single_sync'
    assert engine is container.create_engine()

    resource = container.instance(container=container)
    assert isinstance(resource, SqlaSyncResource)

    container.unwire()


def test_single_async_container():
    container = SingleSqlaAsyncContainer()

    container.config.from_dict({
        'name': 'test_single_async',
        'db_type': SqlEngineType.SQLITE,
        'engine_config': {'dsn': SQLITE_URI},
    })

    engine = container.create_engine()

    assert isinstance(engine, SqlaAsyncEngine)
    assert engine.name == 'test_single_async'
    assert engine is container.create_engine()

    resource = container.instance(container=container)
    assert isinstance(resource, SqlaAsyncResource)

    container.unwire()


def test_multiple_sync_container():
    container = MultipleSqlaSyncContainer()

    container.config.from_dict({
        'one': {
            'db_type': SqlEngineType.SQLITE,
            'engine_config': {'dsn': SQLITE_URI},
        },
        'two': {
            'db_type': SqlEngineType.SQLITE,
            'engine_config': {'dsn': SQLITE_URI},
        },
    })

    assert container.create_engine('_') is None
    engine1 = container.create_engine('one')
    engine2 = container.create_engine('two')

    assert isinstance(engine1, SqlaSyncEngine)
    assert isinstance(engine2, SqlaSyncEngine)
    assert engine1 is not engine2
    assert engine1.name == 'one'
    assert engine2.name == 'two'

    resource = container.instance(container=container)
    assert isinstance(resource, SqlaSyncResource)

    container.unwire()


def test_multiple_async_container():
    container = MultipleSqlaAsyncContainer()

    container.config.from_dict({
        'one': {
            'db_type': SqlEngineType.SQLITE,
            'engine_config': {'dsn': SQLITE_URI},
        },
        'two': {
            'db_type': SqlEngineType.SQLITE,
            'engine_config': {'dsn': SQLITE_URI},
        },
    })

    assert container.create_engine('_') is None
    engine1 = container.create_engine('one')
    engine2 = container.create_engine('two')

    assert isinstance(engine1, SqlaAsyncEngine)
    assert isinstance(engine2, SqlaAsyncEngine)
    assert engine1 is not engine2
    assert engine1.name == 'one'
    assert engine2.name == 'two'

    resource = container.instance(container=container)
    assert isinstance(resource, SqlaAsyncResource)

    container.unwire()
