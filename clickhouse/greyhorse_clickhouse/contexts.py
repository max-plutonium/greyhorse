import asyncio
from contextlib import asynccontextmanager
from typing import Callable

from greyhorse_clickhouse.engine import AsyncChannel, CHAsyncEngine


class CHAsyncContext:
    def __init__(self, engine: CHAsyncEngine):
        self._engine = engine
        self._counter = 0
        self._lock = asyncio.Lock()
        self._session: AsyncChannel | None = None

    @property
    def name(self) -> str:
        return self._engine.name

    @property
    def engine(self) -> CHAsyncEngine:
        return self._engine

    @asynccontextmanager
    async def session_factory(self):
        yield self._session

    async def _setup(self):
        pass

    async def _teardown(self):
        pass

    async def __aenter__(self):
        async with self._lock:
            self._counter += 1
            if 1 != self._counter:
                return self

            self._cm = self._engine.session()
            self._session = await self._cm.__aenter__()
            await self._setup()
            return self

    async def __aexit__(self, *args):
        async with self._lock:
            self._counter = max(self._counter - 1, 0)
            if 0 != self._counter:
                return

            await self._teardown()

            try:
                await self._cm.__aexit__(*args)
            except Exception as _:
                pass

            self._cm = self._session = None
            await self._engine.teardown_session()


CHAsyncContextFactory = Callable[[CHAsyncEngine], CHAsyncContext]
