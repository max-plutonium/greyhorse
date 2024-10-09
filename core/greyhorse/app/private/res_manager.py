from collections import OrderedDict, defaultdict
from collections.abc import Iterable
from functools import partial
from types import GeneratorType

import networkx as nx

from ...error import Error, ErrorCase
from ...result import Err, Ok, Result
from ...utils.injectors import ParamsInjector
from ...utils.invoke import invoke_sync
from ..abc.controllers import Controller, OperatorMember
from ..abc.operators import Operator
from ..abc.providers import (
    FactoryProvider,
    ForwardProvider,
    MutProvider,
    Provider,
    SharedProvider,
)
from ..abc.selectors import Selector
from ..abc.services import ProviderMember, Service
from ..boxes import FactoryGenBox, ForwardGenBox, MutGenBox, SharedGenBox
from ..registries import MutDictRegistry
from .mappers import SyncResourceMapper


class ResourceError(Error):
    namespace = 'greyhorse.app'

    Provision = ErrorCase(msg='Resource provision error: "{details}"', details=str)
    NoSuchResource = ErrorCase(msg='No such resource: "{resource}"', resource=str)
    NoSuchDependency = ErrorCase(msg='No such dependency: "{resource}"', resource=str)


class ResourceManager:
    def __init__(self) -> None:
        self._services: list[Service] = []
        self._controllers: list[Controller] = []
        self._deps = set()
        self._resource_graph = nx.DiGraph()
        self._provided_resources = OrderedDict[Operator, SyncResourceMapper]()
        self._cached_providers = MutDictRegistry[type[Provider], Provider]()
        self._res_providers: dict[type, list[type[Provider]]] = defaultdict(list)
        self._operator_map: dict[type, dict[Controller, OperatorMember]] = defaultdict(dict)
        self._public_operators: list[Operator] = []

    def get_operators(self) -> Iterable[Operator]:
        return self._public_operators.copy()

    def add_service(self, service: Service) -> bool:
        if self._services.count(service):
            return False
        self._services.append(service)
        service.inspect(partial(self._add_service_provider, service))
        return True

    def remove_service(self, service: Service) -> bool:
        if not self._services.count(service):
            return False
        service.inspect(partial(self._remove_service_provider, service))
        self._services.remove(service)
        return True

    def add_controller(self, controller: Controller) -> bool:
        if self._controllers.count(controller):
            return False
        self._controllers.append(controller)
        controller.inspect(partial(self._add_ctrl_operator, controller))
        return True

    def remove_controller(self, controller: Controller) -> bool:
        if not self._controllers.count(controller):
            return False
        controller.inspect(partial(self._remove_ctrl_operator, controller))
        self._controllers.remove(controller)
        return True

    def setup(
        self, providers: Selector[type[Provider], Provider] | None = None
    ) -> Result[None, ResourceError]:
        operators = []

        for ctrl_dict in self._operator_map.values():
            for ctrl, operator_member in ctrl_dict.items():
                factory = partial(operator_member.method, self=ctrl)
                match invoke_sync(factory):
                    case Ok(op) | (Operator() as op):
                        operators.append(op)

                    case Err(e):
                        return ResourceError.Provision(details=e).to_result()

                    case _:
                        continue

        for op in operators:
            if not self.setup_resource(op, providers):
                self._public_operators.append(op)

        return Ok()

    def teardown(self) -> Result[None, ResourceError]:
        while operator := next(reversed(self._provided_resources.keys()), None):
            mapper = self._provided_resources[operator]

            if not (
                res := mapper.teardown().map_err(
                    lambda e: ResourceError.Provision(details=e.message)
                )
            ):
                return res

            del self._provided_resources[operator]

        for k, _ in self._cached_providers.items():  # noqa: PERF102
            self._cached_providers.remove(k)

        self._public_operators = []
        self._deps.clear()
        self._resource_graph.clear()
        assert len(self._provided_resources) == 0
        return Ok()

    def find_provider(
        self,
        prov_type: type[Provider],
        providers: Selector[type[Provider], Provider] | None = None,
    ) -> Result[Provider, ResourceError]:
        if (prov := self._cached_providers.get(prov_type).unwrap_or_none()) or (
            prov := providers.get(prov_type).unwrap_or_none() if providers is not None else None
        ):
            return Ok(prov)

        if not self._resource_graph.has_node(prov_type):
            return ResourceError.NoSuchResource(resource=prov_type.__name__).to_result()

        node = self._resource_graph.nodes[prov_type]
        injector = ParamsInjector()

        for dep_type in self._resource_graph.successors(prov_type):
            if prov := self.find_provider(dep_type, providers):
                injector.add_type_provider(dep_type, prov.unwrap())
            else:
                return ResourceError.NoSuchDependency(resource=dep_type.__name__).to_result()

        factory = node['factory']
        injected_args = injector(factory)

        match invoke_sync(factory, *injected_args.args, **injected_args.kwargs):
            case Ok(prov) | (Provider() as prov):
                if not issubclass(prov_type, ForwardProvider):
                    self._cached_providers.add(prov_type, prov)
                return Ok(prov)

            case Err(e):
                return ResourceError.Provision(details=e.message).to_result()

            case None:
                return ResourceError.NoSuchResource(resource=prov_type.__name__).to_result()

            case GeneratorType() as gen:
                if issubclass(prov_type, SharedProvider):
                    prov = SharedGenBox[prov_type.__wrapped_type__](
                        partial(factory, *injected_args.args, **injected_args.kwargs)
                    )
                    self._cached_providers.add(prov_type, prov)
                    return Ok(prov)
                if issubclass(prov_type, MutProvider):
                    prov = MutGenBox[prov_type.__wrapped_type__](
                        partial(factory, *injected_args.args, **injected_args.kwargs)
                    )
                    self._cached_providers.add(prov_type, prov)
                    return Ok(prov)
                if issubclass(prov_type, FactoryProvider):
                    prov = FactoryGenBox[prov_type.__wrapped_type__](
                        partial(factory, *injected_args.args, **injected_args.kwargs)
                    )
                    self._cached_providers.add(prov_type, prov)
                    return Ok(prov)
                if issubclass(prov_type, ForwardProvider):
                    prov = ForwardGenBox[prov_type.__wrapped_type__](gen)
                    return Ok(prov)

        raise AssertionError('Unexpected return value returned from provider method')

    def setup_resource[T](
        self, operator: Operator[T], providers: Selector[type[Provider], Provider] | None = None
    ) -> Result[bool, ResourceError]:
        res_type = operator.wrapped_type
        prov_type = None

        if operator in self._provided_resources:
            return Ok(False)

        if issubclass(res_type, Provider):
            prov_type = res_type
        else:
            found = False

            if res_type in self._res_providers:
                candidates = self._res_providers[res_type]
            else:
                candidates = (
                    SharedProvider[res_type],
                    ForwardProvider[res_type],
                    FactoryProvider[res_type],
                    MutProvider[res_type],
                )

            for prov_type in candidates:
                if (
                    self._resource_graph.has_node(prov_type)
                    or self._cached_providers.has(prov_type)
                    or (providers.has(prov_type) if providers is not None else False)
                ):
                    found = True
                    break

            if not found:
                return ResourceError.NoSuchResource(resource=res_type.__name__).to_result()

        if (prov := self._cached_providers.get(prov_type).unwrap_or_none()) or (
            prov := providers.get(prov_type).unwrap_or_none()
            if providers is not None
            else False
        ):
            mapper = SyncResourceMapper[prov_type](prov, operator)

        else:
            if not (res := self.find_provider(prov_type, providers)):
                return res  # type: ignore

            prov = res.unwrap()
            mapper = SyncResourceMapper[prov_type](prov, operator)

        if res := mapper.setup():
            self._provided_resources[operator] = mapper

        return res.map(lambda _: True).map_err(lambda e: ResourceError.Provision(details=e))

    def teardown_resource[T](self, operator: Operator[T]) -> Result[bool, ResourceError]:
        if not (mapper := self._provided_resources.get(operator)):
            return Ok(False)

        if res := mapper.teardown():
            del self._provided_resources[operator]

        return res.map(lambda _: True).map_err(lambda e: ResourceError.Provision(details=e))

    def _add_service_provider(self, service: Service, provider_member: ProviderMember) -> None:
        if self._resource_graph.has_node(provider_member.provider_type):
            return

        self._res_providers[provider_member.resource_type].append(provider_member.provider_type)

        self._resource_graph.add_node(
            provider_member.provider_type, factory=partial(provider_member.method, self=service)
        )

        for param_type in provider_member.params.values():
            if not self._resource_graph.has_node(param_type):
                self._deps.add(param_type)

            self._resource_graph.add_edge(provider_member.provider_type, param_type)

    def _remove_service_provider(self, _: Service, provider_member: ProviderMember) -> None:
        if not self._resource_graph.has_node(provider_member.provider_type):
            return

        self._res_providers[provider_member.resource_type].remove(provider_member.provider_type)
        self._resource_graph.remove_node(provider_member.provider_type)

        for param_type in provider_member.params.values():
            if not self._resource_graph.has_node(param_type):
                self._deps.remove(param_type)

    def _add_ctrl_operator(
        self, controller: Controller, operator_member: OperatorMember
    ) -> None:
        ctrl_dict = self._operator_map[operator_member.resource_type]

        if controller in ctrl_dict:
            return

        ctrl_dict[controller] = operator_member

    def _remove_ctrl_operator(
        self, controller: Controller, operator_member: OperatorMember
    ) -> None:
        ctrl_dict = self._operator_map[operator_member.resource_type]

        if controller not in ctrl_dict:
            return

        del ctrl_dict[controller]
