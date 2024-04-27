from greyhorse.app.entities.providers import SyncContextProvider, AsyncContextProvider
from .abc import SyncConnection, SyncSession, AsyncConnection, AsyncSession


class SyncConnectionProvider(SyncContextProvider[SyncConnection]):
    pass


class SyncSessionProvider(SyncContextProvider[SyncSession]):
    pass


class AsyncConnectionProvider(AsyncContextProvider[AsyncConnection]):
    pass


class AsyncSessionProvider(AsyncContextProvider[AsyncSession]):
    pass


