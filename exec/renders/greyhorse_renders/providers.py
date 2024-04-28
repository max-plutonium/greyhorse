from greyhorse.app.entities.providers import AsyncContextProvider, SyncContextProvider
from .abc import AsyncRenderFactory, SyncRenderFactory


class SyncRenderFactoryProvider(SyncContextProvider[SyncRenderFactory]):
    pass


class AsyncRenderFactoryProvider(AsyncContextProvider[AsyncRenderFactory]):
    pass
