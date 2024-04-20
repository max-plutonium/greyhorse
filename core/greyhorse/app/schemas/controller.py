from typing import Pattern

from pydantic import BaseModel, Field

from .components import ResourceConf, ResourcePolicy
from ..entities.controller import ControllerKey
from ..entities.operator import OperatorKey


class OperatorMappingPolicy(BaseModel, frozen=True, arbitrary_types_allowed=True):
    key: OperatorKey
    map_to: OperatorKey
    name_pattern: Pattern | None = None


class ControllerConf(ResourceConf[ControllerKey]):
    operator_mapping: list[OperatorMappingPolicy] = Field(default_factory=list)
    resources_write: list[ResourcePolicy] = Field(default_factory=list)
