from abc import ABC, abstractmethod
from typing import Awaitable, override, TypeVar

from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import Provider, SharedProvider, MutProvider, FactoryProvider, ForwardProvider
from greyhorse.result import Result
from greyhorse.utils.types import TypeWrapper


class ResourceMapper[T](TypeWrapper[T], ABC):
    __slots__ = ('_provider', '_operator', '_methods')

    def __init__(self, provider: Provider[T], operator: Operator[T]):
        self._provider = provider
        self._operator = operator

    def __class_getitem__(cls, provider_type: type[Provider]):
        if isinstance(provider_type, TypeVar):
            # noinspection PyUnresolvedReferences
            return super(TypeWrapper, cls).__class_getitem__(provider_type)

        class_ = super(ResourceMapper, cls).__class_getitem__(provider_type.__wrapped_type__)
        setattr(class_, '_methods', cls._get_provider_methods(provider_type))
        return class_

    @staticmethod
    def _get_provider_methods(provider_type: type[Provider]):
        if issubclass(provider_type, SharedProvider):
            return 'borrow', 'reclaim'
        elif issubclass(provider_type, MutProvider):
            return 'acquire', 'release'
        elif issubclass(provider_type, FactoryProvider):
            return 'create', 'destroy'
        elif issubclass(provider_type, ForwardProvider):
            return 'take', 'drop'

    @abstractmethod
    def setup(self) -> Result[bool, str] | Awaitable[Result[bool, str]]:
        ...

    @abstractmethod
    def teardown(self) -> Result[bool, str] | Awaitable[Result[bool, str]]:
        ...


class SyncResourceMapper[T](ResourceMapper[T]):
    @override
    def setup(self) -> Result[bool, str]:
        init_method = getattr(self._provider, self._methods[0])
        return init_method().map_err(lambda e: e.message).map(self._operator.accept)

    @override
    def teardown(self) -> Result[bool, str]:
        fini_method = getattr(self._provider, self._methods[1])
        return self._operator.revoke().map(fini_method) \
            .ok_or(f'Could not revoke resource "{self.__wrapped_type__.__name__}"').map(lambda _: True)


class AsyncResourceMapper[T](ResourceMapper[T]):
    @override
    async def setup(self) -> Result[bool, str]:
        init_method = getattr(self._provider, self._methods[0])
        return await (await init_method()).map_err(lambda e: e.message).map_async(self._operator.accept)

    @override
    async def teardown(self) -> Result[bool, str]:
        fini_method = getattr(self._provider, self._methods[1])
        return (await (await self._operator.revoke()).map_async(fini_method)) \
            .ok_or(f'Could not revoke resource "{self.__wrapped_type__.__name__}"').map(lambda _: True)
