import asyncio
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import get_type_hints, override

from greyhorse.result import Ok, Result
from greyhorse.utils.types import unwrap_maybe, unwrap_optional

from ..abc.providers import Provider
from ..abc.resources import Lifetime
from ..abc.services import Service, ServiceError, ServiceState, ServiceWaiter


@dataclass(slots=True, frozen=True)
class ResourceMember:
    resource_type: type
    lifetime: Lifetime
    cache: bool
    method: classmethod
    params: dict[str, type] = field(default_factory=dict)


def provide(lifetime: Lifetime, cache: bool = True) -> Callable[[classmethod], classmethod]:
    def decorator(func: classmethod) -> classmethod:
        hints = get_type_hints(func, include_extras=True)
        resource_type = hints.pop('return')

        func.__res_provider__ = ResourceMember(
            unwrap_maybe(unwrap_optional(resource_type)),
            lifetime=lifetime,
            cache=cache,
            method=func,
            params=hints,
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
    def setup(self, *args, **kwargs) -> Result[ServiceState, ServiceError]:  # noqa: ANN002,ANN003
        if self.state == ServiceState.Active:
            return Ok(self.state)

        self._switch_to_active()
        return Ok(self.state)

    @override
    def teardown(self, *args, **kwargs) -> Result[ServiceState, ServiceError]:  # noqa: ANN002,ANN003
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
    async def setup(self, *args, **kwargs) -> Result[ServiceState, ServiceError]:  # noqa: ANN002,ANN003
        if self.state == ServiceState.Active:
            return Ok(self.state)

        await self._switch_to_active()
        return Ok(self.state)

    @override
    async def teardown(self, *args, **kwargs) -> Result[ServiceState, ServiceError]:  # noqa: ANN002,ANN003
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
