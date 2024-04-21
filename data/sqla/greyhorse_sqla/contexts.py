from dataclasses import dataclass

from sqlalchemy.engine import Connection as SyncConnection
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.engine import AsyncConnection
from sqlalchemy.orm import Session as SyncSession

from greyhorse.app.entities.providers import AsyncContextProvider, SyncContextProvider
from .config import SqlEngineType


@dataclass(slots=True, frozen=True)
class SqlaSyncContext:
    name: str
    type: SqlEngineType
    connection: SyncConnection


@dataclass(slots=True, frozen=True)
class SqlaSyncSessionContext:
    name: str
    type: SqlEngineType
    session: SyncSession


@dataclass(slots=True, frozen=True)
class SqlaAsyncContext:
    name: str
    type: SqlEngineType
    connection: AsyncConnection


@dataclass(slots=True, frozen=True)
class SqlaAsyncSessionContext:
    name: str
    type: SqlEngineType
    session: AsyncSession


class SqlaSyncContextProvider(SyncContextProvider[SqlaSyncContext]):
    pass


class SqlaSyncSessionProvider(SyncContextProvider[SqlaSyncSessionContext]):
    pass


class SqlaAsyncContextProvider(AsyncContextProvider[SqlaAsyncContext]):
    pass


class SqlaAsyncSessionProvider(AsyncContextProvider[SqlaAsyncSessionContext]):
    pass
