from typing import Any, Pattern

from pydantic import BaseModel, ConfigDict, Field

from ..entities.operator import OperatorKey
from ..entities.providers import ProviderKey


class DepsPolicy[DK](BaseModel):
    model_config = ConfigDict(frozen=True)

    key: DK
    name_pattern: Pattern | None = None


class ResourcePolicy(DepsPolicy[Any]):
    pass


class ProviderPolicy(DepsPolicy[ProviderKey]):
    pass


class OperatorPolicy(DepsPolicy[OperatorKey]):
    pass


class ResourceConf[K](BaseModel):
    model_config = ConfigDict(frozen=True)

    key: K
    name: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = Field(default=True)
    resources_read: list[ResourcePolicy] = Field(default_factory=list)
    providers_read: list[ProviderPolicy] = Field(default_factory=list)
    operators_read: list[OperatorPolicy] = Field(default_factory=list)
