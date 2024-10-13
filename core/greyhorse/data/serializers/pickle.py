import pickle
from typing import override

from greyhorse.maybe import Just, Maybe, Nothing

from .base import Deserializer, Serializer


class PickleSerializer[T](Serializer[T]):
    def serialize(self, data: T) -> bytes:
        return pickle.dumps(data)


class PickleDeserializer[T](Deserializer[T]):
    @override
    def deserialize(self, data: bytes) -> Maybe[T]:
        try:
            value = pickle.loads(data) if data else None
        except (pickle.UnpicklingError, ValueError, ModuleNotFoundError, MemoryError):
            return Nothing

        return Just(value)
