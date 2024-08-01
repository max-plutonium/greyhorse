from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import Provider
from greyhorse.app.abc.selectors import Selector
from greyhorse.app.abc.services import Service, ServiceState
from greyhorse.app.registries import MutResourceRegistry
from greyhorse.app.schemas.component import ComponentConf
from greyhorse.enum import Enum, Unit, Struct
from greyhorse.maybe import Maybe, Nothing
from greyhorse.result import Ok, Err


class ComponentState(Enum):
    Idle = Unit()
    Partial = Struct(count=int, errors=list[str])
    Error = Struct(errors=list[str])
    Ready = Unit()


class Component:
    def __init__(
        self, name: str, conf: ComponentConf, path: str,
        services: list[tuple[str, Service]],
    ):
        self._name = name
        self._conf = conf
        self._path = path
        self._service_names: dict[str, Service] = {k: v for (k, v) in services}
        self._service_types: dict[type[Service], Service] = {type(v): v for (_, v) in services}
        self._providers = MutResourceRegistry[Provider]()
        self._operators = MutResourceRegistry[Operator]()

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> str:
        return self._path

    def get_service(self, key: str | type) -> Maybe[Service]:
        match key:
            case str():
                return Maybe(self._service_names.get(key))
            case type():
                return Maybe(self._service_types.get(key))
        return Nothing

    def get_providers(self) -> Selector[Provider]:
        return self._providers

    def get_operators(self) -> Selector[Operator]:
        return self._operators

    def setup(self) -> ComponentState:
        count = 0
        errors = []

        for svc in self._service_types.values():
            match svc.setup(self._providers, self._operators):
                case Ok(state):
                    if isinstance(state, ServiceState.Active):
                        count += 1

                case Err(e):
                    errors.append(e.message)

        if not errors:
            return ComponentState.Ready
        elif count > 0:
            return ComponentState.Partial(count=count, errors=errors)
        else:
            return ComponentState.Error(errors=errors)

    def teardown(self) -> ComponentState:
        count = 0
        errors = []

        for svc in reversed(self._service_types.values()):
            match svc.teardown(self._providers, self._operators):
                case Ok(state):
                    if state == ServiceState.Idle:
                        count += 1

                case Err(e):
                    errors.append(e.message)

        if not errors:
            return ComponentState.Idle
        elif count > 0:
            return ComponentState.Partial(count=count, errors=errors)
        else:
            return ComponentState.Error(errors=errors)
