import asyncio
import threading
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from functools import partial
from typing import Any, override

from greyhorse.app.abc.providers import BorrowMutError, Provider
from greyhorse.app.contexts import AsyncMutContext, ContextBuilder, current_scope_id
from greyhorse.app.registries import MutDictRegistry, ScopedMutDictRegistry
from greyhorse.data.storage import DataStorageEngine
from greyhorse.i18n import tr
from greyhorse.logging import logger
from greyhorse.maybe import Maybe
from greyhorse.result import Ok, Result
from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session, async_sessionmaker
from sqlalchemy.ext.asyncio.engine import AsyncConnection, AsyncEngine, AsyncTransaction

from .config import EngineConf
from .providers import SqlaAsyncConnProvider, SqlaAsyncSessionProvider


class _AsyncConnCtx(AsyncMutContext[AsyncConnection]):
    __slots__ = ('_root_tx', '_tx_stack')

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._root_tx: AsyncTransaction | None = None
        self._tx_stack: list[AsyncTransaction] = []

    @override
    async def _enter(self, instance: AsyncConnection) -> None:
        assert self._root_tx is None
        assert not self._tx_stack
        self._root_tx = instance.begin()
        await self._root_tx.__aenter__()

    @override
    async def _exit(self, instance: AsyncConnection, exc_type, exc_value, traceback) -> None:
        assert self._root_tx is not None
        assert not self._tx_stack
        await super()._exit(instance, exc_type, exc_value, traceback)
        await self._root_tx.__aexit__(exc_type, exc_value, traceback)
        await self._root_tx.close()
        self._root_tx = None

    @override
    async def _nested_enter(self, instance: AsyncConnection) -> None:
        nested = instance.begin_nested()
        self._tx_stack.append(nested)
        await nested.__aenter__()

    @override
    async def _nested_exit(
        self, instance: AsyncConnection, exc_type, exc_value, traceback
    ) -> None:
        nested = self._tx_stack.pop()
        await nested.__aexit__(exc_type, exc_value, traceback)
        await nested.close()

    @override
    async def _apply(self, instance: AsyncConnection) -> None:
        tx = self._tx_stack[-1] if self._tx_stack else self._root_tx
        await tx.commit()

    @override
    async def _cancel(self, instance: AsyncConnection) -> None:
        tx = self._tx_stack[-1] if self._tx_stack else self._root_tx
        await tx.rollback()


class _AsyncSessionCtx(AsyncMutContext[AsyncSession]):
    @override
    async def _apply(self, instance: AsyncSession) -> None:
        await instance.commit()

    @override
    async def _cancel(self, instance: AsyncSession) -> None:
        await instance.rollback()


class _ConnProvider(SqlaAsyncConnProvider):
    __slots__ = ('_builder',)

    def __init__(self, builder: ContextBuilder[_AsyncConnCtx, AsyncConnection]) -> None:
        self._builder = builder

    @override
    def acquire(self) -> Result[AsyncMutContext[AsyncConnection], BorrowMutError]:
        return Ok(self._builder.build())

    @override
    def release(self, instance: AsyncMutContext[AsyncConnection]) -> None:
        del instance


class _SessionProvider(SqlaAsyncSessionProvider):
    __slots__ = ('_builder',)

    def __init__(self, builder: ContextBuilder[_AsyncSessionCtx, AsyncSession]) -> None:
        self._builder = builder

    @override
    def acquire(self) -> Result[AsyncMutContext[AsyncSession], BorrowMutError]:
        return Ok(self._builder.build())

    @override
    def release(self, instance: AsyncMutContext[AsyncSession]) -> None:
        del instance


class AsyncSqlaEngine(DataStorageEngine):
    def __init__(self, name: str, config: EngineConf, engine: AsyncEngine) -> None:
        super().__init__(name)
        self._config = config
        self._counter = 0
        self._lock = asyncio.Lock()
        self._engine = engine

        self._registry = ScopedMutDictRegistry[type, Any](
            factory=MutDictRegistry, scope_func=lambda: str(threading.current_thread().ident)
        )

        self._conn_builder = ContextBuilder[_AsyncConnCtx, AsyncConnection](
            lambda conn: conn,
            force_rollback=config.force_rollback,
            auto_apply=config.auto_apply,
        )
        self._conn_builder.add_param('conn', self._get_connection)

        self._session_builder = ContextBuilder[_AsyncSessionCtx, AsyncSession](
            lambda session: session,
            force_rollback=config.force_rollback,
            auto_apply=config.auto_apply,
        )
        self._session_builder.add_param('session', self._get_session)

        self._providers = MutDictRegistry[type[Provider], Callable[[], Provider]]()

    @property
    def active(self) -> bool:
        return self._counter > 0

    @override
    def get_provider[P: Provider](self, prov_type: type[P]) -> Maybe[P]:
        return self._providers.get(prov_type).map(lambda func: func())

    @override
    async def start(self) -> None:
        async with self._lock:
            if self._counter == 0:
                self._providers.add(
                    SqlaAsyncConnProvider, partial(_ConnProvider, self._conn_builder)
                )
                self._providers.add(
                    SqlaAsyncSessionProvider, partial(_SessionProvider, self._session_builder)
                )
                logger.info(
                    tr(
                        'greyhorse.engines.sqla.engine.started',
                        name=self.name,
                        db_type=self._config.type.value,
                        async_='async',
                    )
                )
            self._counter += 1

    @override
    async def stop(self) -> None:
        async with self._lock:
            if self._counter == 1:
                self._providers.remove(SqlaAsyncConnProvider)
                self._providers.remove(SqlaAsyncSessionProvider)
                await self._engine.dispose()
                logger.info(
                    tr(
                        'greyhorse.engines.sqla.engine.stopped',
                        name=self.name,
                        db_type=self._config.type.value,
                        async_='async',
                    )
                )
            self._counter = max(self._counter - 1, 0)

    @asynccontextmanager
    async def _get_connection(self) -> AbstractAsyncContextManager[AsyncConnection]:
        if instance := self._registry.get(AsyncConnection).unwrap_or_none():
            yield instance
            return

        async with self._engine.connect() as instance:
            self._registry.add(AsyncConnection, instance)

            session_maker = async_scoped_session(
                async_sessionmaker(
                    bind=instance,
                    autoflush=False,
                    expire_on_commit=False,
                    join_transaction_mode='create_savepoint',
                ),
                scopefunc=lambda: current_scope_id(AsyncSession),
            )
            self._registry.add(AsyncSession, session_maker)

            yield instance

            self._registry.remove(AsyncSession)
            self._registry.remove(AsyncConnection)

    @asynccontextmanager
    async def _get_session(self) -> AbstractAsyncContextManager[AsyncSession]:
        async with self._get_connection():
            session_maker = self._registry.get(AsyncSession).unwrap()  # type: async_scoped_session
            if session_maker.registry.has():
                session = session_maker()
                yield session
                return

            async with session_maker() as session:
                yield session

            session_maker.registry.clear()
