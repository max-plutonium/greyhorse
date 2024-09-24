from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import (
    ClassMethodDescriptorType,
    FunctionType,
    GetSetDescriptorType,
    MappingProxyType,
    MemberDescriptorType,
    MethodDescriptorType,
    MethodType,
    MethodWrapperType,
    WrapperDescriptorType,
)
from typing import Any, Protocol


@dataclass
class FieldsCache:
    priv: set[str] = field(default_factory=set)
    pub: set[str] = field(default_factory=set)
    ser: set[str] = field(default_factory=set)


class ModelFieldsMixin(Protocol):
    class Meta:
        private_fields: set[str] = set()
        public_fields: set[str] = set()
        serializable_fields: set[str] = set()
        non_serializable_fields: set[str] = set()
        _fields_cache: dict[str, FieldsCache] = dict()

    @classmethod
    def _fields_cache_key(cls):
        return '.'.join([cls.__module__, cls.__qualname__])

    # noinspection PyProtectedMember
    @classmethod
    def _calculate_fields(cls) -> None:
        private_types = (
            type,
            FunctionType,
            MethodType,
            MappingProxyType,
            WrapperDescriptorType,
            MethodWrapperType,
            MethodDescriptorType,
            ClassMethodDescriptorType,
            GetSetDescriptorType,
            MemberDescriptorType,
        )

        private_fields, public_fields, serializable_fields = set(), set(), set()

        for attr in dir(cls):
            value = getattr(cls, attr)
            if isinstance(value, private_types) or attr[0] == '_':
                private_fields.add(attr)
            elif not isinstance(value, private_types):
                if not isinstance(value, property):
                    serializable_fields.add(attr)
                public_fields.add(attr)

        private_fields.update(cls.Meta.private_fields)
        private_fields.difference_update(cls.Meta.public_fields)
        public_fields.update(cls.Meta.public_fields)
        public_fields.difference_update(cls.Meta.private_fields)
        serializable_fields.update(cls.Meta.serializable_fields)
        serializable_fields.difference_update(cls.Meta.non_serializable_fields)
        cls.Meta._fields_cache[cls._fields_cache_key()] = FieldsCache(
            priv=private_fields, pub=public_fields, ser=serializable_fields
        )

    # noinspection PyProtectedMember
    @classmethod
    def drop_fields_cache(cls) -> None:
        key = cls._fields_cache_key()
        cls.Meta._fields_cache.pop(key, None)

    # noinspection PyProtectedMember
    @classmethod
    def get_private_fields(cls) -> set[str]:
        key = cls._fields_cache_key()
        if key not in cls.Meta._fields_cache:
            cls._calculate_fields()
        return cls.Meta._fields_cache[key].priv

    # noinspection PyProtectedMember
    @classmethod
    def get_public_fields(cls) -> set[str]:
        key = cls._fields_cache_key()
        if key not in cls.Meta._fields_cache:
            cls._calculate_fields()
        return cls.Meta._fields_cache[key].pub

    @classmethod
    def get_fields(cls) -> set[str]:
        return cls.get_public_fields()

    def get_values(
        self,
        only_fields: Sequence[str] | None = None,
        exclude_fields: Sequence[str] | None = None,
    ) -> Mapping[str, Any]:
        public_fields = self.get_public_fields()
        only_fields = set(only_fields) if only_fields else set()
        exclude_fields = set(exclude_fields) if exclude_fields else set()

        return {
            name: getattr(self, name)
            for name in public_fields
            if hasattr(self, name)
            and (not only_fields or name in only_fields)
            and (not exclude_fields or name not in exclude_fields)
        }
