from typing import Pattern, Any

from pydantic import BaseModel, Field, model_validator

from ..abc.controllers import Controller
from ..abc.operators import Operator
from ..abc.providers import Provider


class ProvSelPolicy(BaseModel, frozen=True, arbitrary_types_allowed=True):
    type: type[Provider]
    key_pattern: Pattern | None = None


class OpSelPolicy(BaseModel, frozen=True, arbitrary_types_allowed=True):
    type: type[Operator]
    key_pattern: Pattern | None = None


class CtrlConf(BaseModel, frozen=True):
    type: type[Controller]
    name: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = Field(default=True)
    providers_get: list[ProvSelPolicy] = Field(default_factory=list)
    operators_get: list[OpSelPolicy] = Field(default_factory=list)

    @model_validator(mode='before')
    def _setup_name(self: dict[str, Any]):
        if 'name' not in self:
            self['name'] = self['type'].__name__
        return self
