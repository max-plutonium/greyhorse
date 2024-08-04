from typing import Any

from pydantic import BaseModel, Field, model_validator, AliasChoices

from ..abc.controllers import Controller
from ..abc.operators import Operator


class CtrlConf(BaseModel, frozen=True):
    type_: type[Controller] = Field(validation_alias=AliasChoices('type'))
    name: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    operators: list[type[Operator]] = Field(default_factory=list)

    @model_validator(mode='before')
    def _setup_name(self: dict[str, Any]):
        if 'name' not in self:
            self['name'] = self['type'].__name__
        return self
