import aio_pika
import pytest

from greyhorse.app.contexts import AsyncContext
from greyhorse_rmq.config import EngineConf
from greyhorse_rmq.contexts import RmqAsyncContext
from greyhorse_rmq.engine import RmqAsyncEngine
from greyhorse_rmq.factory import RmqAsyncEngineFactory
from .conf import RMQ_URI


def test_async_factory():
    config = EngineConf(dsn=RMQ_URI)

    factory = RmqAsyncEngineFactory()

    assert [] == factory.get_engine_names()
    assert factory.get_engine('test') is None
    assert {} == factory.get_engines()

    engine = factory.create_engine('test', config)

    assert engine
    assert engine.name == 'test'
    assert isinstance(engine, RmqAsyncEngine)
    assert ['test'] == factory.get_engine_names()
    assert factory.get_engine('test') is engine
    assert {'test': engine} == factory.get_engines()


@pytest.mark.asyncio
async def test_async_connection():
    config = EngineConf(dsn=RMQ_URI)

    factory = RmqAsyncEngineFactory()
    engine = factory.create_engine('test', config)

    assert not engine.active
    await engine.start()
    assert engine.active

    ctx = engine.get_context(RmqAsyncContext)
    assert ctx
    assert isinstance(ctx, AsyncContext)

    async with ctx as conn:
        queue = await conn.connection.declare_queue('test', auto_delete=True)
        await conn.connection.default_exchange.publish(
            aio_pika.Message(body=b'12345'),
            routing_key='test',
        )
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:  # type: aio_pika.abc.AbstractIncomingMessage
                async with message.process():
                    assert message.body == b'12345'
                break

    assert engine.active
    await engine.stop()
    assert not engine.active
