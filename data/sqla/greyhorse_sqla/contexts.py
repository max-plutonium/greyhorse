from greyhorse.app.contexts import AsyncMutContext, SyncMutContext
from sqlalchemy.engine import Connection as SyncConnection
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.engine import AsyncConnection
from sqlalchemy.orm import Session as SyncSession

SqlaSyncConnCtx = SyncMutContext[SyncConnection]
SqlaSyncSessionCtx = SyncMutContext[SyncSession]

SqlaAsyncConnCtx = AsyncMutContext[AsyncConnection]
SqlaAsyncSessionCtx = AsyncMutContext[AsyncSession]
