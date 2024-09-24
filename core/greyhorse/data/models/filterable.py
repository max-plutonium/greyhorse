from abc import abstractmethod
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar

from .base import IdType
from .model import Model, UpdateSchemaType

if TYPE_CHECKING:
    from ..repositories.filterable import FilterableRepository


FilterType = TypeVar('FilterType')
SortingType = TypeVar('SortingType')


class FilterableModel(Model[IdType], Generic[IdType, FilterType, SortingType]):
    _repo: 'FilterableRepository[IdType, Self, FilterType, SortingType]'

    @classmethod
    def bind(
        cls, repository: 'FilterableRepository[IdType, Self, FilterType, SortingType]'
    ) -> None:
        cls._repo = repository

    @classmethod
    @abstractmethod
    def get_columns(cls) -> Mapping[str, Any]: ...

    @classmethod
    @abstractmethod
    def get_relationships(cls) -> Mapping[str, Any]: ...

    #
    # Retrieve operations
    #

    @classmethod
    async def list(
        cls,
        filters: FilterType | None = None,
        sorting: SortingType | None = None,
        skip: int = 0,
        limit: int = 0,
        **kwargs,
    ) -> Sequence[Self]:
        return await cls._repo.list(filters, sorting, skip, limit, **kwargs)

    @classmethod
    async def count(cls, filters: FilterType | None = None, **kwargs) -> int:
        return await cls._repo.count(filters, **kwargs)

    @classmethod
    async def exists_by(cls, filters: FilterType, **kwargs) -> bool:
        return await cls._repo.exists_by(filters, **kwargs)

    #
    # Modification operations
    #

    @classmethod
    async def update_by(
        cls, filters: FilterType, data: UpdateSchemaType | Mapping[str, Any], **kwargs
    ) -> int:
        update_data = data if isinstance(data, Mapping) else data.dict(exclude_unset=True)

        if update_data:
            update_data = cls.prepare_for_update(update_data)

        return await cls._repo.update_by(filters, update_data, **kwargs)

    @classmethod
    async def delete_by(cls, filters: FilterType, **kwargs) -> int:
        return await cls._repo.delete_by(filters, **kwargs)
