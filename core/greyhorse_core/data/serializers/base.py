from typing import Any, List, Mapping, Optional, Protocol


class Serializer(Protocol):
    def serialize(self, data: Any | None = None) -> bytes:
        ...


class Deserializer(Protocol):
    def deserialize(self, data: bytes) -> Any | None:
        ...


class ModelSerializer(Protocol):
    serializer: Serializer

    def serialize(self, only_fields: list[str] = None) -> bytes:
        return self.serializer.serialize(self.get_serializable_values(only_fields))

    def get_serializable_values(self, only_fields: list[str] = None) -> Mapping[str, Any] | None:
        ...
