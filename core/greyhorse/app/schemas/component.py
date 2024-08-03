from pydantic import BaseModel, Field, AliasChoices

from greyhorse.app.abc.controllers import ControllerFactories
from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import Provider
from greyhorse.app.abc.services import ServiceFactories
from .controller import CtrlConf
from .service import SvcConf


class ResourceConf(BaseModel, frozen=True):
    type_: type = Field(validation_alias=AliasChoices('type'))
    providers: list[type[Provider]] = Field(default_factory=list)


class ComponentConf(BaseModel, arbitrary_types_allowed=True):
    name: str = Field(frozen=True)
    enabled: bool = Field(default=True)

    resources: list[ResourceConf] = Field(default_factory=list)
    operators: list[type[Operator]] = Field(default_factory=list)

    controllers: list[CtrlConf] = Field(default_factory=list)
    services: list[SvcConf] = Field(default_factory=list)

    controller_factories: ControllerFactories = Field(default_factory=dict)
    service_factories: ServiceFactories = Field(default_factory=dict)
