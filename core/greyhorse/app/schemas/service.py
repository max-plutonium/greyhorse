from typing import Any

from pydantic import BaseModel, Field, model_validator, AliasChoices

from ..abc.providers import Provider
from ..abc.services import Service


class SvcConf(BaseModel, frozen=True):
    type_: type[Service] = Field(validation_alias=AliasChoices('type'))
    name: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    providers: list[type[Provider]] = Field(default_factory=list)

    @model_validator(mode='before')
    def _setup_name(self: dict[str, Any]):
        if 'name' not in self:
            self['name'] = self['type'].__name__
        return self
