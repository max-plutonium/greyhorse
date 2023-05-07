from abc import abstractmethod
from typing import Generic, Self, Mapping, Any, Sequence

from .base import IdType
from .model import Model, UpdateSchemaType
from ..repositories.filterable import FilterableRepository, FilterType, SortingType


class FilterableModel(Model[IdType], Generic[IdType, FilterType, SortingType]):
    _repo: FilterableRepository[IdType, Self, FilterType, SortingType]

    @classmethod
    def bind(cls, repository: FilterableRepository[IdType, Self, FilterType, SortingType]):
        cls._repo = repository

    @classmethod
    @abstractmethod
    def query_for_select(cls, include_rela: set[str] | None = None,
                         exclude_rela: set[str] | None = None, **kwargs):
        ...

    @classmethod
    @abstractmethod
    def query_for_update(cls, **kwargs):
        ...

    @classmethod
    @abstractmethod
    def query_for_delete(cls, **kwargs):
        ...

    @classmethod
    @abstractmethod
    def get_columns(cls) -> Mapping[str, Any]:
        ...

    @classmethod
    @abstractmethod
    def get_relationships(cls) -> Mapping[str, Any]:
        ...

    @classmethod
    @abstractmethod
    def query_options(cls, include: set[str] | None = None, exclude: set[str] | None = None):
        ...

    #
    # Retrieve operations
    #

    @classmethod
    async def list(
        cls, filters: FilterType | None = None,
        sorting: SortingType | None = None,
        skip: int = 0, limit: int = 0, **kwargs,
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
        cls, filters: FilterType, data: UpdateSchemaType | Mapping[str, Any], **kwargs,
    ) -> int:
        if isinstance(data, Mapping):
            update_data = data
        else:
            update_data = data.dict(exclude_unset=True)

        if update_data:
            update_data = cls.prepare_for_update(update_data)

        return await cls._repo.update_by(filters, update_data, **kwargs)

    @classmethod
    async def delete_by(cls, filters: FilterType, **kwargs) -> int:
        return await cls._repo.delete_by(filters, **kwargs)

    #
    # Query operations
    #

    @classmethod
    @abstractmethod
    def query_get(cls, id_value: IdType, query=None, **kwargs):
        ...

    @classmethod
    @abstractmethod
    def query_any(cls, indices: Sequence[IdType], query=None, **kwargs):
        ...

    @classmethod
    @abstractmethod
    def query_list(
        cls, filters: FilterType | None = None,
        sorting: SortingType | None = None,
        skip: int = 0, limit: int = 0, **kwargs,
    ):
        ...

    @classmethod
    @abstractmethod
    def query_count(cls, filters: FilterType | None = None, **kwargs):
        ...

    @classmethod
    @abstractmethod
    def query_exists(cls, id_value: IdType, **kwargs):
        ...

    @classmethod
    @abstractmethod
    def query_exists_by(cls, filters: FilterType, **kwargs):
        ...

    @classmethod
    @abstractmethod
    def query_update(cls, filters: FilterType, **kwargs):
        ...

    @classmethod
    @abstractmethod
    def query_delete(cls, filters: FilterType, **kwargs):
        ...
