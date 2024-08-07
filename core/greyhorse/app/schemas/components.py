from typing import Any

from pydantic import BaseModel, Field, PrivateAttr

from greyhorse.app.abc.controllers import ControllerFactories
from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import Provider
from greyhorse.app.abc.services import ServiceFactories
from greyhorse.app.schemas.elements import CtrlConf, SvcConf
from greyhorse.utils.invoke import caller_path


class ProvidersConf(BaseModel, frozen=True):
    resource: type
    types: list[type[Provider]] = Field(default_factory=list)


class OperatorsConf(BaseModel, frozen=True):
    resource: type
    types: list[type[Operator]] = Field(default_factory=list)


class BasicComponentConf(BaseModel):
    name: str = Field(frozen=True)
    enabled: bool = Field(default=True)

    provider_grants: list[ProvidersConf] = Field(default_factory=list)
    provider_imports: list[ProvidersConf] = Field(default_factory=list)


class ModuleConf(BaseModel):
    enabled: bool = Field(default=True)

    provider_claims: list[ProvidersConf] = Field(default_factory=list)
    provider_exports: list[ProvidersConf] = Field(default_factory=list)

    components: list[BasicComponentConf] = Field(default_factory=list)


class ComponentConf(BasicComponentConf):
    controllers: list[CtrlConf] = Field(default_factory=list)
    services: list[SvcConf] = Field(default_factory=list)

    controller_factories: ControllerFactories = Field(default_factory=dict)
    service_factories: ServiceFactories = Field(default_factory=dict)


class ModuleComponentConf(BasicComponentConf):
    path: str = Field(frozen=True)
    args: dict[str, Any] = Field(default_factory=dict, frozen=True)
    _init_path: list[str] = PrivateAttr(default_factory=lambda: caller_path(5))
    _conf: ModuleConf | None = PrivateAttr(default=None)
