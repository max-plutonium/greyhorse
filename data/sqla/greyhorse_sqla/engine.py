import asyncio
import sys
import threading
from contextlib import AbstractAsyncContextManager, AbstractContextManager, asynccontextmanager, contextmanager
from typing import Any, override

from sqlalchemy.engine import Connection as SyncConnection, Engine as SyncEngine
from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session, async_sessionmaker
from sqlalchemy.ext.asyncio.engine import AsyncConnection, AsyncEngine
from sqlalchemy.orm import Session as SyncSession, scoped_session, sessionmaker

from greyhorse.app.context import AsyncContextBuilder, Context, SyncContextBuilder, current_scope_id
from greyhorse.app.utils.registry import DictRegistry, ScopedRegistry
from greyhorse.data.storage import DataStorageEngine
from greyhorse.i18n import tr
from greyhorse.logging import logger
from .config import EngineConf
from .contexts import SqlaAsyncContext, SqlaAsyncSessionContext, SqlaSyncContext, SqlaSyncSessionContext

type SyncChannel = SyncSession
type AsyncChannel = AsyncSession


class SqlaSyncEngine(DataStorageEngine):
    def __init__(self, name: str, config: EngineConf, engine: SyncEngine):
        super().__init__(name)
        self._config = config
        self._counter = 0
        self._lock = threading.Lock()
        self._engine = engine

        self._registry = ScopedRegistry[type, Any](
            factory=lambda: DictRegistry(),
            scope_func=lambda: str(threading.current_thread().ident),
        )

    @property
    def active(self) -> bool:
        return self._counter > 0

    @override
    def start(self):
        with self._lock:
            if 0 == self._counter:
                logger.info(
                    tr('greyhorse.engines.sqla.engine.started')
                    .format(name=self.name, db_type=self._config.type.value, async_='sync')
                )
            self._counter += 1

    @override
    def stop(self):
        with self._lock:
            if 1 == self._counter:
                self._engine.dispose()
                logger.info(
                    tr('greyhorse.engines.sqla.engine.stopped')
                    .format(name=self.name, db_type=self._config.type.value, async_='sync')
                )
            self._counter = max(self._counter - 1, 0)

    @contextmanager
    def connection(self) -> AbstractContextManager[SyncConnection]:
        if instance := self._registry.get(SyncConnection):
            yield instance
            return

        with self._engine.connect() as instance:
            session_maker = scoped_session(
                sessionmaker(
                    bind=instance, autoflush=False, expire_on_commit=False,
                    join_transaction_mode='create_savepoint',
                ),
                scopefunc=lambda: current_scope_id(SqlaSyncContext),
            )
            self._registry.set(scoped_session, session_maker)

            if self._config.begin_tx:
                with instance.begin() as tx:
                    self._registry.set(SyncConnection, instance)
                    yield instance
                    self._registry.reset(SyncConnection)
                    self._registry.reset(scoped_session)

                    if sys.exc_info()[0] or self._config.force_rollback:
                        tx.rollback()
                    else:
                        tx.commit()
            else:
                self._registry.set(SyncConnection, instance)
                yield instance
                self._registry.reset(SyncConnection)
                self._registry.reset(scoped_session)

    @contextmanager
    def session(self) -> AbstractContextManager[SyncChannel]:
        with self.connection():
            factory = self._registry.get(scoped_session)
            if factory.registry.has():
                yield factory()
                return

            session: SyncSession = factory()

            try:
                if self._config.begin_tx:
                    with session.begin() as tx:
                        yield session

                        if sys.exc_info()[0] or self._config.force_rollback:
                            tx.rollback()
                        else:
                            tx.commit()
                else:
                    yield session

            finally:
                session.close()
                factory.registry.clear()

    @override
    def get_context[T: Context](self, kind: type[Context]) -> T | None:
        if kind is SqlaSyncContext:
            builder = SyncContextBuilder[SqlaSyncContext](kind)
            builder.add_param('name', self.name)
            builder.add_param('type', self._config.type)
            builder.add_param('connection', self.connection)
            return builder.build()
        elif kind is SqlaSyncSessionContext:
            builder = SyncContextBuilder[SqlaSyncSessionContext](kind)
            builder.add_param('name', self.name)
            builder.add_param('type', self._config.type)
            builder.add_param('session', self.session)
            return builder.build()
        else:
            return None


class SqlaAsyncEngine(DataStorageEngine):
    def __init__(self, name: str, config: EngineConf, engine: AsyncEngine):
        super().__init__(name)
        self._config = config
        self._counter = 0
        self._lock = asyncio.Lock()
        self._engine = engine

        self._registry = ScopedRegistry[type, Any](
            factory=lambda: DictRegistry(),
            scope_func=lambda: str(id(asyncio.current_task())),
        )

    @property
    def active(self) -> bool:
        return self._counter > 0

    @override
    async def start(self):
        async with self._lock:
            if 0 == self._counter:
                logger.info(
                    tr('greyhorse.engines.sqla.engine.started')
                    .format(name=self.name, db_type=self._config.type.value, async_='async')
                )
            self._counter += 1

    @override
    async def stop(self):
        async with self._lock:
            if 1 == self._counter:
                await self._engine.dispose()
                logger.info(
                    tr('greyhorse.engines.sqla.engine.stopped')
                    .format(name=self.name, db_type=self._config.type.value, async_='async')
                )
            self._counter = max(self._counter - 1, 0)

    @asynccontextmanager
    async def connection(self) -> AbstractAsyncContextManager[AsyncConnection]:
        if instance := self._registry.get(AsyncConnection):
            yield instance
            return

        async with self._engine.connect() as instance:
            session_maker = async_scoped_session(
                async_sessionmaker(
                    bind=instance, autoflush=False, expire_on_commit=False,
                    join_transaction_mode='create_savepoint',
                ),
                scopefunc=lambda: current_scope_id(SqlaAsyncContext),
            )
            self._registry.set(async_scoped_session, session_maker)

            if self._config.begin_tx:
                async with instance.begin() as tx:
                    self._registry.set(AsyncConnection, instance)
                    yield instance
                    self._registry.reset(AsyncConnection)
                    self._registry.reset(async_scoped_session)

                    if sys.exc_info()[0] or self._config.force_rollback:
                        await tx.rollback()
                    else:
                        await tx.commit()
            else:
                self._registry.set(AsyncConnection, instance)
                yield instance
                self._registry.reset(AsyncConnection)
                self._registry.reset(async_scoped_session)

    @asynccontextmanager
    async def session(self) -> AbstractAsyncContextManager[AsyncChannel]:
        async with self.connection():
            factory = self._registry.get(async_scoped_session)
            if factory.registry.has():
                yield factory()
                return

            session: AsyncSession = factory()

            try:
                if self._config.begin_tx:
                    async with session.begin() as tx:
                        yield session

                        if sys.exc_info()[0] or self._config.force_rollback:
                            await tx.rollback()
                        else:
                            await tx.commit()
                else:
                    yield session

            finally:
                await session.close()
                factory.registry.clear()

    @override
    def get_context[T: Context](self, kind: type[Context]) -> T | None:
        if kind is SqlaAsyncContext:
            builder = AsyncContextBuilder[SqlaAsyncContext](kind)
            builder.add_param('name', self.name)
            builder.add_param('type', self._config.type)
            builder.add_param('connection', self.connection)
            return builder.build()
        elif kind is SqlaAsyncSessionContext:
            builder = AsyncContextBuilder[SqlaAsyncSessionContext](kind)
            builder.add_param('name', self.name)
            builder.add_param('type', self._config.type)
            builder.add_param('session', self.session)
            return builder.build()
        else:
            return None
