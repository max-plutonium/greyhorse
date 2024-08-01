import asyncio
import threading
from abc import ABC
from typing import override

from greyhorse.result import Result, Ok
from ..abc.collectors import Collector, MutCollector
from ..abc.operators import Operator
from ..abc.providers import Provider
from ..abc.services import Service, ServiceWaiter, ServiceState, ServiceError


class SyncService(Service, ABC):
    def __init__(self, *args, **kwargs):
        super(SyncService, self).__init__(*args, **kwargs)
        self._waiter = threading.Event()

    @override
    @property
    def waiter(self) -> ServiceWaiter:
        return ServiceWaiter.Sync(self._waiter)

    @override
    def setup(
        self, providers: Collector[Provider], operators: Collector[Operator],
    ) -> Result[ServiceState, ServiceError]:
        ...

    @override
    def teardown(
        self, providers: MutCollector[Provider], operators: MutCollector[Operator],
    ) -> Result[ServiceState, ServiceError]:
        ...

    @override
    def _switch_to_active(self, started: bool = False) -> Result[ServiceState, ServiceError]:
        if started:
            self._waiter.clear()
        else:
            self._waiter.set()

        self._state = ServiceState.Active(started=not self._waiter.is_set())
        return Ok(self._state)


class AsyncService(Service, ABC):
    def __init__(self, *args, **kwargs):
        super(AsyncService, self).__init__(*args, **kwargs)
        self._waiter = asyncio.Event()

    @override
    @property
    def waiter(self) -> ServiceWaiter:
        return ServiceWaiter.Async(self._waiter)

    @override
    async def setup(
        self, providers: Collector[Provider], operators: Collector[Operator],
    ) -> Result[ServiceState, ServiceError]:
        ...

    @override
    async def teardown(
        self, providers: MutCollector[Provider], operators: MutCollector[Operator],
    ) -> Result[ServiceState, ServiceError]:
        ...

    @override
    def _switch_to_active(self, started: bool = False) -> Result[ServiceState, ServiceError]:
        if started:
            self._waiter.clear()
        else:
            self._waiter.set()

        self._state = ServiceState.Active(started=not self._waiter.is_set())
        return Ok(self._state)
