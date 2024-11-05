import threading
from contextlib import AbstractContextManager, contextmanager
from types import TracebackType
from typing import Any, override

from greyhorse.app.contexts import Context, ContextBuilder, SyncMutContext, current_scope_id
from greyhorse.app.registries import MutDictRegistry, ScopedMutDictRegistry
from greyhorse.data.storage import Engine
from greyhorse.i18n import tr
from greyhorse.logging import logger
from greyhorse.maybe import Just, Maybe, Nothing
from sqlalchemy.engine import Connection as SyncConnection
from sqlalchemy.engine import Engine as SyncEngine
from sqlalchemy.engine.base import NestedTransaction, RootTransaction
from sqlalchemy.orm import Session as SyncSession
from sqlalchemy.orm import scoped_session, sessionmaker

from .config import EngineConf


class _SyncConnCtx(SyncMutContext[SyncConnection]):
    __slots__ = ('_root_tx', '_tx_stack')

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002,ANN003
        super().__init__(*args, **kwargs)
        self._root_tx: RootTransaction | None = None
        self._tx_stack: list[NestedTransaction] = []

    @override
    def _enter(self, instance: SyncConnection) -> None:
        assert self._root_tx is None
        assert not self._tx_stack
        self._root_tx = instance.begin()
        self._root_tx.__enter__()

    @override
    def _exit(
        self,
        instance: SyncConnection,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        assert self._root_tx is not None
        assert not self._tx_stack
        super()._exit(instance, exc_type, exc_value, traceback)
        self._root_tx.__exit__(exc_type, exc_value, traceback)
        self._root_tx.close()
        self._root_tx = None

    @override
    def _nested_enter(self, instance: SyncConnection) -> None:
        nested = instance.begin_nested()
        self._tx_stack.append(nested)
        nested.__enter__()

    @override
    def _nested_exit(
        self,
        instance: SyncConnection,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        nested = self._tx_stack.pop()
        nested.__exit__(exc_type, exc_value, traceback)
        nested.close()

    @override
    def _apply(self, instance: SyncConnection) -> None:
        tx = self._tx_stack[-1] if self._tx_stack else self._root_tx
        tx.commit()

    @override
    def _cancel(self, instance: SyncConnection) -> None:
        tx = self._tx_stack[-1] if self._tx_stack else self._root_tx
        tx.rollback()


class _SyncSessionCtx(SyncMutContext[SyncSession]):
    @override
    def _apply(self, instance: SyncSession) -> None:
        instance.commit()

    @override
    def _cancel(self, instance: SyncSession) -> None:
        instance.rollback()


class SyncSqlaEngine(Engine):
    def __init__(self, name: str, config: EngineConf, engine: SyncEngine) -> None:
        super().__init__(name)
        self._config = config
        self._counter = 0
        self._lock = threading.Lock()
        self._engine = engine

        self._registry = ScopedMutDictRegistry[type, Any](
            factory=MutDictRegistry, scope_func=lambda: str(threading.current_thread().ident)
        )

        self._conn_builder = ContextBuilder[_SyncConnCtx, SyncConnection](
            lambda conn: conn,
            force_rollback=config.force_rollback,
            auto_apply=config.auto_apply,
        )
        self._conn_builder.add_param('conn', self._get_connection)

        self._session_builder = ContextBuilder[_SyncSessionCtx, SyncSession](
            lambda session: session,
            force_rollback=config.force_rollback,
            auto_apply=config.auto_apply,
        )
        self._session_builder.add_param('session', self._get_session)

    @property
    def active(self) -> bool:
        return self._counter > 0

    @override
    def get_context[T: Context](self, kind: type[T]) -> Maybe[T]:
        if kind is SyncMutContext[SyncConnection]:
            return Just(self._conn_builder.build())
        if kind is SyncMutContext[SyncSession]:
            return Just(self._session_builder.build())
        return Nothing

    @override
    def start(self) -> None:
        with self._lock:
            if self._counter == 0:
                logger.info(
                    tr(
                        'greyhorse.engines.sqla.engine.started',
                        name=self.name,
                        db_type=self._config.type.value,
                        async_='sync',
                    )
                )
            self._counter += 1

    @override
    def stop(self) -> None:
        with self._lock:
            if self._counter == 1:
                self._engine.dispose()
                logger.info(
                    tr(
                        'greyhorse.engines.sqla.engine.stopped',
                        name=self.name,
                        db_type=self._config.type.value,
                        async_='sync',
                    )
                )
            self._counter = max(self._counter - 1, 0)

    @contextmanager
    def _get_connection(self) -> AbstractContextManager[SyncConnection]:
        if instance := self._registry.get(SyncConnection).unwrap_or_none():
            yield instance
            return

        with self._engine.connect() as instance:
            self._registry.add(SyncConnection, instance)

            session_maker = scoped_session(
                sessionmaker(
                    bind=instance,
                    autoflush=False,
                    expire_on_commit=False,
                    join_transaction_mode='create_savepoint',
                ),
                scopefunc=lambda: current_scope_id(SyncSession),
            )
            self._registry.add(SyncSession, session_maker)

            yield instance

            self._registry.remove(SyncSession)
            self._registry.remove(SyncConnection)

    @contextmanager
    def _get_session(self) -> AbstractContextManager[SyncSession]:
        with self._get_connection():
            session_maker = self._registry.get(SyncSession).unwrap()  # type: scoped_session
            if session_maker.registry.has():
                session = session_maker()
                yield session
                return

            with session_maker() as session:
                yield session

            session_maker.registry.clear()
