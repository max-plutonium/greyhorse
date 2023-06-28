import aio_pika
import pytest

from conf import RMQ_URI
from greyhorse_rmq.config import EngineConfig
from greyhorse_rmq.engine import RmqAsyncEngine
from greyhorse_rmq.factory import RmqAsyncEngineFactory


def test_async_factory():
    config = EngineConfig(dsn=RMQ_URI)

    factory = RmqAsyncEngineFactory()

    assert [] == factory.get_engine_names()
    assert factory.get_engine('test') is None
    assert {} == factory.get_engines()

    engine = factory('test', config)

    assert engine
    assert isinstance(engine, RmqAsyncEngine)
    assert ['test'] == factory.get_engine_names()
    assert factory.get_engine('test') is engine
    assert {'test': engine} == factory.get_engines()


@pytest.mark.asyncio
async def test_async_connection():
    config = EngineConfig(dsn=RMQ_URI)

    factory = RmqAsyncEngineFactory()
    engine = factory('test', config)

    await engine.start()

    async with engine.session() as conn:
        queue = await conn.declare_queue('test', auto_delete=True)
        await conn.default_exchange.publish(
            aio_pika.Message(body=b'12345'),
            routing_key='test',
        )
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:  # type: aio_pika.abc.AbstractIncomingMessage
                async with message.process():
                    assert message.body == b'12345'
                break

    await engine.stop()
