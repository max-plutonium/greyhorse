from collections import OrderedDict, defaultdict
from collections.abc import Callable, Iterable
from functools import partial
from types import AsyncGeneratorType, GeneratorType

import networkx as nx

from greyhorse.error import Error, ErrorCase
from greyhorse.result import Err, Ok, Result
from greyhorse.utils.invoke import invoke_sync

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
from ..abc.services import ResourceMember, Service
from ..boxes import (
    AsyncFactoryGenBox,
    AsyncForwardGenBox,
    AsyncMutGenBox,
    AsyncSharedGenBox,
    SyncFactoryGenBox,
    SyncForwardGenBox,
    SyncMutGenBox,
    SyncSharedGenBox,
)
from . import Container
from .injection import _invoke_target
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
        self._operator_map: dict[type, dict[Controller, OperatorMember]] = defaultdict(dict)
        self._provided_resources = OrderedDict[Operator, SyncResourceMapper]()
        self._public_operators: list[Operator] = []

    def get_operators(self) -> Iterable[Operator]:
        return self._public_operators.copy()

    def add_service(self, service: Service) -> bool:
        if self._services.count(service):
            return False
        self._services.append(service)
        service.inspect(partial(self._add_service_resource, service))
        return True

    def remove_service(self, service: Service) -> bool:
        if not self._services.count(service):
            return False
        service.inspect(partial(self._remove_service_resource, service))
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

    def setup(self) -> Result[None, ResourceError]:
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
            if not self.setup_operator(op):
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

        self._public_operators = []
        self._deps.clear()
        self._resource_graph.clear()
        assert len(self._provided_resources) == 0
        return Ok()

    @staticmethod
    def _invoke_member(
        container: Container, member: ResourceMember, fn: Callable[[], object], _: object
    ) -> object:
        factory = partial(_invoke_target, fn, member.params, container) if member.params else fn

        if issubclass(member.resource_type, Provider):
            prov = None

            match invoke_sync(factory):
                case Ok(prov) | (Provider() as prov):
                    pass

                case GeneratorType() as gen:
                    if issubclass(member.resource_type, SharedProvider):
                        prov = SyncSharedGenBox[member.resource_type.__wrapped_type__](factory)
                    elif issubclass(member.resource_type, MutProvider):
                        prov = SyncMutGenBox[member.resource_type.__wrapped_type__](factory)
                    elif issubclass(member.resource_type, FactoryProvider):
                        prov = SyncFactoryGenBox[member.resource_type.__wrapped_type__](factory)
                    elif issubclass(member.resource_type, ForwardProvider):
                        prov = SyncForwardGenBox[member.resource_type.__wrapped_type__](gen)

                case AsyncGeneratorType() as gen:
                    if issubclass(member.resource_type, SharedProvider):
                        prov = AsyncSharedGenBox[member.resource_type.__wrapped_type__](factory)
                    elif issubclass(member.resource_type, MutProvider):
                        prov = AsyncMutGenBox[member.resource_type.__wrapped_type__](factory)
                    elif issubclass(member.resource_type, FactoryProvider):
                        prov = AsyncFactoryGenBox[member.resource_type.__wrapped_type__](
                            factory
                        )
                    elif issubclass(member.resource_type, ForwardProvider):
                        prov = AsyncForwardGenBox[member.resource_type.__wrapped_type__](gen)

                case _:
                    raise AssertionError(
                        'Unexpected return value returned from provider method'
                    )

            return prov

        return factory()

    def install_container(self, container: Container) -> bool:
        result = True

        for resource_type, node_data in self._resource_graph.nodes(data=True):
            if 'member' not in node_data:
                continue

            member: ResourceMember = node_data['member']
            fn = partial(self._invoke_member, container, member, node_data['factory'])
            registry = container.child_registry(member.lifetime).unwrap_or(container.registry)
            result &= registry.add_factory(resource_type, fn, cache=member.cache)

        return result

    def setup_operator[T](
        self,
        operator: Operator[T],
        container: Container | None = None,
        providers: Selector[type[Provider], Provider] | None = None,
    ) -> Result[bool, ResourceError]:
        res_type = operator.wrapped_type
        prov_type = None

        if operator in self._provided_resources:
            return Ok(False)

        if issubclass(res_type, Provider):
            prov_type = res_type
        else:
            found = False

            candidates = (
                SharedProvider[res_type],
                ForwardProvider[res_type],
                FactoryProvider[res_type],
                MutProvider[res_type],
            )

            for prov_type in candidates:
                if self._resource_graph.has_node(prov_type) or (
                    providers.has(prov_type) if providers is not None else False
                ):
                    found = True
                    break

            if not found:
                return ResourceError.NoSuchResource(resource=res_type.__name__).to_result()

        prov = container.get(prov_type).unwrap_or_none() if container is not None else None
        if prov is None:
            prov = providers.get(prov_type).unwrap_or_none() if providers is not None else None
        if prov is None:
            return ResourceError.NoSuchResource(resource=res_type.__name__).to_result()

        mapper = SyncResourceMapper[prov_type](prov, operator)

        if res := mapper.setup():
            self._provided_resources[operator] = mapper

        return res.map(lambda _: True).map_err(lambda e: ResourceError.Provision(details=e))

    def teardown_operator[T](self, operator: Operator[T]) -> Result[bool, ResourceError]:
        if not (mapper := self._provided_resources.get(operator)):
            return Ok(False)

        if res := mapper.teardown():
            del self._provided_resources[operator]

        return res.map(lambda _: True).map_err(lambda e: ResourceError.Provision(details=e))

    def _add_service_resource(self, service: Service, member: ResourceMember) -> None:
        if self._resource_graph.has_node(member.resource_type):
            return

        self._resource_graph.add_node(
            member.resource_type, factory=partial(member.method, self=service), member=member
        )

        for param_type in member.params.values():
            if not self._resource_graph.has_node(param_type):
                self._deps.add(param_type)

            self._resource_graph.add_edge(member.resource_type, param_type)

    def _remove_service_resource(self, _: Service, member: ResourceMember) -> None:
        if not self._resource_graph.has_node(member.resource_type):
            return

        self._resource_graph.remove_node(member.resource_type)

        for param_type in member.params.values():
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
