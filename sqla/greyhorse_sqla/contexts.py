import asyncio
import threading
from contextlib import contextmanager, asynccontextmanager
from typing import Callable

from sqlalchemy import exc

from greyhorse_sqla.engine import SqlaSyncEngine, SqlaAsyncEngine


class SqlaSyncContext:
    def __init__(
        self, sqla_engine: SqlaSyncEngine, force_rollback: bool = True,
    ):
        self._sqla_engine = sqla_engine
        self._force_rollback = force_rollback
        self._counter = 0
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return self._sqla_engine.name

    @contextmanager
    def session_factory(self):
        yield self.session

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

    def setup(self):
        pass

    def teardown(self):
        pass

    def __enter__(self):
        with self._lock:
            self._counter += 1
            if 1 != self._counter:
                return self

            self._cm = self._sqla_engine.session(force_rollback=self._force_rollback)
            self.session = self._cm.__enter__()
            self.setup()
            return self

    def __exit__(self, *args):
        with self._lock:
            self._counter = max(self._counter - 1, 0)
            if 0 != self._counter:
                self.session.flush()
                return

            self.teardown()

            try:
                self._cm.__exit__(*args)
            except exc.ResourceClosedError:
                pass

            self._cm = self.session = None
            self._sqla_engine.teardown_session()


class SqlaAsyncContext:
    def __init__(
        self, sqla_engine: SqlaAsyncEngine, force_rollback: bool = True,
    ):
        self._sqla_engine = sqla_engine
        self._force_rollback = force_rollback
        self._counter = 0
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        return self._sqla_engine.name

    @asynccontextmanager
    async def session_factory(self):
        yield self.session

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()

    async def setup(self):
        pass

    async def teardown(self):
        pass

    async def __aenter__(self):
        async with self._lock:
            self._counter += 1
            if 1 != self._counter:
                return self

            self._cm = self._sqla_engine.session(force_rollback=self._force_rollback)
            self.session = await self._cm.__aenter__()
            await self.setup()
            return self

    async def __aexit__(self, *args):
        async with self._lock:
            self._counter = max(self._counter - 1, 0)
            if 0 != self._counter:
                await self.session.flush()
                return

            await self.teardown()

            try:
                await self._cm.__aexit__(*args)
            except exc.ResourceClosedError:
                pass

            self._cm = self.session = None
            await self._sqla_engine.teardown_session()


SqlaSyncContextFactory = Callable[[SqlaSyncEngine, bool], SqlaSyncContext]
SqlaAsyncContextFactory = Callable[[SqlaAsyncEngine, bool], SqlaAsyncContext]
