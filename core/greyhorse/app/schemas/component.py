from pydantic import BaseModel, Field

from greyhorse.app.abc.controllers import ControllerFactories
from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import Provider
from greyhorse.app.abc.services import ServiceFactories
from .controller import CtrlConf
from .service import SvcConf


class ProvidersConf(BaseModel, frozen=True):
    resource: type
    types: list[type[Provider]] = Field(default_factory=list)


class OperatorsConf(BaseModel, frozen=True):
    resource: type
    types: list[type[Operator]] = Field(default_factory=list)


class ComponentConf(BaseModel):
    name: str = Field(frozen=True)
    enabled: bool = Field(default=True)

    providers: list[ProvidersConf] = Field(default_factory=list)
    operators: list[OperatorsConf] = Field(default_factory=list)

    controllers: list[CtrlConf] = Field(default_factory=list)
    services: list[SvcConf] = Field(default_factory=list)

    controller_factories: ControllerFactories = Field(default_factory=dict)
    service_factories: ServiceFactories = Field(default_factory=dict)
