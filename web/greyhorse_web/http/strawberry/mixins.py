import dataclasses
from collections.abc import Iterable
from typing import Any

import strawberry


class FromEntityMixin[E, T]:
    @classmethod
    def from_entity(cls, entity: E) -> T:
        data = {}
        for field in dataclasses.fields(cls):
            if type(field) is dataclasses.Field:
                data[field.name] = getattr(entity, field.name)
        return cls(**data)

    @classmethod
    def from_entities(cls, entities: Iterable[E]) -> Iterable[T]:
        for entity in entities:
            yield cls.from_entity(entity)


class ToDictMixin:
    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in dataclasses.asdict(self).items() if v != strawberry.UNSET}
