import asyncio
import sys
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager, AbstractContextManager, asynccontextmanager, AbstractAsyncContextManager
from datetime import timedelta
from typing import Callable

from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.ext.asyncio import AsyncSession as SqlaAsyncSession, async_scoped_session, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session as SqlaSyncSession, scoped_session, sessionmaker

from greyhorse_core.context import get_context
from greyhorse_core.engines.base import SyncEngine, AsyncEngine
from greyhorse_core.i18n import tr
from greyhorse_core.logging import logger
from greyhorse_sqla.config import SqlEngineType


class SqlaEngine(ABC):
    def __init__(self, raw_engine, db_type: SqlEngineType, timeout: timedelta):
        self._db_type = db_type
        self._timeout = timeout
        self._engine = raw_engine.execution_options(timeout=int(timeout.total_seconds()))
        self._force_rollback = False

    @property
    def raw_engine(self):
        return self._engine

    @property
    def db_type(self):
        return self._db_type

    @property
    def timeout(self) -> timedelta:
        return self._timeout

    @property
    @abstractmethod
    def connection_class(self):
        ...

    @contextmanager
    def with_force_rollback(self):
        self._force_rollback = True
        yield
        self._force_rollback = False


class SqlaSyncEngine(SyncEngine[SqlaSyncSession], SqlaEngine):
    def __init__(self, name: str, engine, db_type: SqlEngineType, timeout: timedelta):
        SyncEngine.__init__(self, name)
        SqlaEngine.__init__(self, engine, db_type, timeout)

        self._counter = 0
        self._lock = threading.Lock()
        self._session_factory = sessionmaker(bind=engine, autoflush=False)
        self._scoped_session = scoped_session(
            self._session_factory, scopefunc=lambda: get_context().session_id
        )

    @property
    def connection_class(self):
        return SqlaSyncSession

    @contextmanager
    def session(self, begin_tx: bool = True, force_rollback: bool = False) \
            -> AbstractContextManager[SqlaSyncSession]:
        if self._scoped_session.registry.has():
            yield self._scoped_session()
            return

        session: SqlaSyncSession = self._scoped_session()

        if begin_tx:
            with session.begin() as tx:
                yield session

                if sys.exc_info()[0] or self._force_rollback or force_rollback:
                    tx.rollback()
                else:
                    tx.commit()
        else:
            yield session

    def teardown_session(self):
        self._scoped_session.remove()

    def start(self):
        with self._lock:
            if 0 == self._counter:
                logger.info(tr('greyhorse.engines.sql.engine.started')
                            .format(name=self.name, db_type=self.db_type.value, async_='sync'))
            self._counter += 1

    def stop(self):
        with self._lock:
            if 1 == self._counter:
                self.raw_engine.dispose()
                logger.info(tr('greyhorse.engines.sql.engine.stopped')
                            .format(name=self.name, db_type=self.db_type.value, async_='sync'))
            self._counter = max(self._counter - 1, 0)


class SqlaAsyncEngine(AsyncEngine[SqlaAsyncSession], SqlaEngine):
    def __init__(self, name: str, engine, db_type: SqlEngineType, timeout: timedelta):
        AsyncEngine.__init__(self, name)
        SqlaEngine.__init__(self, engine, db_type, timeout)

        self._counter = 0
        self._lock = asyncio.Lock()
        self._session_factory = async_sessionmaker(
            bind=engine, autoflush=False, expire_on_commit=False,
        )
        self._scoped_session = async_scoped_session(
            self._session_factory, scopefunc=lambda: get_context().session_id
        )

    @property
    def connection_class(self):
        return SqlaAsyncSession

    @asynccontextmanager
    async def session(self, begin_tx: bool = True, force_rollback: bool = False) \
            -> AbstractAsyncContextManager[SqlaAsyncSession]:
        if self._scoped_session.registry.has():
            yield self._scoped_session()
            return

        session: SqlaAsyncSession = self._scoped_session()

        if begin_tx:
            async with session.begin() as tx:
                yield session

                if sys.exc_info()[0] or self._force_rollback or force_rollback:
                    await tx.rollback()
                else:
                    await tx.commit()
        else:
            yield session

    async def teardown_session(self):
        await self._scoped_session.remove()

    async def start(self):
        async with self._lock:
            if 0 == self._counter:
                logger.info(tr('greyhorse.engines.sql.engine.started')
                            .format(name=self.name, db_type=self.db_type.value, async_='async'))
            self._counter += 1

    async def stop(self):
        async with self._lock:
            if 1 == self._counter:
                await self.raw_engine.dispose()
                logger.info(tr('greyhorse.engines.sql.engine.stopped')
                            .format(name=self.name, db_type=self.db_type.value, async_='async'))
            self._counter = max(self._counter - 1, 0)
