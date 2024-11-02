from typing import Any

from pydantic import BaseModel, Field, PrivateAttr

from greyhorse.utils.invoke import caller_path

from ..abc.controllers import ControllerFactories
from ..abc.providers import (
    FactoryProvider,
    ForwardProvider,
    MutProvider,
    Provider,
    SharedProvider,
)
from ..abc.services import ServiceFactories
from ..schemas.elements import CtrlConf, SvcConf


class ComponentConf(BaseModel):
    enabled: bool = Field(default=True)

    resource_claims: list[type] = Field(default_factory=list)
    operators: list[type] = Field(default_factory=list)
    providers: list[type[Provider]] = Field(default_factory=list)

    controllers: list[CtrlConf] = Field(default_factory=list)
    services: list[SvcConf] = Field(default_factory=list)

    controller_factories: ControllerFactories = Field(default_factory=dict)
    service_factories: ServiceFactories = Field(default_factory=dict)


class ModuleConf(BaseModel):
    enabled: bool = Field(default=True)

    provider_claims: list[type[ForwardProvider] | type[SharedProvider]] = Field(
        default_factory=list
    )
    resource_claims: list[type] = Field(default_factory=list)

    operators: list[type] = Field(default_factory=list)
    providers: list[type[FactoryProvider] | type[MutProvider]] = Field(default_factory=list)

    components: dict[str, ComponentConf] = Field(default_factory=dict)


class ModuleComponentConf(ComponentConf):
    path: str = Field(frozen=True)
    args: dict[str, Any] = Field(default_factory=dict, frozen=True)
    _init_path: list[str] = PrivateAttr(default_factory=lambda: caller_path(5))
    _conf: ModuleConf | None = PrivateAttr(default=None)
