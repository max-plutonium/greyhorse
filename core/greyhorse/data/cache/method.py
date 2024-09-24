import asyncio
import operator
from collections.abc import Mapping, Sequence
from datetime import timedelta
from functools import reduce
from typing import Any

from greyhorse.data.cache.base import CacheData, ModelCacheOperator
from greyhorse.utils.hashes import calculate_digest


class MethodCache:
    def __init__(self, op: ModelCacheOperator, ttl: timedelta | None = None) -> None:
        self._op = op
        self._ttl = ttl

    @property
    def op(self) -> ModelCacheOperator:
        return self._op

    def get_model_cache_key(self) -> str:
        return self._op.get_model_cache_key()

    def get_cache_id(self, id_value: Any) -> str:
        return self._op.get_cache_id(id_value)

    def get_cache_key(self, id_value: Any) -> str:
        return self._op.get_cache_key(id_value)

    @staticmethod
    def cache_key_for(method: str, args: Mapping[str, Any] | None = None) -> str:
        id_data = [method]

        if args:
            id_data.append(calculate_digest(args))
        else:
            id_data.append('_')

        return ':'.join(id_data)

    async def put(
        self,
        method: str,
        args: Mapping[str, Any] | None = None,
        data: Any | None = None,
        cache_key: str | None = None,
        ttl: timedelta | None = None,
        **kwargs,
    ) -> bool:
        cache_key = cache_key or self.cache_key_for(method, args)
        data = CacheData(cache_id=cache_key, data=data)
        return await self._op.cache_one(data, ttl=ttl or self._ttl, **kwargs)

    async def get(
        self,
        method: str,
        args: Mapping[str, Any] | None = None,
        cache_key: str | None = None,
        **kwargs,
    ) -> tuple[bool, Any | None]:
        cache_key = cache_key or self.cache_key_for(method, args)
        exists, data = await self._op.load_one(self.get_cache_key(cache_key), **kwargs)
        return exists, data

    async def drop(
        self, method: str, args: Mapping[str, Any] | None = None, cache_key: str | None = None
    ) -> bool:
        cache_key = cache_key or self.cache_key_for(method, args)
        return await self._op.drop_one(self.get_cache_key(cache_key))

    async def drop_all(self, methods: Sequence[str] | None = None) -> int:
        methods = methods if methods else list()
        if not methods:
            return await self._op.drop_all()
        results = await asyncio.gather(*(self._op.drop_all(method) for method in methods))
        return reduce(operator.add, results, 0)
