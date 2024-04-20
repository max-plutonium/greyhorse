from typing import Any, Mapping

import aio_pika
import pytest
import pytest_asyncio

from greyhorse_rmq.config import EngineConf
from greyhorse_rmq.contexts import RmqAsyncContext
from greyhorse_rmq.factory import RmqAsyncEngineFactory
from greyhorse_rmq.rpc.client import AsyncRmqClient
from greyhorse_rmq.rpc.server import AsyncRmqServer
from .conf import RMQ_URI


class TestRmqServer(AsyncRmqServer):
    async def __call__(self, body: bytes, info: Mapping[str, Any]) -> bytes | None:
        return str(int(body) + 1).encode()


@pytest_asyncio.fixture(scope='function')
async def rmq_connection():
    factory = RmqAsyncEngineFactory()
    engine = factory.create_engine('test', EngineConf(dsn=RMQ_URI))

    await engine.start()

    async with engine.get_context(RmqAsyncContext) as ctx:
        yield ctx.connection

    await engine.stop()


@pytest.mark.asyncio
async def test_rpc(rmq_connection: aio_pika.RobustChannel):
    rpc_queue = await rmq_connection.declare_queue('rpc_queue', auto_delete=True)
    server = TestRmqServer(rpc_queue, rmq_connection.default_exchange)

    await server.start()

    client = await AsyncRmqClient(rmq_connection, 'rpc_queue').connect()
    assert '1' == (await client.send(str(0).encode())).decode()
    assert '0' == (await client.send(str(-1).encode())).decode()
    await client.disconnect()

    await server.stop()
