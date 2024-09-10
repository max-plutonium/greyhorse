from typing import TYPE_CHECKING

from greyhorse.app.abc.controllers import Controller, ControllerError, ControllerFactoryFn
from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import Provider
from greyhorse.app.abc.services import Service, ServiceError, ServiceFactoryFn
from greyhorse.app.registries import MutDictRegistry
from greyhorse.app.schemas.components import ComponentConf, ModuleComponentConf
from greyhorse.app.schemas.elements import CtrlConf, SvcConf
from greyhorse.error import Error, ErrorCase
from greyhorse.logging import logger
from greyhorse.result import Err, Ok, Result
from greyhorse.utils.injectors import ParamsInjector
from ..private.component import ResourceManager
from ...maybe import Just, Maybe, Nothing

if TYPE_CHECKING:
    from .module import Module


class ComponentError(Error):
    namespace = 'greyhorse.app.component'

    Resource = ErrorCase(
        msg='{path}: Resource error in component: "{name}", details: "{details}"',
        path=str,
        name=str,
        details=str,
    )
    Ctrl = ErrorCase(
        msg='{path}: Controller error in component: "{name}", details: "{details}"',
        path=str,
        name=str,
        details=str,
    )
    Service = ErrorCase(
        msg='{path}: Service error in component: "{name}", details: "{details}"',
        path=str,
        name=str,
        details=str,
    )
    Module = ErrorCase(
        msg='{path}: Submodule error in component: "{name}", details: "{details}"',
        path=str,
        name=str,
        details=str,
    )


class Component:
    def __init__(self, name: str, path: str, conf: ComponentConf) -> None:
        self._name = name
        self._path = path
        self._conf = conf
        self._rm = ResourceManager()

        self._controllers: list[Controller] = []
        self._services: list[Service] = []

        self._private_providers = MutDictRegistry[type[Provider], Provider]()
        self._private_operators = MutDictRegistry[type, Operator]()  # TODO remove

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> str:
        return self._path

    def add_controller(self, controller: Controller) -> bool:
        if self._controllers.count(controller):
            return False
        self._controllers.append(controller)
        return self._rm.add_controller(controller)

    def remove_controller(self, controller: Controller) -> bool:
        if not self._controllers.count(controller):
            return False
        self._controllers.remove(controller)
        return self._rm.remove_controller(controller)

    def add_service(self, service: Service) -> bool:
        if self._services.count(service):
            return False
        self._services.append(service)
        return self._rm.add_service(service)

    def remove_service(self, service: Service) -> bool:
        if not self._services.count(service):
            return False
        self._services.remove(service)
        return self._rm.remove_service(service)

    def get_provider[T](self, prov_type: type[Provider[T]]) -> Maybe[Provider[T]]:
        return (
            self._rm.find_provider(prov_type, self._private_providers)
            .map(Just)
            .unwrap_or(Nothing)
        )

    def add_provider[T](self, prov_type: type[Provider[T]], provider: Provider[T]) -> bool:
        return self._private_providers.add(prov_type, provider)

    def remove_provider[T](self, prov_type: type[Provider[T]]) -> bool:
        return self._private_providers.remove(prov_type)

    def setup(self) -> Result[None, ComponentError]:
        injector = ParamsInjector()

        logger.info('{path}: Component "{name}" setup'.format(path=self._path, name=self.name))

        if not (res := self._create_services(injector)):
            return res

        for svc in res.unwrap():
            injector.add_type_provider(type(svc), svc)
            self.add_service(svc)

        for svc in self._services:
            if not (
                res := svc.setup(self._private_operators).map_err(
                    lambda e: ComponentError.Service(
                        path=self._path, name=self.name, details=e.message,
                    ),
                )
            ):
                return res

        if not (res := self._create_controllers(injector)):
            return res

        for ctrl in res.unwrap():
            self.add_controller(ctrl)

        for ctrl in self._controllers:
            if not (
                res := ctrl.setup(self._private_providers).map_err(
                    lambda e: ComponentError.Ctrl(
                        path=self._path, name=self.name, details=e.message,
                    ),
                )
            ):
                return res

        if not (
            res := self._rm.setup(self._private_providers).map_err(
                lambda e: ComponentError.Resource(
                    path=self._path, name=self.name, details=e.message,
                ),
            )
        ):
            return res

        logger.info(
            '{path}: Component "{name}" setup successful'.format(
                path=self._path, name=self.name,
            ),
        )

        return Ok(None)

    def teardown(self) -> Result[None, ComponentError]:
        logger.info(
            '{path}: Component "{name}" teardown'.format(path=self._path, name=self.name),
        )

        if not (
            res := self._rm.teardown().map_err(
                lambda e: ComponentError.Resource(
                    path=self._path, name=self.name, details=e.message,
                ),
            )
        ):
            return res

        while ctrl := next(reversed(self._controllers), None):
            if not (
                res := ctrl.teardown(self._private_providers).map_err(
                    lambda e: ComponentError.Ctrl(
                        path=self._path, name=self.name, details=e.message,
                    ),
                )
            ):
                return res

            self.remove_controller(ctrl)

        assert not self._controllers

        while svc := next(reversed(self._services), None):
            if not (
                res := svc.teardown(self._private_operators).map_err(
                    lambda e: ComponentError.Service(
                        path=self._path, name=self.name, details=e.message,
                    ),
                )
            ):
                return res

            self.remove_service(svc)

        assert not self._services

        logger.info(
            '{path}: Component "{name}" teardown successful'.format(
                path=self._path, name=self.name,
            ),
        )

        return Ok(None)

    def _create_controller(
        self, conf: CtrlConf, factory: ControllerFactoryFn, injector: ParamsInjector,
    ) -> Result[Controller, ControllerError]:
        logger.info(
            '{path}: Component controller "{name}" create'.format(
                path=self._path, name=conf.name,
            ),
        )

        values = conf.args.copy()
        values['name'] = conf.name
        injected_args = injector(factory, values=values)

        try:
            if not (res := factory(*injected_args.args, **injected_args.kwargs)):
                return res

        except Exception as e:
            error = ControllerError.Factory(details=str(e))
            logger.error(error.message)
            return error.to_result()

        logger.info(
            '{path}: Component controller "{name}" created successfully'.format(
                path=self._path, name=conf.name,
            ),
        )

        if isinstance(res, Controller):
            return Ok(res)

        return res

    def _create_service(
        self, conf: SvcConf, factory: ServiceFactoryFn, injector: ParamsInjector,
    ) -> Result[Service, ServiceError]:
        logger.info(
            '{path}: Component service "{name}" create'.format(path=self._path, name=conf.name),
        )

        values = conf.args.copy()
        values['name'] = conf.name
        injected_args = injector(factory, values=values)

        try:
            if not (res := factory(*injected_args.args, **injected_args.kwargs)):
                return res

        except Exception as e:
            error = ServiceError.Factory(details=str(e))
            logger.error(error.message)
            return error.to_result()

        logger.info(
            '{path}: Component service "{name}" created successfully'.format(
                path=self._path, name=conf.name,
            ),
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
                    error = ComponentError.Ctrl(
                        path=self._path, name=self.name, details=e.message,
                    )
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
                    error = ComponentError.Service(
                        path=self._path, name=self.name, details=e.message,
                    )
                    logger.error(error.message)
                    return error.to_result()

        return Ok(result)


class ModuleComponent(Component):
    def __init__(
        self, name: str, path: str, conf: ModuleComponentConf, module: 'Module',
    ) -> None:
        super().__init__(name, path, conf)
        self._conf = conf
        self._module = module

    def setup(self) -> Result[None, ComponentError]:
        if not (res := super().setup()):
            return res

        for op in self._rm.get_operators():
            self._module.add_operator(op)

        if not (
            res := self._module.setup().map_err(
                lambda e: ComponentError.Module(
                    path=self._path, name=self.name, details=e.message,
                ),
            )
        ):
            return res

        return Ok(None)

    def teardown(self) -> Result[None, ComponentError]:
        if not (
            res := self._module.teardown().map_err(
                lambda e: ComponentError.Module(
                    path=self._path, name=self.name, details=e.message,
                ),
            )
        ):
            return res

        for op in self._rm.get_operators():
            self._module.remove_operator(op)

        return super().teardown()


13
