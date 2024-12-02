from typing import Any

from pydantic import AliasChoices, BaseModel, Field, PrivateAttr, model_validator

from ...utils.invoke import caller_path
from ..abc.controllers import Controller
from ..abc.services import Service


class CtrlConf(BaseModel, frozen=True):
    type_: type[Controller] = Field(validation_alias=AliasChoices('type'))
    name: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    resources: list[type] = Field(default_factory=list)
    enabled: bool = Field(default=True)
    _init_path: list[str] = PrivateAttr(default_factory=lambda: caller_path(5))

    @model_validator(mode='before')
    def _setup_name(self: dict[str, Any]) -> dict:
        if 'name' not in self:
            self['name'] = self['type'].__name__
        return self


class SvcConf(BaseModel, frozen=True):
    type_: type[Service] = Field(validation_alias=AliasChoices('type'))
    name: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    resources: list[type] = Field(default_factory=list)
    enabled: bool = Field(default=True)
    _init_path: list[str] = PrivateAttr(default_factory=lambda: caller_path(5))

    @model_validator(mode='before')
    def _setup_name(self: dict[str, Any]) -> dict:
        if 'name' not in self:
            self['name'] = self['type'].__name__
        return self
