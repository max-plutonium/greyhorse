import asyncio
from typing import Any, Mapping

import pytest
import pytest_asyncio

from conf import RMQ_URI
from greyhorse_rmq.config import EngineConfig
from greyhorse_rmq.factory import RmqAsyncEngineFactory
from greyhorse_rmq.rpc.client import AsyncRmqClient
from greyhorse_rmq.rpc.server import AsyncRmqServer


class TestRmqServer(AsyncRmqServer):
    async def __call__(self, body: bytes, info: Mapping[str, Any]) -> bytes | None:
        return str(int(body) + 1).encode()


@pytest_asyncio.fixture(scope='function')
async def rmq_session():
    factory = RmqAsyncEngineFactory()
    engine = factory('test', EngineConfig(dsn=RMQ_URI))

    await engine.start()
    async with engine.session() as channel:
        yield channel
    await engine.stop()


@pytest.mark.asyncio
async def test_rpc(event_loop, rmq_session):
    rpc_queue = await rmq_session.declare_queue('rpc_queue', auto_delete=True)
    server = TestRmqServer(rpc_queue, rmq_session.default_exchange)
    asyncio.get_event_loop().create_task(server.run())

    client = await AsyncRmqClient(rmq_session, 'rpc_queue').connect()
    assert '1' == (await client.send(str(0).encode())).decode()
    assert '0' == (await client.send(str(-1).encode())).decode()
    await client.disconnect()
    await server.stop()
