from abc import ABC
from collections.abc import Mapping, Sequence
from typing import Any

from ..serializers import Deserializer, Serializer
from .model import Model


class SerializableModel(Model, ABC):
    class Meta(Model.Meta):
        serializer: Serializer = None
        deserializer: Deserializer = None

    def __init_subclass__(cls, **kwargs):
        from greyhorse.data.serializers.pickle import PickleDeserializer, PickleSerializer

        cls.Meta.serializer = cls.Meta.serializer or PickleSerializer()
        cls.Meta.deserializer = cls.Meta.deserializer or PickleDeserializer()

        super().__init_subclass__(**kwargs)

    # noinspection PyProtectedMember
    @classmethod
    def get_serializable_fields(cls) -> set[str]:
        key = cls._fields_cache_key()
        if key not in cls.Meta._fields_cache:
            cls._calculate_fields()
        return cls.Meta._fields_cache[key].ser

    def get_serializable_values(
        self, only_fields: Sequence[str] | None = None
    ) -> Mapping[str, Any] | None:
        serializable_fields = self.get_serializable_fields()
        only_fields = set(only_fields) if only_fields else set()

        return {
            name: getattr(self, name)
            for name in serializable_fields
            if hasattr(self, name) and (not only_fields or name in only_fields)
        }

    def serialize(self, only_fields: Sequence[str] | None = None) -> bytes:
        return self.Meta.serializer.serialize(self.get_serializable_values(only_fields))

    @classmethod
    def deserialize(cls, data: bytes) -> Mapping[str, Any] | None:
        return cls.Meta.deserializer.deserialize(data)
