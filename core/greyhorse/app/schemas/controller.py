from typing import Pattern

from pydantic import BaseModel, ConfigDict, Field

from .components import ResourceConf, ResourcePolicy
from ..entities.controller import ControllerKey
from ..entities.operator import OperatorKey


class OperatorMappingPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: OperatorKey
    map_to: OperatorKey
    name_pattern: Pattern | None = None


class ControllerConf(ResourceConf[ControllerKey]):
    model_config = ConfigDict(frozen=True)

    operator_mapping: list[OperatorMappingPolicy] = Field(default_factory=list)
    resources_write: list[ResourcePolicy] = Field(default_factory=list)
