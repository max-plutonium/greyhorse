from collections import defaultdict
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, override

from greyhorse.logging import logger
from greyhorse.maybe import Maybe, Nothing
from greyhorse.result import Err, Ok, Result
from greyhorse.utils.injectors import ParamsInjector
from greyhorse.utils.invoke import invoke_sync

from ..abc.component import Component, ComponentError
from ..abc.controllers import Controller, ControllerError, ControllerFactoryFn
from ..abc.operators import Operator
from ..abc.providers import Provider
from ..abc.resources import Lifetime
from ..abc.services import Service, ServiceError, ServiceFactoryFn
from ..abc.visitor import Visitor
from ..registries import MutDictRegistry
from ..resources import (
    Container,
    ResourceManager,
    inject_targets,
    make_container,
    uninject_targets,
)
from ..schemas.components import ComponentConf, ModuleComponentConf
from ..schemas.elements import CtrlConf, SvcConf

if TYPE_CHECKING:
    from .module import Module


class SyncComponent(Component):
    def __init__(self, name: str, path: str, conf: ComponentConf) -> None:
        super().__init__(name, path)
        self._conf = conf
        self._rm = ResourceManager()

        self._controllers: list[Controller] = []
        self._services: list[Service] = []

        self._resources = MutDictRegistry[type, Any]()
        self._container: Container | None = None
        self._operators: dict[type, list[Operator]] = defaultdict(list)

    @override
    def accept_visitor(self, visitor: Visitor) -> None:
        visitor.start_component(self)
        for svc in self._services:
            svc.accept_visitor(visitor)
        for ctrl in self._controllers:
            ctrl.accept_visitor(visitor)
        visitor.finish_component(self)

    @override
    def get_provider[P: Provider](self, prov_type: type[P]) -> Maybe[P]:
        if prov_type in self._conf.providers:
            return self._container.get(prov_type)
        return Nothing

    @override
    def get_operators[T](self, res_type: type[T]) -> Iterable[Operator[T]]:
        if res_type in self._conf.operators:
            return self._operators[res_type].copy()
        return []

    @override
    def add_resource[T](self, res_type: type[T], resource: T) -> bool:
        if res_type in self._conf.resource_claims:
            return self._resources.add(res_type, resource)
        return False

    @override
    def remove_resource[T](self, res_type: type[T]) -> bool:
        if res_type in self._conf.resource_claims:
            return self._resources.remove(res_type)
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

    @override
    def create(self) -> Result[None, ComponentError]:
        logger.info('{path}: Component "{name}" create'.format(path=self._path, name=self.name))

        self._container = make_container(lifetime=Lifetime.COMPONENT())

        inject_targets(
            self._container,
            [svc.type_.__module__ for svc in self._conf.services]
            + [ctrl.type_.__module__ for ctrl in self._conf.controllers],
        )

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

        self._rm.install_container(self._container)

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

    @override
    def setup(self) -> Result[None, ComponentError]:
        logger.info('{path}: Component "{name}" setup'.format(path=self._path, name=self.name))

        for k, v in self._resources.list():
            self._container.add_resource(k, v)

        self._container.context.__enter__()

        injector = ParamsInjector()
        injector.add_type_provider(Container, self._container)

        for ctrl, _ctrl_conf in zip(self._controllers, self._conf.controllers, strict=False):
            injected_args = injector(ctrl.setup)

            if not (
                res := invoke_sync(
                    ctrl.setup, *injected_args.args, **injected_args.kwargs
                ).map_err(
                    lambda e: ComponentError.Ctrl(
                        path=self._path, name=self.name, details=e.message
                    )
                )
            ):
                return res

        injector.remove_type_provider(Container)

        for svc, _svc_conf in zip(self._services, self._conf.services, strict=False):
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

        logger.info(
            '{path}: Component "{name}" setup successful'.format(
                path=self._path, name=self.name
            )
        )

        return Ok()

    @override
    def teardown(self) -> Result[None, ComponentError]:
        logger.info(
            '{path}: Component "{name}" teardown'.format(path=self._path, name=self.name)
        )

        injector = ParamsInjector()

        for svc, _svc_conf in zip(
            reversed(self._services), reversed(self._conf.services), strict=False
        ):
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

        injector.add_type_provider(Container, self._container)

        for ctrl, _ctrl_conf in zip(
            reversed(self._controllers), reversed(self._conf.controllers), strict=False
        ):
            injected_args = injector(ctrl.teardown)

            if not (
                res := invoke_sync(
                    ctrl.teardown, *injected_args.args, **injected_args.kwargs
                ).map_err(
                    lambda e: ComponentError.Ctrl(
                        path=self._path, name=self.name, details=e.message
                    )
                )
            ):
                return res

        injector.remove_type_provider(Container)

        self._container.context.__exit__()

        for k, _v in self._resources.list():
            self._container.remove_resource(k)

        logger.info(
            '{path}: Component "{name}" teardown successful'.format(
                path=self._path, name=self.name
            )
        )

        return Ok()

    @override
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

        uninject_targets(
            [svc.type_.__module__ for svc in self._conf.services]
            + [ctrl.type_.__module__ for ctrl in self._conf.controllers]
        )

        self._container = None

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
        values['init_path'] = conf._init_path  # noqa: SLF001
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
        values['init_path'] = conf._init_path  # noqa: SLF001
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
            if not conf.enabled:
                continue

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
            if not conf.enabled:
                continue

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


class SyncModuleComponent(SyncComponent):
    def __init__(
        self, name: str, path: str, conf: ModuleComponentConf, module: 'Module'
    ) -> None:
        super().__init__(name, path, conf)
        self._conf = conf
        self._module = module

    @override
    def accept_visitor(self, visitor: Visitor) -> None:
        visitor.start_component(self)
        for svc in self._services:
            svc.accept_visitor(visitor)
        for ctrl in self._controllers:
            ctrl.accept_visitor(visitor)
        self._module.accept_visitor(visitor)
        visitor.finish_component(self)

    @override
    def create(self) -> Result[None, ComponentError]:
        if not (res := super().create()):
            return res

        for prov_type in self._module.conf.provider_claims:
            if prov := self._container.get(prov_type):
                self._module.add_provider(prov_type, prov.unwrap())

        if not (
            res := self._module.create().map_err(
                lambda e: ComponentError.Module(
                    path=self._path, name=self.name, details=e.message
                )
            )
        ):
            return res

        return Ok()

    @override
    def setup(self) -> Result[None, ComponentError]:
        if not (res := super().setup()):
            return res

        for res_type in self._module.conf.resource_claims:
            if res := self._container.get(res_type):
                self._module.add_resource(res_type, res.unwrap())

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

        for prov_type in self._module.conf.providers:
            if prov := self._module.get_provider(prov_type):
                self._container.registry.add_factory(prov_type, prov.unwrap())

        return Ok()

    @override
    def teardown(self) -> Result[None, ComponentError]:
        for prov_type in reversed(self._module.conf.providers):
            self._container.registry.remove_factory(prov_type)

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

        return super().teardown()

    @override
    def destroy(self) -> Result[None, ComponentError]:
        if not (
            res := self._module.destroy().map_err(
                lambda e: ComponentError.Module(
                    path=self._path, name=self.name, details=e.message
                )
            )
        ):
            return res

        for prov_type in reversed(self._module.conf.provider_claims):
            self._module.remove_provider(prov_type)

        return super().destroy()
