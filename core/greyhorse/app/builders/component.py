from greyhorse.app.abc.controllers import Controller, ControllerError, ControllerFactoryFn
from greyhorse.app.abc.services import Service, ServiceError, ServiceFactoryFn
from greyhorse.app.entities.components import Component
from greyhorse.app.schemas.component import ComponentConf
from greyhorse.app.schemas.controller import CtrlConf
from greyhorse.app.schemas.service import SvcConf
from greyhorse.error import Error, ErrorCase
from greyhorse.logging import logger
from greyhorse.result import Result, Ok, Err
from greyhorse.utils.injectors import ParamsInjector


class ComponentBuildError(Error):
    namespace = 'greyhorse.app.builders.component'

    Disabled = ErrorCase(msg='Component is disabled: "{path}"', path=str)
    Factory = ErrorCase(
        msg='Component factory error: "{path}", details: "{details}"',
        path=str, details=str,
    )
    CtrlError = ErrorCase(
        msg='Controller error in component: "{path}", details: "{details}"',
        path=str, details=str,
    )
    SvcError = ErrorCase(
        msg='Service error in component: "{path}", details: "{details}"',
        path=str, details=str,
    )


class ComponentBuilder:
    def __init__(self, conf: ComponentConf, path: str):
        self._conf = conf
        self._path = path
        self._injector = ParamsInjector()

    def create_pass(self) -> Result[Component, ComponentBuildError]:
        if not self._conf.enabled:
            return ComponentBuildError.Disabled(path=self._path).to_result()

        logger.info('Try to create component: "{path}"'.format(path=self._path))

        if not (res := self._create_controllers()):
            return res

        controllers = res.unwrap()

        if not (res := self._create_services()):
            return res

        services = res.unwrap()

        try:
            instance = Component(
                name=self._conf.name, conf=self._conf, path=self._path,
                controllers=controllers, services=services,
            )

        except Exception as e:
            error = ComponentBuildError.Factory(path=self._path, details=str(e))
            logger.error(error.message)
            return error.to_result()

        logger.info('Component created successfully: "{path}"'.format(path=self._path))
        return Ok(instance)

    def _create_controller(
        self, conf: CtrlConf, factory: ControllerFactoryFn,
    ) -> Result[Controller, ControllerError]:
        logger.info(
            'Try to create component controller: "{path}" "{name}"'
            .format(path=self._path, name=conf.name)
        )

        injected_args = self._injector(factory, values=conf.args)

        try:
            if not (res := factory(*injected_args.args, **injected_args.kwargs)):
                return res

        except Exception as e:
            error = ControllerError.Unexpected(details=str(e))
            logger.error(error.message)
            return error.to_result()

        logger.info(
            'Component controller created successfully: "{path}" "{name}"'
            .format(path=self._path, name=conf.name)
        )

        if isinstance(res, Controller):
            return Ok(res)

        return res

    def _create_service(
        self, conf: SvcConf, factory: ServiceFactoryFn,
    ) -> Result[Service, ServiceError]:
        logger.info(
            'Try to create component service: "{path}" "{name}"'
            .format(path=self._path, name=conf.name)
        )

        injected_args = self._injector(factory, values=conf.args)

        try:
            if not (res := factory(*injected_args.args, **injected_args.kwargs)):
                return res

        except Exception as e:
            error = ServiceError.Unexpected(details=str(e))
            logger.error(error.message)
            return error.to_result()

        logger.info(
            'Component service created successfully: "{path}" "{name}"'
            .format(path=self._path, name=conf.name)
        )

        if isinstance(res, Service):
            return Ok(res)

        return res

    def _create_controllers(self) -> Result[list[Controller], ComponentBuildError]:
        result = []

        for conf in self._conf.controllers:
            factory = self._conf.controller_factories.get(conf.type, conf.type)

            match self._create_controller(conf, factory):
                case Ok(ctrl):
                    result.append(ctrl)

                case Err(e):
                    error = ComponentBuildError.CtrlError(path=self._path, details=e.message)
                    logger.error(error.message)
                    return error.to_result()

        return Ok(result)

    def _create_services(self) -> Result[list[tuple[str, Service]], ComponentBuildError]:
        result = []

        for conf in self._conf.services:
            factory = self._conf.service_factories.get(conf.type, conf.type)

            match self._create_service(conf, factory):
                case Ok(svc):
                    result.append((conf.name, svc))

                case Err(e):
                    error = ComponentBuildError.SvcError(path=self._path, details=e.message)
                    logger.error(error.message)
                    return error.to_result()

        return Ok(result)
