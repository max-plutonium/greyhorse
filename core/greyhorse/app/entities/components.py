from typing import TYPE_CHECKING

from greyhorse.app.abc.collectors import Collector, MutCollector
from greyhorse.app.abc.controllers import Controller, ControllerError, ControllerFactoryFn
from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import Provider
from greyhorse.app.abc.selectors import ListSelector
from greyhorse.app.abc.services import Service, ServiceFactoryFn, ServiceError
from greyhorse.app.registries import MutDictRegistry
from greyhorse.app.schemas.components import ComponentConf, ModuleComponentConf
from greyhorse.app.schemas.elements import CtrlConf, SvcConf
from greyhorse.error import Error, ErrorCase
from greyhorse.logging import logger
from greyhorse.maybe import Maybe
from greyhorse.result import Result, Ok, Err
from greyhorse.utils.injectors import ParamsInjector

if TYPE_CHECKING:
    from .module import Module


class ComponentError(Error):
    namespace = 'greyhorse.app.component'

    Ctrl = ErrorCase(
        msg='{path}: Controller error in component: "{name}", details: "{details}"',
        path=str, name=str, details=str,
    )
    Service = ErrorCase(
        msg='{path}: Service error in component: "{name}", details: "{details}"',
        path=str, name=str, details=str,
    )
    Module = ErrorCase(
        msg='{path}: Submodule error in component: "{name}", details: "{details}"',
        path=str, name=str, details=str,
    )


class BasicComponent:
    def __init__(self, name: str, path: str):
        self._name = name
        self._path = path

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> str:
        return self._path


class Component(BasicComponent):
    def __init__(
        self, name: str, path: str, conf: ComponentConf,
        operator_reg: MutDictRegistry[type, Operator],
    ):
        super().__init__(name, path)
        self._conf = conf

        self._controllers: list[Controller] = []
        self._services: dict[type[Service], Service] = {}

        self._imported_providers = MutDictRegistry[type[Provider], Provider]()
        self._private_providers = MutDictRegistry[type[Provider], Provider]()
        self._operator_reg = operator_reg

    def get_service[T: Service](self, type_: type[T]) -> Maybe[T]:
        return Maybe(self._services.get(type_))

    def setup(
        self, prov_selector: ListSelector[type[Provider], Provider],
        prov_collector: Collector[type[Provider], Provider],
    ) -> Result[None, ComponentError]:
        injector = ParamsInjector()

        logger.info(
            '{path}: Component "{name}" setup'
            .format(path=self._path, name=self.name)
        )

        for prov_conf in self._conf.provider_grants:
            for prov_type in prov_conf.types:
                for _, prov in prov_selector.items(lambda t: issubclass(t, prov_type)):
                    self._imported_providers.add(prov_type, prov)

        for prov_type, provider in self._imported_providers.items():
            injector.add_type_provider(prov_type, provider)

        if not (res := self._create_controllers(injector)):
            return res

        self._controllers = res.unwrap()

        for ctrl in self._controllers:
            if not (res := ctrl.setup(self._imported_providers, self._operator_reg).map_err(
                lambda e: ComponentError.Ctrl(path=self._path, name=self.name, details=e.message)
            )):
                return res

        for res_type, operator in self._operator_reg.items():
            injector.add_type_provider(Operator[res_type], operator)

        if not (res := self._create_services(injector)):
            return res

        self._services = {type(s): s for s in res.unwrap()}

        for svc in self._services.values():
            if not (res := svc.setup(self._operator_reg, self._private_providers).map_err(
                lambda e: ComponentError.Service(path=self._path, name=self.name, details=e.message)
            )):
                return res

        for prov_conf in self._conf.provider_imports:
            for prov_type in prov_conf.types:
                for _, prov in self._private_providers.items(lambda t: issubclass(t, prov_type)):
                    prov_collector.add(prov_type, prov)

        logger.info(
            '{path}: Component "{name}" setup successful'
            .format(path=self._path, name=self.name)
        )

        return Ok(None)

    def teardown(
        self, prov_selector: ListSelector[type[Provider], Provider],
        prov_collector: MutCollector[type[Provider], Provider],
    ) -> Result[None, ComponentError]:

        logger.info(
            '{path}: Component "{name}" teardown'
            .format(path=self._path, name=self.name)
        )

        for prov_conf in reversed(self._conf.provider_imports):
            for prov_type in prov_conf.types:
                for _, prov in self._private_providers.items(lambda t: issubclass(t, prov_type)):
                    prov_collector.remove(prov_type, prov)

        for svc in reversed(self._services.values()):
            if not (res := svc.teardown(self._operator_reg, self._private_providers).map_err(
                lambda e: ComponentError.Service(path=self._path, name=self.name, details=e.message)
            )):
                return res

        self._services = {}

        for ctrl in reversed(self._controllers):
            if not (res := ctrl.teardown(self._imported_providers, self._operator_reg).map_err(
                lambda e: ComponentError.Ctrl(path=self._path, name=self.name, details=e.message)
            )):
                return res

        self._controllers = []

        for prov_conf in reversed(self._conf.provider_grants):
            for prov_type in prov_conf.types:
                for _, prov in prov_selector.items(lambda t: issubclass(t, prov_type)):
                    self._imported_providers.remove(prov_type, prov)

        logger.info(
            '{path}: Component "{name}" teardown successful'
            .format(path=self._path, name=self.name)
        )

        return Ok(None)

    def _create_controller(
        self, conf: CtrlConf, factory: ControllerFactoryFn,
        injector: ParamsInjector,
    ) -> Result[Controller, ControllerError]:
        logger.info(
            '{path}: Component controller "{name}" create'
            .format(path=self._path, name=conf.name)
        )

        values = conf.args.copy()
        values['name'] = conf.name
        values['operators'] = conf.operators
        injected_args = injector(factory, values=values)

        try:
            if not (res := factory(*injected_args.args, **injected_args.kwargs)):
                return res

        except Exception as e:
            error = ControllerError.Factory(details=str(e))
            logger.error(error.message)
            return error.to_result()

        logger.info(
            '{path}: Component controller "{name}" created successfully'
            .format(path=self._path, name=conf.name)
        )

        if isinstance(res, Controller):
            return Ok(res)

        return res

    def _create_service(
        self, conf: SvcConf, factory: ServiceFactoryFn,
        injector: ParamsInjector,
    ) -> Result[Service, ServiceError]:
        logger.info(
            '{path}: Component service "{name}" create'
            .format(path=self._path, name=conf.name)
        )

        values = conf.args.copy()
        values['name'] = conf.name
        values['providers'] = conf.providers
        injected_args = injector(factory, values=values)

        try:
            if not (res := factory(*injected_args.args, **injected_args.kwargs)):
                return res

        except Exception as e:
            error = ServiceError.Factory(details=str(e))
            logger.error(error.message)
            return error.to_result()

        logger.info(
            '{path}: Component service "{name}" created successfully'
            .format(path=self._path, name=conf.name)
        )

        if isinstance(res, Service):
            return Ok(res)

        return res

    def _create_controllers(
        self, injector: ParamsInjector,
    ) -> Result[list[Controller], ComponentError]:
        result = []

        for conf in self._conf.controllers:
            factory = self._conf.controller_factories.get(conf.type_, conf.type_)

            match self._create_controller(conf, factory, injector):
                case Ok(ctrl):
                    result.append(ctrl)

                case Err(e):
                    error = ComponentError.Ctrl(path=self._path, name=self.name, details=e.message)
                    logger.error(error.message)
                    return error.to_result()

        return Ok(result)

    def _create_services(
        self, injector: ParamsInjector,
    ) -> Result[list[Service], ComponentError]:
        result = []

        for conf in self._conf.services:
            factory = self._conf.service_factories.get(conf.type_, conf.type_)

            match self._create_service(conf, factory, injector):
                case Ok(svc):
                    result.append(svc)

                case Err(e):
                    error = ComponentError.Service(path=self._path, name=self.name, details=e.message)
                    logger.error(error.message)
                    return error.to_result()

        return Ok(result)


class ModuleComponent(BasicComponent):
    def __init__(
        self, name: str, path: str,
        conf: ModuleComponentConf, module: 'Module',
    ):
        super().__init__(name, path)
        self._conf = conf
        self._module = module

    def setup(
        self, prov_selector: ListSelector[type[Provider], Provider],
        prov_collector: Collector[type[Provider], Provider],
    ) -> Result[None, ComponentError]:
        for prov_conf in self._conf.provider_grants:
            for prov_type in prov_conf.types:
                for _, prov in prov_selector.items(lambda t: issubclass(t, prov_type)):
                    self._module.add_provider(prov_type, prov)

        if not (res := self._module.setup().map_err(
            lambda e: ComponentError.Module(path=self._path, name=self.name, details=e.message)
        )):
            return res

        for prov_conf in self._conf.provider_imports:
            for prov_type in prov_conf.types:
                if prov := self._module.get_provider(prov_type).unwrap_or_none():
                    prov_collector.add(prov_type, prov)

        return Ok(None)

    def teardown(
        self, prov_selector: ListSelector[type[Provider], Provider],
        prov_collector: MutCollector[type[Provider], Provider],
    ) -> Result[None, ComponentError]:
        for prov_conf in reversed(self._conf.provider_imports):
            for prov_type in prov_conf.types:
                if prov := self._module.get_provider(prov_type).unwrap_or_none():
                    prov_collector.remove(prov_type, prov)

        if not (res := self._module.teardown().map_err(
            lambda e: ComponentError.Module(path=self._path, name=self.name, details=e.message)
        )):
            return res

        for prov_conf in reversed(self._conf.provider_grants):
            for prov_type in prov_conf.types:
                for _, prov in prov_selector.items(lambda t: issubclass(t, prov_type)):
                    self._module.remove_provider(prov_type, prov)

        return Ok(None)
