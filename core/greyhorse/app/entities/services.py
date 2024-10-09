import asyncio
import threading
from typing import get_type_hints, override

from greyhorse.result import Ok, Result

from ..abc.providers import Provider
from ..abc.services import ProviderMember, Service, ServiceError, ServiceState, ServiceWaiter


def provider(provider_type: type[Provider]):
    def decorator(func: classmethod):
        hints = get_type_hints(func, include_extras=True)
        ret_type = hints.pop('return', None)
        func.__provider__ = ProviderMember(
            provider_type.__wrapped_type__,
            provider_type,
            method=func,
            params=hints,
            ret_type=ret_type,
        )
        return func

    return decorator


class SyncService(Service):
    def __init__(self) -> None:
        super().__init__()
        self._provided_providers: dict[type[Provider], Provider] = {}
        self._waiter = threading.Event()

    @override
    @property
    def waiter(self) -> ServiceWaiter:
        return ServiceWaiter.Sync(self._waiter)

    @override
    def setup(self, *args, **kwargs) -> Result[ServiceState, ServiceError]:
        if self.state == ServiceState.Active:
            return Ok(self.state)

        self._switch_to_active()
        return Ok(self.state)

    @override
    def teardown(self, *args, **kwargs) -> Result[ServiceState, ServiceError]:
        if self.state == ServiceState.Idle:
            return Ok(self.state)

        self._switch_to_idle()
        return Ok(self.state)

    @override
    def _switch_to_idle(self) -> None:
        self._state = ServiceState.Idle

    @override
    def _switch_to_active(self, started: bool = False) -> None:
        if started:
            self._waiter.clear()
        else:
            self._waiter.set()

        self._state = ServiceState.Active(started=not self._waiter.is_set())


class AsyncService(Service):
    def __init__(self) -> None:
        super().__init__()
        self._provided_providers: dict[type[Provider], Provider] = {}
        self._waiter = asyncio.Event()

    @override
    @property
    def waiter(self) -> ServiceWaiter:
        return ServiceWaiter.Async(self._waiter)

    @override
    async def setup(self, *args, **kwargs) -> Result[ServiceState, ServiceError]:
        if self.state == ServiceState.Active:
            return Ok(self.state)

        await self._switch_to_active()
        return Ok(self.state)

    @override
    async def teardown(self, *args, **kwargs) -> Result[ServiceState, ServiceError]:
        if self.state == ServiceState.Idle:
            return Ok(self.state)

        await self._switch_to_idle()
        return Ok(self.state)

    @override
    async def _switch_to_idle(self) -> None:
        self._state = ServiceState.Idle

    @override
    async def _switch_to_active(self, started: bool = False) -> None:
        if started:
            self._waiter.clear()
        else:
            self._waiter.set()

        self._state = ServiceState.Active(started=not self._waiter.is_set())
