from typing import Pattern

from pydantic import BaseModel, Field

from .components import ResourceConf
from .controller import OperatorMappingPolicy
from ..entities.providers import ProviderKey
from ..entities.service import ServiceKey


class ProviderMappingPolicy(BaseModel, frozen=True, arbitrary_types_allowed=True):
    key: ProviderKey
    name_pattern: Pattern | None = None


class ServiceConf(ResourceConf[ServiceKey]):
    operator_mapping: list[OperatorMappingPolicy] = Field(default_factory=list)
    provider_mapping: list[ProviderMappingPolicy] = Field(default_factory=list)
