from typing import Any

from pydantic import BaseModel, Field, PrivateAttr

from greyhorse.app.abc.controllers import ControllerFactories
from greyhorse.app.abc.providers import Provider
from greyhorse.app.abc.services import ServiceFactories
from greyhorse.app.schemas.elements import CtrlConf, SvcConf
from greyhorse.utils.invoke import caller_path


class ProvidersConf(BaseModel, frozen=True):
    resource: type
    providers: list[type[Provider]] = Field(default_factory=list)


class ComponentConf(BaseModel):
    enabled: bool = Field(default=True)

    resource_grants: list[type] = Field(default_factory=list)
    provider_grants: list[ProvidersConf] = Field(default_factory=list)
    provider_imports: list[ProvidersConf] = Field(default_factory=list)

    controllers: list[CtrlConf] = Field(default_factory=list)
    services: list[SvcConf] = Field(default_factory=list)

    controller_factories: ControllerFactories = Field(default_factory=dict)
    service_factories: ServiceFactories = Field(default_factory=dict)


class ModuleConf(BaseModel):
    enabled: bool = Field(default=True)

    resource_claims: list[type] = Field(default_factory=list)
    provider_claims: list[ProvidersConf] = Field(default_factory=list)
    can_provide: list[type] = Field(default_factory=list)

    components: dict[str, ComponentConf] = Field(default_factory=dict)


class ModuleComponentConf(ComponentConf):
    path: str = Field(frozen=True)
    args: dict[str, Any] = Field(default_factory=dict, frozen=True)
    _init_path: list[str] = PrivateAttr(default_factory=lambda: caller_path(5))
    _conf: ModuleConf | None = PrivateAttr(default=None)
