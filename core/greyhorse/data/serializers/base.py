from collections.abc import Mapping
from typing import Any, Protocol

from greyhorse.maybe import Maybe


class Serializer[T](Protocol):
    def serialize(self, data: T) -> bytes: ...


class Deserializer[T](Protocol):
    def deserialize(self, data: bytes) -> Maybe[T]: ...


class ModelSerializer(Protocol):
    serializer: Serializer

    def serialize(self, only_fields: list[str] | None = None) -> bytes:
        return self.serializer.serialize(self.get_serializable_values(only_fields))

    def get_serializable_values(
        self, only_fields: list[str] | None = None
    ) -> Mapping[str, Any] | None: ...
