from dataclasses import dataclass

from sqlalchemy.engine import Connection as SyncConnection
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.engine import AsyncConnection
from sqlalchemy.orm import Session as SyncSession

from greyhorse.app.abc.providers import SharedProvider, MutProvider
from greyhorse.app.contexts import SyncContext, AsyncContext, SyncMutContext, AsyncMutContext
from .config import SqlEngineType


SqlaSyncConnProvider = MutProvider[SyncMutContext[SyncConnection]]
SqlaSyncSessionProvider = MutProvider[SyncMutContext[SyncSession]]

SqlaAsyncConnProvider = MutProvider[AsyncMutContext[AsyncConnection]]
SqlaAsyncSessionProvider = MutProvider[AsyncMutContext[AsyncSession]]



