from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from typing import Any


@dataclass
class CacheData:
    cache_id: str
    data: Any | None = None


class CacheOperator(ABC):
    def get_cache_id(self, id_value: Any) -> str:
        return str(id_value)

    @abstractmethod
    def get_cache_key(self, id_value: Any) -> str: ...

    @abstractmethod
    async def cache_one(
        self, data: CacheData, ttl: timedelta | None = None, **kwargs
    ) -> bool: ...

    @abstractmethod
    async def cache_many(
        self, objects: Sequence[CacheData], ttl: timedelta | None = None, **kwargs
    ) -> bool: ...

    @abstractmethod
    async def load_one(self, cache_key: str, **kwargs) -> tuple[bool, Any | None]: ...

    @abstractmethod
    async def load_many(
        self, indices: Sequence[Any], **kwargs
    ) -> Sequence[Mapping[str, Any] | None]: ...

    @abstractmethod
    async def drop_one(self, cache_key: str) -> bool: ...

    @abstractmethod
    async def drop_many(self, indices: Sequence[Any] | None = None) -> int: ...

    @abstractmethod
    async def drop_all(self, prefix: str | None = None) -> int: ...

    @abstractmethod
    async def exists(self, cache_key: str) -> bool: ...


class ModelCacheOperator(CacheOperator):
    @abstractmethod
    def get_model_cache_key(self) -> str: ...

    def get_cache_id(self, id_value: Any) -> str:
        return str(id_value)

    def get_cache_key(self, id_value: Any) -> str:
        return f'{self.get_model_cache_key()}:{self.get_cache_id(id_value)}'


class ScanCacheMixin(CacheOperator):
    @abstractmethod
    async def scan(
        self, cache_key: str | None = None, match: str | None = None, count: int | None = None
    ) -> AsyncGenerator[tuple[str, Any | None], None]: ...
