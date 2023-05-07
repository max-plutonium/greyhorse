from abc import ABC, abstractmethod
from typing import TypeVar, Sequence, Mapping, Any, Generic

from greyhorse_core.data.repositories.base import Repository, IdType, ModelType

FilterType = TypeVar('FilterType')
SortingType = TypeVar('SortingType')


class FilterableRepository(
    Repository[IdType, ModelType],
    Generic[IdType, ModelType, FilterType, SortingType]
):
    @abstractmethod
    async def list(
        self, filters: FilterType | None = None,
        sorting: SortingType | None = None,
        skip: int = 0, limit: int = 0, **kwargs,
    ) -> Sequence[ModelType]:
        ...

    @abstractmethod
    async def count(self, filters: FilterType | None = None, **kwargs) -> int:
        ...

    @abstractmethod
    async def exists_by(self, filters: FilterType, **kwargs) -> bool:
        ...

    @abstractmethod
    async def update_by(self, filters: FilterType, data: Mapping[str, Any], **kwargs) -> int:
        ...

    @abstractmethod
    async def delete_by(self, filters: FilterType, **kwargs) -> int:
        ...
