from typing import Any, Callable, Optional, Pattern

from pydantic import BaseModel, Field, PrivateAttr

from greyhorse.utils.invoke import caller_path
from .controller import ControllerConf
from .service import ServiceConf
from ..entities.controller import ControllerFactoryMapping
from ..entities.module import Module
from ..entities.operator import OperatorKey
from ..entities.providers import ProviderKey
from ..entities.service import ServiceFactoryMapping


class ProviderClaim(BaseModel, frozen=True, arbitrary_types_allowed=True):
    key: ProviderKey
    name_pattern: Pattern | None = None


class OperatorExport(BaseModel, frozen=True, arbitrary_types_allowed=True):
    key: OperatorKey
    name_pattern: Pattern | None = None


class ModuleDesc(BaseModel):
    path: str = Field(frozen=True)
    args: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = Field(default=True, frozen=True)

    _conf: Optional['ModuleConf'] = PrivateAttr(default=None)
    _initpath: list[str] = PrivateAttr(default_factory=lambda: caller_path(5))


class ModuleConf(BaseModel, arbitrary_types_allowed=True):
    name: str = Field(frozen=True)
    enabled: bool = Field(default=True)
    factory: Callable[[...], Module] = Field(default=Module, frozen=True)

    submodules: list[ModuleDesc] = Field(default_factory=list)

    controllers: list[ControllerConf] = Field(default_factory=list)
    services: list[ServiceConf] = Field(default_factory=list)

    controller_factories: ControllerFactoryMapping = Field(default_factory=dict)
    service_factories: ServiceFactoryMapping = Field(default_factory=dict)

    provider_claims: list[ProviderClaim] = Field(default_factory=list)
    operator_exports: list[OperatorExport] = Field(default_factory=list)
