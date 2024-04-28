import threading
from abc import ABC, abstractmethod

from greyhorse.app.context import SyncContext
from greyhorse.app.entities.module import Module
from greyhorse.app.entities.providers import SyncContextProvider
from greyhorse.app.entities.service import Service
from greyhorse.app.schemas.module import ModuleConf, ModuleDesc, ServiceConf
from greyhorse.app.schemas.service import ProviderMappingPolicy
from greyhorse.result import F


class Service1(Service):
    def __init__(self, name: str):
        super().__init__(name)
        self._event = threading.Event()

        self._provider_factories.set(
            Provider1, lambda: Provider1(self._ctx1), name='name1',
        )

        self._provider_factories.set(
            Provider1, lambda: Provider1(self._ctx2), name='name2',
        )

        self._ctx1 = SyncContext[dict](lambda: {'a': 123})
        self._ctx2 = SyncContext[dict](lambda: {'a': 456})

    @property
    def active(self) -> bool:
        return False

    async def start(self):
        self._event.clear()

    async def stop(self):
        self._event.set()

    def wait(self) -> threading.Event:
        return self._event


class Provider1(SyncContextProvider[dict]):
    pass


class Operator1(ABC):
    @abstractmethod
    def summ(self, a: int, b: int) -> int:
        ...


class Module1(Module):
    def start(self):
        super().start()


def __init__(id: int, data: str) -> ModuleConf:
    return ModuleConf(
        name='app',
        factory=Module1,
        submodules=[
            ModuleDesc(
                path='.module1.main', args={'id': 456, 'data': 'test1'},
            )
        ],
        services=[
            ServiceConf(
                key=Service1, name='service1',
                provider_mapping=[
                    ProviderMappingPolicy(key=Provider1, name_pattern=r'\D+1$'),
                ],
            ),
            ServiceConf(
                key=Service1, name='service2',
                provider_mapping=[
                    ProviderMappingPolicy(key=Provider1, name_pattern=r'\D+2$'),
                ],
            ),
        ],
        service_factories={Service1: F(Service1)},
    )


def __fini__():
    pass
