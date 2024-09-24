from greyhorse.app.abc.providers import MutProvider
from greyhorse.app.contexts import AsyncMutContext, SyncMutContext
from sqlalchemy.engine import Connection as SyncConnection
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.engine import AsyncConnection
from sqlalchemy.orm import Session as SyncSession

SqlaSyncConnProvider = MutProvider[SyncMutContext[SyncConnection]]
SqlaSyncSessionProvider = MutProvider[SyncMutContext[SyncSession]]

SqlaAsyncConnProvider = MutProvider[AsyncMutContext[AsyncConnection]]
SqlaAsyncSessionProvider = MutProvider[AsyncMutContext[AsyncSession]]
