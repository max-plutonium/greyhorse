import asyncio
import threading
from contextlib import asynccontextmanager, contextmanager
from typing import Callable

from sqlalchemy import exc
from sqlalchemy.ext.asyncio import AsyncSession as SqlaAsyncSession
from sqlalchemy.orm import Session as SqlaSyncSession

from greyhorse_sqla.engine import SqlaAsyncEngine, SqlaSyncEngine


class SqlaSyncContext:
    def __init__(self, engine: SqlaSyncEngine, force_rollback: bool = True):
        self._engine = engine
        self._force_rollback = force_rollback
        self._counter = 0
        self._lock = threading.Lock()
        self._session: SqlaSyncSession | None = None

    @property
    def name(self) -> str:
        return self._engine.name

    @property
    def engine(self) -> SqlaSyncEngine:
        return self._engine

    @contextmanager
    def session_factory(self):
        yield self._session

    def commit(self):
        self._session.commit()

    def rollback(self):
        self._session.rollback()

    def _setup(self):
        pass

    def _teardown(self):
        pass

    def __enter__(self):
        with self._lock:
            self._counter += 1
            if 1 != self._counter:
                return self

            self._cm = self._engine.session(force_rollback=self._force_rollback)
            self._session = self._cm.__enter__()
            self._setup()
            return self

    def __exit__(self, *args):
        with self._lock:
            self._counter = max(self._counter - 1, 0)
            if 0 != self._counter:
                self._session.flush()
                return

            self._teardown()

            try:
                self._cm.__exit__(*args)
            except exc.ResourceClosedError:
                pass

            self._cm = self._session = None
            self._engine.teardown_session()


class SqlaAsyncContext:
    def __init__(self, engine: SqlaAsyncEngine, force_rollback: bool = True):
        self._engine = engine
        self._force_rollback = force_rollback
        self._counter = 0
        self._lock = asyncio.Lock()
        self._session: SqlaAsyncSession | None = None

    @property
    def name(self) -> str:
        return self._engine.name

    @property
    def engine(self) -> SqlaAsyncEngine:
        return self._engine

    @asynccontextmanager
    async def session_factory(self):
        yield self._session

    async def commit(self):
        await self._session.commit()

    async def rollback(self):
        await self._session.rollback()

    async def _setup(self):
        pass

    async def _teardown(self):
        pass

    async def __aenter__(self):
        async with self._lock:
            self._counter += 1
            if 1 != self._counter:
                return self

            self._cm = self._engine.session(force_rollback=self._force_rollback)
            self._session = await self._cm.__aenter__()
            await self._setup()
            return self

    async def __aexit__(self, *args):
        async with self._lock:
            self._counter = max(self._counter - 1, 0)
            if 0 != self._counter:
                await self._session.flush()
                return

            await self._teardown()

            try:
                await self._cm.__aexit__(*args)
            except exc.ResourceClosedError:
                pass

            self._cm = self._session = None
            await self._engine.teardown_session()


SqlaSyncContextFactory = Callable[[SqlaSyncEngine, bool], SqlaSyncContext]
SqlaAsyncContextFactory = Callable[[SqlaAsyncEngine, bool], SqlaAsyncContext]
