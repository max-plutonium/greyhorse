from collections import defaultdict
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from greyhorse.app.abc.controllers import Controller, ControllerError, ControllerFactoryFn
from greyhorse.app.abc.providers import Provider
from greyhorse.app.abc.services import Service, ServiceError, ServiceFactoryFn
from greyhorse.app.registries import MutNamedDictRegistry
from greyhorse.app.schemas.components import ComponentConf, ModuleComponentConf
from greyhorse.app.schemas.elements import CtrlConf, SvcConf
from greyhorse.error import Error, ErrorCase
from greyhorse.logging import logger
from greyhorse.result import Err, Ok, Result
from greyhorse.utils.injectors import ParamsInjector

from ...maybe import Just, Maybe, Nothing
from ...utils.invoke import invoke_sync
from ..abc.operators import Operator
from ..abc.selectors import NamedListSelector, NamedSelector
from ..abc.visitor import Visitor
from ..private.res_manager import ResourceManager

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

        self._resources = MutNamedDictRegistry[type, Any]()
        # XXX: component providers
        # self._providers = MutDictRegistry[type[Provider], Provider]()
        self._operators: dict[type, list[Operator]] = defaultdict(list)

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> str:
        return self._path

    def accept_visitor(self, visitor: Visitor) -> None:
        visitor.start_component(self)
        for svc in self._services:
            svc.accept_visitor(visitor)
        for ctrl in self._controllers:
            ctrl.accept_visitor(visitor)
        visitor.finish_component(self)

    def get_provider[P: Provider](self, prov_type: type[P]) -> Maybe[P]:
        if prov_type in self._conf.providers:
            return self._rm.find_provider(prov_type).map(Just).unwrap_or(Nothing)
        return Nothing

    def get_operators[T](self, res_type: type[T]) -> Iterable[Operator[T]]:
        if res_type in self._conf.operators:
            return self._operators[res_type].copy()
        return []

    # XXX: component providers
    # def add_provider[T](self, prov_type: type[Provider[T]], provider: Provider[T]) -> bool:
    #     return self._providers.add(prov_type, provider)

    # XXX: component providers
    # def remove_provider[T](self, prov_type: type[Provider[T]]) -> bool:
    #     return self._providers.remove(prov_type)

    def add_resource(self, res_type: type, resource: Any, name: str | None = None) -> bool:  # noqa: ANN401
        if res_type in self._conf.resource_claims:
            return self._resources.add(res_type, resource, name=name)
        return False

    def remove_resource(self, res_type: type, name: str | None = None) -> bool:
        if res_type in self._conf.resource_claims:
            return self._resources.remove(res_type, name=name)
        return False

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

    def create(self) -> Result[None, ComponentError]:
        logger.info('{path}: Component "{name}" create'.format(path=self._path, name=self.name))

        injector = ParamsInjector()

        if not (res := self._create_services(injector)):
            return res  # type: ignore

        for svc in res.unwrap():
            injector.add_type_provider(type(svc), svc)
            self.add_service(svc)

        if not (res := self._create_controllers(injector)):
            return res  # type: ignore

        for svc in self._services:
            injector.remove_type_provider(type(svc))

        for ctrl in res.unwrap():
            self.add_controller(ctrl)

        if not (
            res := self._rm.setup().map_err(
                lambda e: ComponentError.Resource(
                    path=self._path, name=self.name, details=e.message
                )
            )
        ):
            return res

        for op in self._rm.get_operators():
            self._operators[op.wrapped_type].append(op)

        logger.info(
            '{path}: Component "{name}" create successful'.format(
                path=self._path, name=self.name
            )
        )

        return Ok()

    def setup(self) -> Result[None, ComponentError]:
        logger.info('{path}: Component "{name}" setup'.format(path=self._path, name=self.name))

        injector = ParamsInjector()

        for ctrl, _ctrl_conf in zip(self._controllers, self._conf.controllers, strict=False):
            if not (
                res := invoke_sync(ctrl.setup, self._resources).map_err(
                    lambda e: ComponentError.Ctrl(
                        path=self._path, name=self.name, details=e.message
                    )
                )
            ):
                return res

        injector.add_type_provider(NamedSelector[type, Any], self._resources)
        injector.add_type_provider(NamedListSelector[type, Any], self._resources)

        for svc, svc_conf in zip(self._services, self._conf.services, strict=False):
            for res_type in svc_conf.resources:
                injector.add_type_provider(Maybe[res_type], self._resources.get(res_type))

            injected_args = injector(svc.setup)

            if not (
                res := invoke_sync(
                    svc.setup, *injected_args.args, **injected_args.kwargs
                ).map_err(
                    lambda e: ComponentError.Service(
                        path=self._path, name=self.name, details=e.message
                    )
                )
            ):
                return res

            for res_type in svc_conf.resources:
                injector.remove_type_provider(Maybe[res_type])

        injector.remove_type_provider(NamedSelector[type, Any])
        injector.remove_type_provider(NamedListSelector[type, Any])

        logger.info(
            '{path}: Component "{name}" setup successful'.format(
                path=self._path, name=self.name
            )
        )

        return Ok()

    def teardown(self) -> Result[None, ComponentError]:
        injector = ParamsInjector()

        logger.info(
            '{path}: Component "{name}" teardown'.format(path=self._path, name=self.name)
        )

        injector.add_type_provider(NamedSelector[type, Any], self._resources)
        injector.add_type_provider(NamedListSelector[type, Any], self._resources)

        for svc, svc_conf in zip(
            reversed(self._services), reversed(self._conf.services), strict=False
        ):
            for res_type in svc_conf.resources:
                injector.add_type_provider(Maybe[res_type], self._resources.get(res_type))

            injected_args = injector(svc.teardown)

            if not (
                res := invoke_sync(
                    svc.teardown, *injected_args.args, **injected_args.kwargs
                ).map_err(
                    lambda e: ComponentError.Service(
                        path=self._path, name=self.name, details=e.message
                    )
                )
            ):
                return res

            for res_type in svc_conf.resources:
                injector.remove_type_provider(Maybe[res_type])

        injector.remove_type_provider(NamedSelector[type, Any])
        injector.remove_type_provider(NamedListSelector[type, Any])

        for ctrl, _ctrl_conf in zip(
            reversed(self._controllers), reversed(self._conf.controllers), strict=False
        ):
            if not (
                res := invoke_sync(ctrl.teardown, self._resources).map_err(
                    lambda e: ComponentError.Ctrl(
                        path=self._path, name=self.name, details=e.message
                    )
                )
            ):
                return res

        logger.info(
            '{path}: Component "{name}" teardown successful'.format(
                path=self._path, name=self.name
            )
        )

        return Ok()

    def destroy(self) -> Result[None, ComponentError]:
        logger.info(
            '{path}: Component "{name}" destroy'.format(path=self._path, name=self.name)
        )

        for op in self._rm.get_operators():
            self._operators[op.wrapped_type].remove(op)

        if not (
            res := self._rm.teardown().map_err(
                lambda e: ComponentError.Resource(
                    path=self._path, name=self.name, details=e.message
                )
            )
        ):
            return res

        while ctrl := next(reversed(self._controllers), None):
            self.remove_controller(ctrl)

        while svc := next(reversed(self._services), None):
            self.remove_service(svc)

        assert not self._controllers
        assert not self._services

        logger.info(
            '{path}: Component "{name}" destroy successful'.format(
                path=self._path, name=self.name
            )
        )

        return Ok()

    def _create_controller(
        self, conf: CtrlConf, factory: ControllerFactoryFn, injector: ParamsInjector
    ) -> Result[Controller, ControllerError]:
        logger.info(
            '{path}: Component controller "{name}" create'.format(
                path=self._path, name=conf.name
            )
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
                path=self._path, name=conf.name
            )
        )

        if isinstance(res, Controller):
            return Ok(res)

        return res

    def _create_service(
        self, conf: SvcConf, factory: ServiceFactoryFn, injector: ParamsInjector
    ) -> Result[Service, ServiceError]:
        logger.info(
            '{path}: Component service "{name}" create'.format(path=self._path, name=conf.name)
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
                path=self._path, name=conf.name
            )
        )

        if isinstance(res, Service):
            return Ok(res)

        return res

    def _create_controllers(
        self, injector: ParamsInjector
    ) -> Result[list[Controller], ComponentError]:
        result = []

        for conf in self._conf.controllers:
            factory = self._conf.controller_factories.get(conf.type_, conf.type_)

            match self._create_controller(conf, factory, injector):
                case Ok(ctrl):
                    result.append(ctrl)

                case Err(e):
                    error = ComponentError.Ctrl(
                        path=self._path, name=self.name, details=e.message
                    )
                    logger.error(error.message)
                    return error.to_result()

        return Ok(result)

    def _create_services(
        self, injector: ParamsInjector
    ) -> Result[list[Service], ComponentError]:
        result = []

        for conf in self._conf.services:
            factory = self._conf.service_factories.get(conf.type_, conf.type_)

            match self._create_service(conf, factory, injector):
                case Ok(svc):
                    result.append(svc)

                case Err(e):
                    error = ComponentError.Service(
                        path=self._path, name=self.name, details=e.message
                    )
                    logger.error(error.message)
                    return error.to_result()

        return Ok(result)


class ModuleComponent(Component):
    def __init__(
        self, name: str, path: str, conf: ModuleComponentConf, module: 'Module'
    ) -> None:
        super().__init__(name, path, conf)
        self._conf = conf
        self._module = module

    def accept_visitor(self, visitor: Visitor) -> None:
        visitor.start_component(self)
        for svc in self._services:
            svc.accept_visitor(visitor)
        for ctrl in self._controllers:
            ctrl.accept_visitor(visitor)
        self._module.accept_visitor(visitor)
        visitor.finish_component(self)

    def setup(self) -> Result[None, ComponentError]:
        if not (res := super().setup()):
            return res

        for prov_type in self._module.conf.provider_claims:
            if prov := self.get_provider(prov_type).unwrap_or_none():
                self._module.add_provider(prov_type, prov)

        for res_type in self._module.conf.resource_claims:
            if res := self._resources.get(res_type).unwrap_or_none():
                self._module.add_resource(res_type, res)

        for res_type in self._module.conf.operators:
            for op in self._operators[res_type]:
                self._module.add_operator(op)

        if not (
            res := self._module.setup().map_err(
                lambda e: ComponentError.Module(
                    path=self._path, name=self.name, details=e.message
                )
            )
        ):
            return res

        return Ok()

    def teardown(self) -> Result[None, ComponentError]:
        if not (
            res := self._module.teardown().map_err(
                lambda e: ComponentError.Module(
                    path=self._path, name=self.name, details=e.message
                )
            )
        ):
            return res

        for res_type in reversed(self._module.conf.operators):
            for op in self._operators[res_type]:
                self._module.remove_operator(op)

        for res_type in reversed(self._module.conf.resource_claims):
            self._module.remove_resource(res_type)

        for prov_type in reversed(self._module.conf.provider_claims):
            self._module.remove_provider(prov_type)

        return super().teardown()
