from abc import abstractmethod
from typing import Any, Generic, Mapping, Sequence, TypeVar

from .base import EntityType, IdType, Repository

FilterType = TypeVar('FilterType')
SortingType = TypeVar('SortingType')


class FilterableRepository(
    Repository[IdType, EntityType],
    Generic[IdType, EntityType, FilterType, SortingType],
):
    @abstractmethod
    async def list(
        self, filters: FilterType | None = None,
        sorting: SortingType | None = None,
        skip: int = 0, limit: int = 0, **kwargs,
    ) -> Sequence[EntityType]:
        ...

    @abstractmethod
    async def sublist(
        self, field, filters: FilterType | None = None,
        sorting: SortingType | None = None,
        skip: int = 0, limit: int = 0, **kwargs,
    ) -> Sequence[EntityType]:
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

    #
    # Query operations
    #

    @abstractmethod
    def query_for_select(self, **kwargs):
        ...

    @abstractmethod
    def query_for_update(self, **kwargs):
        ...

    @abstractmethod
    def query_for_delete(self, **kwargs):
        ...

    @abstractmethod
    def query_get(self, id_value: IdType, query=None, **kwargs):
        ...

    @abstractmethod
    def query_any(self, indices: Sequence[IdType], query=None, **kwargs):
        ...

    @abstractmethod
    def query_list(
        self, filters: FilterType | None = None,
        sorting: SortingType | None = None,
        skip: int = 0, limit: int = 0, **kwargs,
    ):
        ...

    @abstractmethod
    def query_count(self, filters: FilterType | None = None, **kwargs):
        ...

    @abstractmethod
    def query_exists(self, id_value: IdType, **kwargs):
        ...

    @abstractmethod
    def query_exists_by(self, filters: FilterType, **kwargs):
        ...

    @abstractmethod
    def query_update(self, filters: FilterType, **kwargs):
        ...

    @abstractmethod
    def query_delete(self, filters: FilterType, **kwargs):
        ...
