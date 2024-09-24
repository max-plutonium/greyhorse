from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any, Generic, Self, TypeVar

IdType = TypeVar('IdType')


class AbstractModel(Generic[IdType], ABC):
    @abstractmethod
    def get_id_value(self) -> IdType: ...

    #
    # Retrieve operations
    #

    @classmethod
    @abstractmethod
    async def get(cls, id_value: IdType, **kwargs) -> Self | None: ...

    @classmethod
    @abstractmethod
    async def get_any(cls, indices: Sequence[IdType], **kwargs) -> Sequence[Self | None]: ...

    @classmethod
    @abstractmethod
    async def exists(cls, id_value: IdType, **kwargs) -> bool: ...

    @abstractmethod
    async def load(self, only: Sequence[str] | None = None) -> bool: ...

    #
    # Modification operations
    #

    @classmethod
    @abstractmethod
    async def create(cls, data: Mapping[str, Any], **kwargs) -> Self | None: ...

    @classmethod
    @abstractmethod
    async def get_or_create(
        cls, id_value: IdType, data: Mapping[str, Any], **kwargs
    ) -> tuple[Self | None, bool]: ...

    @abstractmethod
    async def update(self, data: Mapping[str, Any], **kwargs) -> bool: ...

    @classmethod
    @abstractmethod
    async def update_by_id(
        cls, id_value: IdType, data: Mapping[str, Any], **kwargs
    ) -> bool: ...

    @abstractmethod
    async def save(self, **kwargs) -> bool: ...

    @classmethod
    @abstractmethod
    async def save_all(cls, objects: Sequence[Self], **kwargs) -> bool: ...

    @abstractmethod
    async def delete(self) -> bool: ...

    @classmethod
    @abstractmethod
    async def delete_all(cls, indices: Sequence[IdType] | None = None) -> bool: ...

    @classmethod
    @abstractmethod
    async def delete_by_id(cls, id_value: IdType) -> bool: ...
