from greyhorse.app.abc.services import Service, ServiceError, ServiceFactoryFn
from greyhorse.app.entities.components import Component
from greyhorse.app.schemas.component import ComponentConf
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
    SvcFactoryNotFound = ErrorCase(
        msg='Service factory not found in component "{path}": "{type_}"',
        path=str, type_=str,
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

        if not (res := self._create_services()):
            return res

        try:
            instance = Component(
                name=self._conf.name, conf=self._conf, path=self._path,
                services=res.unwrap(),
            )

        except Exception as e:
            error = ComponentBuildError.Factory(path=self._path, details=str(e))
            logger.error(error.message)
            return error.to_result()

        logger.info('Component created successfully: "{path}"'.format(path=self._path))
        return Ok(instance)

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
        return res

    def _create_services(self) -> Result[list[tuple[str, Service]], ComponentBuildError]:
        result = []

        for conf in self._conf.services:
            if factory := self._conf.service_factories.get(conf.type):
                match self._create_service(conf, factory):
                    case Ok(svc):
                        result.append((conf.name, svc))

                    case Err(e):
                        error = ComponentBuildError.SvcError(path=self._path, details=e.message)
                        logger.error(error.message)
                        return error.to_result()
            else:
                error = ComponentBuildError.SvcFactoryNotFound(path=self._path, type_=conf.type.__name__)
                logger.error(error.message)
                return error.to_result()

        return Ok(result)
