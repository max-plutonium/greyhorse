import asyncio
from abc import ABC
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Self, TypeVar

from pydantic.main import BaseModel as PydanticModel

from .base import AbstractModel, IdType
from .fields import ModelFieldsMixin

if TYPE_CHECKING:
    from ..repositories.base import ModelRepository


CreateSchemaType = TypeVar('CreateSchemaType', bound=PydanticModel)
UpdateSchemaType = TypeVar('UpdateSchemaType', bound=PydanticModel)


class Model(AbstractModel[IdType], ModelFieldsMixin, ABC):
    _repo: 'ModelRepository[IdType, Self]'

    @classmethod
    def bind(cls, repository: 'ModelRepository[IdType, Self]') -> None:
        cls._repo = repository

    @classmethod
    async def construct(cls, data: Mapping[str, Any], **kwargs) -> Self:
        return await cls._repo.construct(data, **kwargs)

    @classmethod
    async def construct_all(
        cls, objects: Sequence[Mapping[str, Any] | None], **kwargs
    ) -> Sequence[Self | None]:
        loop = asyncio.get_event_loop()
        awaitables = list()

        for data in objects:
            if data is None:
                future = loop.create_future()
                future.set_result(None)
                awaitables.append(future)
            else:
                awaitables.append(cls.construct(data, **kwargs))

        return await asyncio.gather(*awaitables)

    @classmethod
    def prepare_for_create(cls, data: Mapping[str, Any]) -> Mapping[str, Any]:
        return data

    @classmethod
    def prepare_for_update(cls, data: Mapping[str, Any]) -> Mapping[str, Any]:
        return data

    @classmethod
    def prepare_for_delete(cls, obj: Self) -> Self:
        return obj

    #
    # Retrieve operations
    #

    @classmethod
    async def get(cls, id_value: IdType, **kwargs) -> Self | None:
        return await cls._repo.get(id_value, **kwargs)

    @classmethod
    async def get_any(cls, indices: Sequence[IdType], **kwargs) -> Sequence[Self | None]:
        return await cls._repo.get_any(indices, **kwargs)

    @classmethod
    async def exists(cls, id_value: IdType, **kwargs) -> bool:
        return await cls._repo.exists(id_value, **kwargs)

    async def load(self, only: Sequence[str] | None = None) -> bool:
        return await self._repo.load(self, only)

    #
    # Modification operations
    #

    @classmethod
    async def create(cls, data: CreateSchemaType | Mapping[str, Any], **kwargs) -> Self | None:
        create_data = data if isinstance(data, Mapping) else data.dict(exclude_unset=True)

        if create_data:
            create_data = cls.prepare_for_create(create_data)

        return await cls._repo.create(create_data, **kwargs)

    @classmethod
    async def get_or_create(
        cls, id_value: Any, data: CreateSchemaType | Mapping[str, Any], **kwargs
    ) -> tuple[Self | None, bool]:
        if instance := await cls.get(id_value, **kwargs):
            return instance, False
        return await cls.create(data, **kwargs), True

    async def update(self, data: UpdateSchemaType | Mapping[str, Any], **kwargs) -> bool:
        update_data = data if isinstance(data, Mapping) else data.dict(exclude_unset=True)

        if update_data:
            update_data = self.prepare_for_update(update_data)

        return await self._repo.update_by_id(self.get_id_value(), update_data, **kwargs)

    @classmethod
    async def update_by_id(
        cls, id_value: IdType, data: UpdateSchemaType | Mapping[str, Any], **kwargs
    ) -> bool:
        update_data = data if isinstance(data, Mapping) else data.dict(exclude_unset=True)

        if update_data:
            update_data = cls.prepare_for_update(update_data)

        return await cls._repo.update_by_id(id_value, update_data, **kwargs)

    async def save(self, **kwargs) -> bool:
        return await self._repo.save(self, **kwargs)

    @classmethod
    async def save_all(cls, objects: Sequence[Self], **kwargs) -> bool:
        return await cls._repo.save_all(objects, **kwargs)

    async def delete(self) -> bool:
        return await self._repo.delete(self)

    @classmethod
    async def delete_all(cls, indices: Sequence[IdType] | None = None) -> int:
        return await cls._repo.delete_all(indices)

    @classmethod
    async def delete_by_id(cls, id_value: IdType) -> bool:
        return await cls._repo.delete_by_id(id_value)
