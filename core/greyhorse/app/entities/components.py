from greyhorse.app.abc.collectors import Collector, MutCollector
from greyhorse.app.abc.controllers import Controller
from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import Provider
from greyhorse.app.abc.selectors import Selector, ListSelector
from greyhorse.app.abc.services import Service, ServiceState
from greyhorse.app.registries import MutDictRegistry
from greyhorse.app.schemas.component import ComponentConf
from greyhorse.enum import Enum, Unit, Struct
from greyhorse.maybe import Maybe


class ComponentState(Enum):
    Idle = Unit()
    Partial = Struct(count=int, errors=list[str])
    Error = Struct(errors=list[str])
    Ready = Unit()


class Component:
    def __init__(
        self, name: str, conf: ComponentConf, path: str,
        controllers: list[Controller], services: list[Service],
    ):
        self._name = name
        self._conf = conf
        self._path = path

        self._controllers: list[Controller] = controllers
        self._services: dict[type[Service], Service] = {type(s): s for s in services}

        self._operator_reg = MutDictRegistry[type, Operator]()

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> str:
        return self._path

    def get_service[T: Service](self, type_: type[T]) -> Maybe[T]:
        return Maybe(self._services.get(type_))

    def setup(
        self,
        prov_selector: Selector[type[Provider], Provider],
        prov_collector: Collector[type[Provider], Provider],
        op_selector: ListSelector[type, Operator],
    ) -> ComponentState:
        count = 0
        errors = []

        for op_conf in self._conf.operators:
            for _, operator in op_selector.items(lambda t: t == op_conf.resource):
                self._operator_reg.add(op_conf.resource, operator)

        for ctrl in self._controllers:
            if ctrl.setup(prov_selector, self._operator_reg) \
                    .map_err(lambda e: errors.append(e.message)) \
                    .unwrap_or(False):
                count += 1

        for svc in self._services.values():
            if svc.setup(self._operator_reg, prov_collector).map_err(
                lambda e: errors.append(e.message)
            ).map(lambda s: isinstance(s, ServiceState.Active)):
                count += 1

        if not errors:
            return ComponentState.Ready
        elif count > 0:
            return ComponentState.Partial(count=count, errors=errors)
        else:
            return ComponentState.Error(errors=errors)

    def teardown(
        self,
        prov_selector: Selector[type[Provider], Provider],
        prov_collector: MutCollector[type[Provider], Provider],
        op_selector: ListSelector[type, Operator],
    ) -> ComponentState:
        count = 0
        errors = []

        for svc in reversed(self._services.values()):
            if svc.teardown(self._operator_reg, prov_collector).map_err(
                lambda e: errors.append(e.message)
            ).map(lambda s: s == ServiceState.Idle):
                count += 1

        for ctrl in reversed(self._controllers):
            if ctrl.teardown(prov_selector, self._operator_reg) \
                    .map_err(lambda e: errors.append(e.message)) \
                    .unwrap_or(False):
                count += 1

        for op_conf in reversed(self._conf.operators):
            for _, operator in op_selector.items(lambda t: t == op_conf.resource):
                self._operator_reg.remove(op_conf.resource, operator)

        if not errors:
            return ComponentState.Ready
        elif count > 0:
            return ComponentState.Partial(count=count, errors=errors)
        else:
            return ComponentState.Error(errors=errors)
