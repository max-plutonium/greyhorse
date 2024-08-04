import asyncio
import inspect
import threading
from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from typing import override, Any

from greyhorse.result import Result, Ok
from ..abc.operators import Operator
from ..abc.providers import Provider
from ..abc.selectors import ListSelector
from ..abc.services import Service, ServiceWaiter, ServiceState, ServiceError, ResourceProvisionError
from ..private.mappers import ProvidedResourceMapper
from ...utils.invoke import invoke_sync


@dataclass(slots=True, frozen=True)
class _ProviderMember:
    class_name: str
    method_name: str
    resource_type: type
    provider_type: type[Provider]
    method: classmethod


def _is_provider_member(member: Any) -> bool:
    return isinstance(member, _ProviderMember)


def provider(provider_type: type[Provider]):
    def decorator(func: classmethod):
        class_name, method_name = func.__qualname__.split('.')
        return _ProviderMember(
            class_name, method_name,
            provider_type.__wrapped_type__,
            provider_type, func,
        )

    return decorator


class SyncService(Service):
    def __init__(self, *args, **kwargs):
        super(SyncService, self).__init__(*args, **kwargs)
        self._providers: dict[type, list[type[Provider]]] = defaultdict(list)
        self._provider_members: dict[type[Provider], _ProviderMember] = {}
        self._provided_resources: dict[type, dict[Operator, ProvidedResourceMapper]] = defaultdict(dict)
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
    ) -> Result[ServiceState, ServiceError]:
        if self.state == ServiceState.Active:
            return Ok(self.state)
        return self._switch_to_active()

    @override
    def teardown(
        self, selector: ListSelector[type, Operator],
    ) -> Result[ServiceState, ServiceError]:
        if self.state == ServiceState.Idle:
            return Ok(self.state)
        return self._switch_to_idle()

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
    def setup_resource[T](
        self, prov_type: type[Provider[T]], operator: Operator[T], *args, **kwargs,
    ) -> Result[bool, ResourceProvisionError]:
        if not (member := self._provider_members.get(prov_type)):
            return ResourceProvisionError.NoSuchProvider(type_=prov_type.__name__).to_result()

        # noinspection PyTypeChecker
        res = invoke_sync(member.method, self, *args, **kwargs)
        assert isinstance(res, Result)

        if not res:
            return res

        return res.and_then(
            partial(self._apply_provision, prov_type=prov_type, operator=operator)
        ).map_err(lambda e: ResourceProvisionError.Provision(details=e))

    @override
    def teardown_resource[T](
        self, prov_type: type[Provider], operator: Operator[T],
    ) -> Result[bool, ResourceProvisionError]:
        return self._cancel_provision(prov_type, operator) \
            .map_err(lambda e: ResourceProvisionError.Provision(details=e))

    @override
    def _switch_to_active(self, started: bool = False) -> Result[ServiceState, ServiceError]:
        if started:
            self._waiter.clear()
        else:
            self._waiter.set()

        self._state = ServiceState.Active(started=not self._waiter.is_set())
        return Ok(self._state)

    def _apply_provision[T](
        self, provider: Provider[T], prov_type: type[Provider], operator: Operator[T],
    ) -> Result[bool, str]:
        if prov_type not in self._provider_members:
            return Ok(False)
        if operator in self._provided_resources[prov_type.__wrapped_type__]:
            return Ok(True)

        mapper = ProvidedResourceMapper[prov_type](provider, operator)
        if (res := mapper.setup()) and res.unwrap():
            self._provided_resources[prov_type.__wrapped_type__][operator] = mapper
        return res

    def _cancel_provision[T](
        self, prov_type: type[Provider], operator: Operator[T],
    ) -> Result[bool, str]:
        if not (mappers := self._provided_resources.get(prov_type.__wrapped_type__)):
            return Ok(False)
        if not (mapper := mappers.get(operator)):
            return Ok(False)

        if (res := mapper.teardown()) and res.unwrap():
            del mappers[operator]
        return res


class AsyncService(Service):
    def __init__(self, *args, **kwargs):
        super(AsyncService, self).__init__(*args, **kwargs)
        self._providers: dict[type, list[type[Provider]]] = defaultdict(list)
        self._provider_members: dict[type[Provider], _ProviderMember] = {}
        self._provided_resources: dict[type, dict[Operator, ProvidedResourceMapper]] = defaultdict(dict)
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
    ) -> Result[ServiceState, ServiceError]:
        if self.state == ServiceState.Active:
            return Ok(self.state)
        return self._switch_to_active()

    @override
    async def teardown(
        self, selector: ListSelector[type, Operator],
    ) -> Result[ServiceState, ServiceError]:
        if self.state == ServiceState.Idle:
            return Ok(self.state)
        return self._switch_to_idle()

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
    def setup_resource[T](
        self, prov_type: type[Provider[T]], operator: Operator[T], *args, **kwargs,
    ) -> Result[bool, ResourceProvisionError]:
        if not (member := self._provider_members.get(prov_type)):
            return ResourceProvisionError.NoSuchProvider(type_=prov_type.__name__).to_result()

        # noinspection PyTypeChecker
        res = invoke_sync(member.method, self, *args, **kwargs)
        assert isinstance(res, Result)

        if not res:
            return res

        return res.and_then(
            partial(self._apply_provision, prov_type=prov_type, operator=operator)
        ).map_err(lambda e: ResourceProvisionError.Provision(details=e))

    @override
    def teardown_resource[T](
        self, prov_type: type[Provider], operator: Operator[T],
    ) -> Result[bool, ResourceProvisionError]:
        return self._cancel_provision(prov_type, operator) \
            .map_err(lambda e: ResourceProvisionError.Provision(details=e))

    @override
    def _switch_to_active(self, started: bool = False) -> Result[ServiceState, ServiceError]:
        if started:
            self._waiter.clear()
        else:
            self._waiter.set()

        self._state = ServiceState.Active(started=not self._waiter.is_set())
        return Ok(self._state)

    def _apply_provision[T](
        self, provider: Provider[T], prov_type: type[Provider], operator: Operator[T],
    ) -> Result[bool, str]:
        if prov_type not in self._provider_members:
            return Ok(False)
        if operator in self._provided_resources[prov_type.__wrapped_type__]:
            return Ok(True)

        mapper = ProvidedResourceMapper[prov_type](provider, operator)
        if (res := mapper.setup()) and res.unwrap():
            self._provided_resources[prov_type.__wrapped_type__][operator] = mapper
        return res

    def _cancel_provision[T](
        self, prov_type: type[Provider], operator: Operator[T],
    ) -> Result[bool, str]:
        if not (mappers := self._provided_resources.get(prov_type.__wrapped_type__)):
            return Ok(False)
        if not (mapper := mappers.get(operator)):
            return Ok(False)

        if (res := mapper.teardown()) and res.unwrap():
            del mappers[operator]
        return res
