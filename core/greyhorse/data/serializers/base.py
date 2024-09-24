from collections.abc import Mapping
from typing import Any, Protocol


class Serializer(Protocol):
    def serialize(self, data: Any | None = None) -> bytes: ...


class Deserializer(Protocol):
    def deserialize(self, data: bytes) -> Any | None: ...


class ModelSerializer(Protocol):
    serializer: Serializer

    def serialize(self, only_fields: list[str] | None = None) -> bytes:
        return self.serializer.serialize(self.get_serializable_values(only_fields))

    def get_serializable_values(
        self, only_fields: list[str] | None = None
    ) -> Mapping[str, Any] | None: ...
