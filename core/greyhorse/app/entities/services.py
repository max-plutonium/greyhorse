import asyncio
import inspect
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from functools import partial
from typing import override, Any

from greyhorse.result import Result, Ok, Err
from ..abc.collectors import Collector, MutCollector
from ..abc.operators import Operator
from ..abc.providers import Provider
from ..abc.selectors import ListSelector
from ..abc.services import Service, ServiceWaiter, ServiceState, ServiceError, ProvisionError
from ..private.mappers import SyncResourceMapper, AsyncResourceMapper
from ...utils.invoke import invoke_sync, invoke_async


@dataclass(slots=True, frozen=True)
class _ProviderMember:
    class_name: str
    method_name: str
    resource_type: type
    provider_type: type[Provider]
    method: classmethod
    params: dict[str, inspect.Parameter] = field(default_factory=dict)


def _is_provider_member(member: Any) -> bool:
    return isinstance(member, _ProviderMember)


def provider(provider_type: type[Provider]):
    def decorator(func: classmethod):
        class_name, method_name = func.__qualname__.split('.')
        sig = inspect.signature(func)
        params = {k: v for k, v in sig.parameters.items() if k != 'self'}

        return _ProviderMember(
            class_name, method_name,
            provider_type.__wrapped_type__,
            provider_type, func, params,
        )

    return decorator


class SyncService(Service):
    def __init__(self, providers: list[type[Provider]] | None = None):
        super().__init__()
        self._public_providers = providers or []
        self._providers: dict[type, list[type[Provider]]] = defaultdict(list)
        self._provider_members: dict[type[Provider], _ProviderMember] = {}
        self._provided_resources: dict[type, dict[Operator, SyncResourceMapper]] = defaultdict(dict)
        self._provided_providers: dict[type[Provider], Provider] = {}
        self._waiter = threading.Event()
        self._init_provider_members()

    def _init_provider_members(self):
        provider_members = inspect.getmembers(self, _is_provider_member)

        for name, member in provider_members:  # type: str, _ProviderMember
            self._providers[member.resource_type].append(member.provider_type)
            self._provider_members[member.provider_type] = member
            setattr(self, name, partial(member.method, self))

    @override
    @property
    def waiter(self) -> ServiceWaiter:
        return ServiceWaiter.Sync(self._waiter)

    @override
    def setup(
        self, selector: ListSelector[type, Operator],
        collector: Collector[type[Provider], Provider],
    ) -> Result[ServiceState, ServiceError]:
        if self.state == ServiceState.Active:
            return Ok(self.state)

        for prov_type in self._public_providers:
            res_type = prov_type.__wrapped_type__

            for _, operator in selector.items(lambda t: issubclass(t, res_type)):
                res = self.setup_resource(prov_type, operator) \
                    .map_err(lambda e: ServiceError.AutoProvision(details=e.message))
                if not res:
                    return res

        for prov_type, member in self._provider_members.items():
            if len(member.params) > 0:
                continue

            # noinspection PyTypeChecker
            match invoke_sync(member.method, self):
                case Ok(prov) | (Provider() as prov):
                    if collector.add(prov_type, prov):
                        self._provided_providers[prov_type] = prov

                case Err(e):
                    return ServiceError.Collect(details=e.message).to_result()

        self._switch_to_active()
        return Ok(self.state)

    @override
    def teardown(
        self, selector: ListSelector[type, Operator],
        collector: MutCollector[type[Provider], Provider],
    ) -> Result[ServiceState, ServiceError]:
        if self.state == ServiceState.Idle:
            return Ok(self.state)

        for prov_type in reversed(self._public_providers):
            res_type = prov_type.__wrapped_type__

            for _, operator in selector.items(lambda t: issubclass(t, res_type)):
                res = self.teardown_resource(prov_type, operator) \
                    .map_err(lambda e: ServiceError.AutoProvision(details=e.message))
                if not res:
                    return res

        provs_to_remove = []

        for prov_type, prov in reversed(self._provided_providers.items()):
            if collector.remove(prov_type, prov):
                provs_to_remove.append(prov_type)
            else:
                # TODO logger warn
                pass

        for prov_type in provs_to_remove:
            del self._provided_providers[prov_type]

        self._switch_to_idle()
        return Ok(self.state)

    @override
    def can_provide(self, resource_type: type) -> bool:
        if resource_type not in self._providers:
            return False
        return len(self._providers[resource_type]) > 0

    @override
    def get_resource_types(self) -> list[type]:
        return list(self._providers.keys())

    @override
    def get_provider_types(self, resource_type: type) -> list[type[Provider]]:
        if resource_type not in self._providers:
            return []
        return self._providers[resource_type].copy()

    @override
    def setup_resource(
        self, prov_type: type[Provider], operator: Operator, *args, **kwargs,
    ) -> Result[None, ProvisionError]:
        if not (member := self._provider_members.get(prov_type)):
            return ProvisionError.NoSuchProvider(type_=prov_type.__name__).to_result()
        if operator in self._provided_resources[prov_type.__wrapped_type__]:
            return Ok(None)

        # noinspection PyTypeChecker
        match invoke_sync(member.method, self, *args, **kwargs):
            case Ok(prov) | (Provider() as prov):
                mapper = SyncResourceMapper[prov_type](prov, operator)

                if res := mapper.setup().map_err(lambda e: ProvisionError.Provision(details=e)):
                    self._provided_resources[prov_type.__wrapped_type__][operator] = mapper
                return res

            case Err(e):
                return e

    @override
    def teardown_resource(
        self, prov_type: type[Provider], operator: Operator,
    ) -> Result[None, ProvisionError]:
        if not (mappers := self._provided_resources.get(prov_type.__wrapped_type__)):
            return Ok(None)
        if not (mapper := mappers.get(operator)):
            return Ok(None)

        if res := mapper.teardown().map_err(lambda e: ProvisionError.Provision(details=e)):
            del mappers[operator]
        return res

    @override
    def _switch_to_idle(self):
        self._state = ServiceState.Idle

    @override
    def _switch_to_active(self, started: bool = False):
        if started:
            self._waiter.clear()
        else:
            self._waiter.set()

        self._state = ServiceState.Active(started=not self._waiter.is_set())


class AsyncService(Service):
    def __init__(self, providers: list[type[Provider]] | None = None):
        super().__init__()
        self._public_providers = providers or []
        self._providers: dict[type, list[type[Provider]]] = defaultdict(list)
        self._provider_members: dict[type[Provider], _ProviderMember] = {}
        self._provided_resources: dict[type, dict[Operator, AsyncResourceMapper]] = defaultdict(dict)
        self._provided_providers: dict[type[Provider], Provider] = {}
        self._waiter = asyncio.Event()
        self._init_provider_members()

    def _init_provider_members(self):
        provider_members = inspect.getmembers(self, _is_provider_member)

        for name, member in provider_members:  # type: str, _ProviderMember
            self._providers[member.resource_type].append(member.provider_type)
            self._provider_members[member.provider_type] = member
            setattr(self, name, partial(member.method, self))

    @override
    @property
    def waiter(self) -> ServiceWaiter:
        return ServiceWaiter.Async(self._waiter)

    @override
    async def setup(
        self, selector: ListSelector[type, Operator],
        collector: Collector[type[Provider], Provider],
    ) -> Result[ServiceState, ServiceError]:
        if self.state == ServiceState.Active:
            return Ok(self.state)

        for prov_type in self._public_providers:
            res_type = prov_type.__wrapped_type__

            for _, operator in selector.items(lambda t: issubclass(t, res_type)):
                res = (await self.setup_resource(prov_type, operator)) \
                    .map_err(lambda e: ServiceError.AutoProvision(details=e.message))
                if not res:
                    return res

        for prov_type, member in self._provider_members.items():
            if len(member.params) > 0:
                continue

            # noinspection PyTypeChecker
            match await invoke_async(member.method, self):
                case Ok(prov) | (Provider() as prov):
                    if collector.add(prov_type, prov):
                        self._provided_providers[prov_type] = prov

                case Err(e):
                    return ServiceError.Collect(details=e.message).to_result()

        await self._switch_to_active()
        return Ok(self.state)

    @override
    async def teardown(
        self, selector: ListSelector[type, Operator],
        collector: MutCollector[type[Provider], Provider],
    ) -> Result[ServiceState, ServiceError]:
        if self.state == ServiceState.Idle:
            return Ok(self.state)

        for prov_type in reversed(self._public_providers):
            res_type = prov_type.__wrapped_type__

            for _, operator in selector.items(lambda t: issubclass(t, res_type)):
                res = (await self.teardown_resource(prov_type, operator)) \
                    .map_err(lambda e: ServiceError.AutoProvision(details=e.message))
                if not res:
                    return res

        provs_to_remove = []

        for prov_type, prov in reversed(self._provided_providers.items()):
            if collector.remove(prov_type, prov):
                provs_to_remove.append(prov_type)
            else:
                # TODO logger warn
                pass

        for prov_type in provs_to_remove:
            del self._provided_providers[prov_type]

        await self._switch_to_idle()
        return Ok(self.state)

    @override
    def can_provide(self, resource_type: type) -> bool:
        if resource_type not in self._providers:
            return False
        return len(self._providers[resource_type]) > 0

    @override
    def get_resource_types(self) -> list[type]:
        return list(self._providers.keys())

    @override
    def get_provider_types(self, resource_type: type) -> list[type[Provider]]:
        if resource_type not in self._providers:
            return []
        return self._providers[resource_type].copy()

    @override
    async def setup_resource(
        self, prov_type: type[Provider], operator: Operator, *args, **kwargs,
    ) -> Result[None, ProvisionError]:
        if not (member := self._provider_members.get(prov_type)):
            return ProvisionError.NoSuchProvider(type_=prov_type.__name__).to_result()
        if operator in self._provided_resources[prov_type.__wrapped_type__]:
            return Ok(None)

        # noinspection PyTypeChecker
        match await invoke_async(member.method, self, *args, **kwargs):
            case Ok(prov) | (Provider() as prov):
                mapper = AsyncResourceMapper[prov_type](prov, operator)

                if res := (await mapper.setup()).map_err(lambda e: ProvisionError.Provision(details=e)):
                    self._provided_resources[prov_type.__wrapped_type__][operator] = mapper
                return res

            case Err(e):
                return e

    @override
    async def teardown_resource(
        self, prov_type: type[Provider], operator: Operator,
    ) -> Result[None, ProvisionError]:
        if not (mappers := self._provided_resources.get(prov_type.__wrapped_type__)):
            return Ok(None)
        if not (mapper := mappers.get(operator)):
            return Ok(None)

        if res := (await mapper.teardown()).map_err(lambda e: ProvisionError.Provision(details=e)):
            del mappers[operator]
        return res

    @override
    async def _switch_to_idle(self):
        self._state = ServiceState.Idle

    @override
    async def _switch_to_active(self, started: bool = False):
        if started:
            self._waiter.clear()
        else:
            self._waiter.set()

        self._state = ServiceState.Active(started=not self._waiter.is_set())
