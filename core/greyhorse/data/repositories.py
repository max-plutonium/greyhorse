from abc import ABC, abstractmethod
from collections.abc import Awaitable, Iterable, Mapping
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
    def get(self, id_value: ID, **kwargs) -> Maybe[E] | Awaitable[Maybe[E]]: ...

    @abstractmethod
    def get_any(
        self, indices: Iterable[ID], **kwargs
    ) -> Iterable[Maybe[E]] | Awaitable[Iterable[Maybe[E]]]: ...

    @abstractmethod
    def exists(self, id_value: ID, **kwargs) -> bool | Awaitable[bool]: ...

    @abstractmethod
    def load(
        self, instance: E, only: Iterable[str] | None = None
    ) -> bool | Awaitable[bool]: ...


class MutRepository[E, ID](Repository[E, ID], Protocol):
    @abstractmethod
    def create(
        self, data: Mapping[str, Any], **kwargs
    ) -> Result[E, EntityError] | Awaitable[Result[E, EntityError]]: ...

    @abstractmethod
    def get_or_create(
        self, id_value: ID, data: Mapping[str, Any], **kwargs
    ) -> (
        tuple[Result[E, EntityError], bool] | Awaitable[tuple[Result[E, EntityError], bool]]
    ): ...

    @abstractmethod
    def update_by_id(
        self, id_value: ID, data: Mapping[str, Any], **kwargs
    ) -> Result[None, EntityError] | Awaitable[Result[None, EntityError]]: ...

    @abstractmethod
    def save(
        self, instance: E, **kwargs
    ) -> Result[None, EntityError] | Awaitable[Result[None, EntityError]]: ...

    @abstractmethod
    def save_all(self, objects: Iterable[E], **kwargs) -> int | Awaitable[int]: ...

    @abstractmethod
    def delete(self, instance: E) -> bool | Awaitable[bool]: ...

    @abstractmethod
    def delete_all(self, indices: Iterable[ID] | None = None) -> int | Awaitable[int]: ...

    @abstractmethod
    def delete_by_id(self, id_value: ID) -> bool | Awaitable[bool]: ...


class SyncRepository[E, ID](TypeWrapper[E, ID], ABC):
    @abstractmethod
    def get(self, id_value: ID, **kwargs) -> Maybe[E]: ...

    @abstractmethod
    def get_any(self, indices: Iterable[ID], **kwargs) -> Iterable[Maybe[E]]: ...

    @abstractmethod
    def exists(self, id_value: ID, **kwargs) -> bool: ...

    @abstractmethod
    def load(self, instance: E, only: Iterable[str] | None = None) -> bool: ...


class AsyncRepository[E, ID](TypeWrapper[E, ID], ABC):
    @abstractmethod
    async def get(self, id_value: ID, **kwargs) -> Maybe[E]: ...

    @abstractmethod
    async def get_any(self, indices: Iterable[ID], **kwargs) -> Iterable[Maybe[E]]: ...

    @abstractmethod
    async def exists(self, id_value: ID, **kwargs) -> bool: ...

    @abstractmethod
    async def load(self, instance: E, only: Iterable[str] | None = None) -> bool: ...


class SyncMutRepository[E, ID](SyncRepository[E, ID], ABC):
    @abstractmethod
    def create(self, data: Mapping[str, Any], **kwargs) -> Result[E, EntityError]: ...

    def get_or_create(
        self, id_value: ID, data: Mapping[str, Any], **kwargs
    ) -> tuple[Result[E, EntityError], bool]:
        if instance := self.get(id_value, **kwargs).unwrap_or_none():
            return Ok(instance), False
        return self.create(data, **kwargs), True

    @abstractmethod
    def update_by_id(
        self, id_value: ID, data: Mapping[str, Any], **kwargs
    ) -> Result[None, EntityError]: ...

    @abstractmethod
    def save(self, instance: E, **kwargs) -> Result[None, EntityError]: ...

    @abstractmethod
    def save_all(self, objects: Iterable[E], **kwargs) -> int: ...

    @abstractmethod
    def delete(self, instance: E) -> bool: ...

    @abstractmethod
    def delete_all(self, indices: Iterable[ID] | None = None) -> int: ...

    @abstractmethod
    def delete_by_id(self, id_value: ID) -> bool: ...


class AsyncMutRepository[E, ID](AsyncRepository[E, ID], ABC):
    @abstractmethod
    async def create(self, data: Mapping[str, Any], **kwargs) -> Result[E, EntityError]: ...

    async def get_or_create(
        self, id_value: ID, data: Mapping[str, Any], **kwargs
    ) -> tuple[Result[E, EntityError], bool]:
        if instance := (await self.get(id_value, **kwargs)).unwrap_or_none():
            return Ok(instance), False
        return await self.create(data, **kwargs), True

    @abstractmethod
    async def update_by_id(
        self, id_value: ID, data: Mapping[str, Any], **kwargs
    ) -> Result[None, EntityError]: ...

    @abstractmethod
    async def save(self, instance: E, **kwargs) -> Result[None, EntityError]: ...

    @abstractmethod
    async def save_all(self, objects: Iterable[E], **kwargs) -> int: ...

    @abstractmethod
    async def delete(self, instance: E) -> bool: ...

    @abstractmethod
    async def delete_all(self, indices: Iterable[ID] | None = None) -> int: ...

    @abstractmethod
    async def delete_by_id(self, id_value: ID) -> bool: ...


class SyncFilterable[E, ID](ABC):
    @abstractmethod
    def list(
        self, query: Query | None = None, skip: int = 0, limit: int = 0, **kwargs
    ) -> Iterable[E]: ...

    @abstractmethod
    def sublist(
        self, field: str, query: Query | None = None, skip: int = 0, limit: int = 0, **kwargs
    ) -> Iterable[E]: ...

    @abstractmethod
    def count(self, query: Query | None = None, **kwargs) -> int: ...

    @abstractmethod
    def exists_by(self, query: Query, **kwargs) -> bool: ...


class AsyncFilterable[E, ID](ABC):
    @abstractmethod
    async def list(
        self, query: Query | None = None, skip: int = 0, limit: int = 0, **kwargs
    ) -> Iterable[E]: ...

    @abstractmethod
    async def sublist(
        self, field: str, query: Query | None = None, skip: int = 0, limit: int = 0, **kwargs
    ) -> Iterable[E]: ...

    @abstractmethod
    async def count(self, query: Query | None = None, **kwargs) -> int: ...

    @abstractmethod
    async def exists_by(self, query: Query, **kwargs) -> bool: ...


class SyncMutFilterable[E, ID](SyncFilterable[E, ID], ABC):
    @abstractmethod
    def update_by(self, query: Query, data: Mapping[str, Any], **kwargs) -> int: ...

    @abstractmethod
    def delete_by(self, query: Query, **kwargs) -> int: ...


class AsyncMutFilterable[E, ID](AsyncFilterable[E, ID], ABC):
    @abstractmethod
    async def update_by(self, query: Query, data: Mapping[str, Any], **kwargs) -> int: ...

    @abstractmethod
    async def delete_by(self, query: Query, **kwargs) -> int: ...
