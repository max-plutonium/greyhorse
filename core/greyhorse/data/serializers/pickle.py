import pickle
from typing import Any

from .base import Deserializer, Serializer


class PickleSerializer(Serializer):
    def serialize(self, data: Any | None = None) -> bytes:
        return pickle.dumps(data)


class PickleDeserializer(Deserializer):
    def deserialize(self, data: bytes) -> Any | None:
        try:
            values = pickle.loads(data) if data else None
        except (pickle.UnpicklingError, ValueError, ModuleNotFoundError, MemoryError):
            return None

        return values
