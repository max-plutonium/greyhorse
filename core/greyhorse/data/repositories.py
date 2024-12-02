from abc import ABC, abstractmethod
from collections.abc import AsyncIterable, Awaitable, Iterable, Mapping
from typing import Any, Protocol

from greyhorse.data.query import Query
from greyhorse.error import Error, ErrorCase
from greyhorse.maybe import Maybe
from greyhorse.result import Ok, Result
from greyhorse.utils.types import TypeWrapper


class EntityError(Error):
    namespace = 'greyhorse.data'

    Validation = ErrorCase(msg='Entity validation error: "{details}"', details=str)
    AlreadyExists = ErrorCase(msg='Entity already exists')
    NotOnlyOne = ErrorCase(msg='The result is not the only one')
    Empty = ErrorCase(msg='The result is empty')
    Deleted = ErrorCase(msg='Cannot perform operation because the entity is deleted')


class Repository[E, ID](Protocol):
    @abstractmethod
    def get(self, id_value: ID) -> Maybe[E] | Awaitable[Maybe[E]]: ...

    @abstractmethod
    def get_any(
        self, indices: Iterable[ID]
    ) -> Iterable[Maybe[E]] | Awaitable[Iterable[Maybe[E]]]: ...

    @abstractmethod
    def exists(self, id_value: ID) -> bool | Awaitable[bool]: ...

    @abstractmethod
    def load(
        self, instance: E, only: Iterable[str] | None = None
    ) -> bool | Awaitable[bool]: ...


class MutRepository[E, ID](Repository[E, ID], Protocol):
    @abstractmethod
    def create(
        self, data: Mapping[str, Any]
    ) -> Result[E, EntityError] | Awaitable[Result[E, EntityError]]: ...

    @abstractmethod
    def get_or_create(
        self, id_value: ID, data: Mapping[str, Any]
    ) -> (
        tuple[Result[E, EntityError], bool] | Awaitable[tuple[Result[E, EntityError], bool]]
    ): ...

    @abstractmethod
    def update_by_id(
        self, id_value: ID, data: Mapping[str, Any]
    ) -> Result[None, EntityError] | Awaitable[Result[None, EntityError]]: ...

    @abstractmethod
    def save(
        self, instance: E
    ) -> Result[None, EntityError] | Awaitable[Result[None, EntityError]]: ...

    @abstractmethod
    def save_all(self, objects: Iterable[E]) -> int | Awaitable[int]: ...

    @abstractmethod
    def delete(self, instance: E) -> bool | Awaitable[bool]: ...

    @abstractmethod
    def delete_all(self, indices: Iterable[ID] | None = None) -> int | Awaitable[int]: ...

    @abstractmethod
    def delete_by_id(self, id_value: ID) -> bool | Awaitable[bool]: ...


class SyncRepository[E, ID](TypeWrapper[E, ID], ABC):
    @abstractmethod
    def get(self, id_value: ID) -> Maybe[E]: ...

    @abstractmethod
    def get_any(self, indices: Iterable[ID]) -> Iterable[Maybe[E]]: ...

    @abstractmethod
    def exists(self, id_value: ID) -> bool: ...

    @abstractmethod
    def load(self, instance: E, only: Iterable[str] | None = None) -> bool: ...


class AsyncRepository[E, ID](TypeWrapper[E, ID], ABC):
    @abstractmethod
    async def get(self, id_value: ID) -> Maybe[E]: ...

    @abstractmethod
    async def get_any(self, indices: Iterable[ID]) -> Iterable[Maybe[E]]: ...

    @abstractmethod
    async def exists(self, id_value: ID) -> bool: ...

    @abstractmethod
    async def load(self, instance: E, only: Iterable[str] | None = None) -> bool: ...


class SyncMutRepository[E, ID](SyncRepository[E, ID], ABC):
    @abstractmethod
    def create(self, data: Mapping[str, Any]) -> Result[E, EntityError]: ...

    def get_or_create(
        self, id_value: ID, data: Mapping[str, Any]
    ) -> tuple[Result[E, EntityError], bool]:
        if instance := self.get(id_value).unwrap_or_none():
            return Ok(instance), False
        return self.create(data), True

    @abstractmethod
    def update_by_id(
        self, id_value: ID, data: Mapping[str, Any]
    ) -> Result[None, EntityError]: ...

    @abstractmethod
    def save(self, instance: E) -> Result[None, EntityError]: ...

    @abstractmethod
    def save_all(self, objects: Iterable[E]) -> int: ...

    @abstractmethod
    def delete(self, instance: E) -> bool: ...

    @abstractmethod
    def delete_all(self, indices: Iterable[ID] | None = None) -> int: ...

    @abstractmethod
    def delete_by_id(self, id_value: ID) -> bool: ...


class AsyncMutRepository[E, ID](AsyncRepository[E, ID], ABC):
    @abstractmethod
    async def create(self, data: Mapping[str, Any]) -> Result[E, EntityError]: ...

    async def get_or_create(
        self, id_value: ID, data: Mapping[str, Any]
    ) -> tuple[Result[E, EntityError], bool]:
        if instance := (await self.get(id_value)).unwrap_or_none():
            return Ok(instance), False
        return await self.create(data), True

    @abstractmethod
    async def update_by_id(
        self, id_value: ID, data: Mapping[str, Any]
    ) -> Result[None, EntityError]: ...

    @abstractmethod
    async def save(self, instance: E) -> Result[None, EntityError]: ...

    @abstractmethod
    async def save_all(self, objects: Iterable[E]) -> int: ...

    @abstractmethod
    async def delete(self, instance: E) -> bool: ...

    @abstractmethod
    async def delete_all(self, indices: Iterable[ID] | None = None) -> int: ...

    @abstractmethod
    async def delete_by_id(self, id_value: ID) -> bool: ...


class SyncFilterable[E, ID](ABC):
    @property
    @abstractmethod
    def query_class(self) -> type[Query]: ...

    @abstractmethod
    def list(
        self, query: Query | None = None, skip: int = 0, limit: int = 0
    ) -> Iterable[E]: ...

    @abstractmethod
    def sublist(
        self, field: object, query: Query | None = None, skip: int = 0, limit: int = 0
    ) -> Iterable[E]: ...

    @abstractmethod
    def count(self, query: Query | None = None) -> int: ...

    @abstractmethod
    def exists_by(self, query: Query) -> bool: ...


class AsyncFilterable[E, ID](ABC):
    @property
    @abstractmethod
    def query_class(self) -> type[Query]: ...

    @abstractmethod
    async def list(
        self, query: Query | None = None, skip: int = 0, limit: int = 0
    ) -> AsyncIterable[E]: ...

    @abstractmethod
    async def sublist(
        self,
        field: object,
        query: Query | None = None,
        skip: int = 0,
        limit: int = 0,
        **kwargs: dict[str, Any],
    ) -> Iterable[E]: ...

    @abstractmethod
    async def count(self, query: Query | None = None) -> int: ...

    @abstractmethod
    async def exists_by(self, query: Query) -> bool: ...


class SyncMutFilterable[E, ID](SyncFilterable[E, ID], ABC):
    @abstractmethod
    def update_by(self, query: Query, data: Mapping[str, Any]) -> int: ...

    @abstractmethod
    def delete_by(self, query: Query) -> int: ...


class AsyncMutFilterable[E, ID](AsyncFilterable[E, ID], ABC):
    @abstractmethod
    async def update_by(self, query: Query, data: Mapping[str, Any]) -> int: ...

    @abstractmethod
    async def delete_by(self, query: Query) -> int: ...
