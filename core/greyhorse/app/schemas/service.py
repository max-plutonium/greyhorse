from typing import Pattern

from pydantic import BaseModel, ConfigDict, Field

from .components import ResourceConf
from .controller import OperatorMappingPolicy
from ..entities.providers import ProviderKey
from ..entities.service import ServiceKey


class ProviderMappingPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: ProviderKey
    name_pattern: Pattern | None = None


class ServiceConf(ResourceConf[ServiceKey]):
    model_config = ConfigDict(frozen=True)

    operator_mapping: list[OperatorMappingPolicy] = Field(default_factory=list)
    provider_mapping: list[ProviderMappingPolicy] = Field(default_factory=list)
