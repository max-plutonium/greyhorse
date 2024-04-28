import asyncio
import threading
from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Mapping, TYPE_CHECKING, cast, override

from greyhorse.result import Result
from .deps import DepsProvider
from .operator import OperatorFactoryFn, OperatorFactoryRegistry, OperatorKey
from .providers import ProviderFactoryFn, ProviderFactoryRegistry, ProviderKey
from ..errors import NoOpFoundForPattern, NoProvFoundForPattern, OpPolicyViolation, ProvPolicyViolation
from ..utils.registry import DictRegistry, KeyMapping
from ...i18n import tr
from ...logging import logger

if TYPE_CHECKING:
    from ..schemas.service import ProviderMappingPolicy
    from ..schemas.controller import OperatorMappingPolicy

type ServiceKey = type[Service]
type ServiceFactoryFn = Callable[[...], Result[Service]]
type ServiceFactoryMapping = Mapping[ServiceKey, ServiceFactoryFn]


class Service(ABC):
    def __init__(
        self, name: str, deps_provider: DepsProvider | None = None,
    ):
        self._name = name
        self._deps_provider = deps_provider
        self._op_factories = DictRegistry[OperatorKey, OperatorFactoryFn]()
        self._provider_factories = DictRegistry[ProviderKey, ProviderFactoryFn]()

    @property
    def name(self) -> str:
        return self._name

    @property
    @abstractmethod
    def active(self) -> bool:
        ...

    def set_deps_provider(self, instance: DepsProvider):
        self._deps_provider = instance

    def reset_deps_provider(self):
        self._deps_provider = None

    def get_operator_factory(self, key: OperatorKey, name: str | None = None) -> OperatorFactoryFn | None:
        if not self._deps_provider:
            return None
        return self._deps_provider.get_operator_factory(key, name=name)

    def get_provider_factory(self, key: ProviderKey, name: str | None = None) -> ProviderFactoryFn | None:
        if not self._deps_provider:
            return None
        return self._deps_provider.get_provider_factory(key, name=name)

    def get_resource[T](self, key: type, name: str | None = None) -> T | None:
        if not self._deps_provider:
            return None
        if instance := self._deps_provider.get_resource(key, name=name):
            return cast(T, instance)
        return None

    @property
    def provider_factories(self) -> ProviderFactoryRegistry:
        return self._provider_factories

    @property
    def operator_factories(self) -> OperatorFactoryRegistry:
        return self._op_factories

    def create(self) -> Awaitable[Result] | Result:
        return Result.from_ok()

    def destroy(self) -> Awaitable[Result] | Result:
        return Result.from_ok()

    def start(self) -> Awaitable[None] | None:
        pass

    def stop(self) -> Awaitable[None] | None:
        pass

    @abstractmethod
    def wait(self) -> threading.Event | asyncio.Event:
        ...

    def check_operator_mapping(
        self, policies: list['OperatorMappingPolicy'],
    ) -> Result[Mapping[OperatorKey, KeyMapping[OperatorKey]]]:
        policies_dict = {p.key: p for p in policies}
        key_mapping = {}

        for key in self._op_factories.list_keys():
            if key not in policies_dict:
                error = OpPolicyViolation(type='service', name=self.name, key=str(key.__name__))
                logger.error(error.message)
                return Result.from_error(error)

            name_pattern = policies_dict[key].name_pattern

            if name_pattern is None:
                key_mapping[key] = KeyMapping[OperatorKey](map_to=policies_dict[key].map_to)
                policies_dict.pop(key)
                continue

            names = []

            for name in self._op_factories.get_names(key):
                if name_pattern.match(name):
                    names.append(name)

            if not names:
                error = NoOpFoundForPattern(
                    type='service', name=self.name, key=str(key.__name__), pattern=name_pattern,
                )
                logger.error(error.message)
                return Result.from_error(error)

            key_mapping[key] = KeyMapping[OperatorKey](map_to=policies_dict[key].map_to, names=names)
            policies_dict.pop(key)

        for p in policies_dict.values():
            logger.warn(tr('app.entities.operator-unused-policy').format(
                type='service', name=self.name, key=str(p.key.__name__), pattern=p.name_pattern or '-',
            ))

        return Result.from_ok(key_mapping)

    def check_provider_mapping(
        self, policies: list['ProviderMappingPolicy'],
    ) -> Result[Mapping[ProviderKey, KeyMapping[ProviderKey]]]:
        policies_dict = {p.key: p for p in policies}
        key_mapping = {}

        for key in self._provider_factories.list_keys():
            if key not in policies_dict:
                error = ProvPolicyViolation(type='service', name=self.name, key=str(key.__name__))
                logger.error(error.message)
                return Result.from_error(error)

            name_pattern = policies_dict[key].name_pattern

            if name_pattern is None:
                key_mapping[key] = KeyMapping[ProviderKey](map_to=key)
                policies_dict.pop(key)
                continue

            names = []

            for name in self._provider_factories.get_names(key):
                if name_pattern.match(name):
                    names.append(name)

            if not names:
                error = NoProvFoundForPattern(
                    type='service', name=self.name, key=str(key.__name__), pattern=name_pattern,
                )
                logger.error(error.message)
                return Result.from_error(error)

            key_mapping[key] = KeyMapping[ProviderKey](map_to=key, names=names)
            policies_dict.pop(key)

        for p in policies_dict.values():
            logger.warn(tr('app.entities.provider-unused-policy').format(
                type='service', name=self.name, key=str(p.key.__name__), pattern=p.name_pattern or '-',
            ))

        return Result.from_ok(key_mapping)


class SyncService(Service, ABC):
    def __init__(self, name: str):
        super().__init__(name)
        self._event = threading.Event()

    @property
    def active(self) -> bool:
        return not self._event.is_set()

    @override
    def create(self) -> Result:
        return Result.from_ok()

    @override
    def destroy(self) -> Result:
        return Result.from_ok()

    @override
    def start(self) -> None:
        self._event.clear()

    @override
    def stop(self) -> None:
        self._event.set()

    @override
    def wait(self) -> threading.Event:
        return self._event


class AsyncService(Service, ABC):
    def __init__(self, name: str):
        super().__init__(name)
        self._event = asyncio.Event()

    @property
    def active(self) -> bool:
        return not self._event.is_set()

    @override
    async def create(self) -> Result:
        return Result.from_ok()

    @override
    async def destroy(self) -> Result:
        return Result.from_ok()

    @override
    async def start(self) -> None:
        self._event.clear()

    @override
    async def stop(self) -> None:
        self._event.set()

    @override
    def wait(self) -> asyncio.Event:
        return self._event
