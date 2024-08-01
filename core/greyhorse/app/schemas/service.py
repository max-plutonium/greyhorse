from typing import Pattern, Any

from pydantic import BaseModel, Field, model_validator

from ..abc.operators import Operator
from ..abc.providers import Provider
from ..abc.services import Service


class ProvColPolicy(BaseModel, frozen=True, arbitrary_types_allowed=True):
    type: type[Provider]
    key_pattern: Pattern | None = None


class OpColPolicy(BaseModel, frozen=True, arbitrary_types_allowed=True):
    type: type[Operator]
    key_pattern: Pattern | None = None


class SvcConf(BaseModel, frozen=True):
    type: type[Service]
    name: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = Field(default=True)
    providers_set: list[ProvColPolicy] = Field(default_factory=list)
    operators_set: list[OpColPolicy] = Field(default_factory=list)

    @model_validator(mode='before')
    def _setup_name(self: dict[str, Any]):
        if 'name' not in self:
            self['name'] = self['type'].__name__
        return self
