from pydantic import BaseModel, Field

from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import Provider
from greyhorse.app.abc.services import ServiceFactories
from .service import SvcConf


class ComponentConf(BaseModel, arbitrary_types_allowed=True):
    name: str = Field(frozen=True)
    enabled: bool = Field(default=True)

    resources: list[type] = Field(default_factory=list)
    providers: list[type[Provider]] = Field(default_factory=list)
    operators: list[type[Operator]] = Field(default_factory=list)
    services: list[SvcConf] = Field(default_factory=list)

    service_factories: ServiceFactories = Field(default_factory=dict)
