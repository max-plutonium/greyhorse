import asyncio

import pytest

from greyhorse_core.context import get_context


@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


# @pytest.fixture(scope='session', autouse=True)
# def testcontext():
#     get_context().session_id = 'tests'
