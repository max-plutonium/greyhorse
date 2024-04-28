from typing import cast

from greyhorse.app.entities.controller import Controller
from greyhorse.app.entities.module import Module
from greyhorse.app.entities.providers import SyncContextProvider
from greyhorse.app.entities.service import AsyncService
from greyhorse.app.schemas.components import OperatorPolicy, ProviderPolicy
from greyhorse.app.schemas.controller import OperatorMappingPolicy
from greyhorse.app.schemas.module import ControllerConf, ModuleConf, OperatorExport, ProviderClaim, ServiceConf
from greyhorse.result import F
from ..main import Operator1, Provider1


class Provider2(SyncContextProvider[int]):
    pass


class Service2(AsyncService):
    async def start(self):
        if of := self.get_operator_factory(Operator1, 'name1'):
            res = of()
            op = cast(Operator1, res)
            r = op.summ(100, 200)

        return await super().start()


class Controller2(Controller):
    def __init__(self, id: int, data: str, name: str):
        super().__init__(name)
        self._id = id
        self._data = data

        self._op_factories.set(
            Operator2, Operator2, name='name1',
        )

        self._op_factories.set(
            Operator2, Operator2, name='name2',
        )

    @property
    def active(self) -> bool:
        return False

    async def start(self):
        if of := self.get_provider_factory(Provider1, 'name1'):
            res = of()
            prov = cast(Provider1, res)
            r = prov.get()
        pass

    async def stop(self):
        pass


class Operator2(Operator1):
    def summ(self, a: int, b: int) -> int:
        return a + b


class Module2(Module):
    def start(self):
        super().start()

    def stop(self):
        super().stop()


def __init__(id: int, data: str) -> ModuleConf:
    return ModuleConf(
        name='module1',
        factory=Module2,
        provider_claims=[
            ProviderClaim(key=Provider1, name_pattern=r'\D+1$'),
            ProviderClaim(key=Provider1, name_pattern=r'\D+2$'),
        ],
        operator_exports=[
            OperatorExport(key=Operator1, name_pattern=r'\D+1$'),
        ],
        services=[
            ServiceConf(
                key=Service2, name='service1',
                operators_read=[
                    OperatorPolicy(key=Operator1, name_pattern=r'\D+1$'),
                ],
            ),
            ServiceConf(
                key=Service2, name='service2',
            ),
        ],
        service_factories={Service2: F(Service2)},
        controllers=[
            ControllerConf(
                key=Controller2, name='ctrl1',
                args={'id': id + 2, 'data': data},
                operator_mapping=[
                    OperatorMappingPolicy(key=Operator2, map_to=Operator1, name_pattern=r'\D+1$'),
                ],
                providers_read=[
                    ProviderPolicy(key=Provider1, name_pattern=r'\D+1$'),
                ],
            ),
            ControllerConf(
                key=Controller2, name='ctrl2',
                args={'id': id + 3, 'data': data},
                operator_mapping=[
                    OperatorMappingPolicy(key=Operator2, map_to=Operator1, name_pattern=r'\D+2$'),
                ],
                providers_read=[
                    ProviderPolicy(key=Provider1, name_pattern=r'\D+2$'),
                ],
            ),
        ],
        controller_factories={Controller2: F(Controller2)},
    )


def __fini__():
    pass
