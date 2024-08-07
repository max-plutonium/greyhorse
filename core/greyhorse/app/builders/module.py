from greyhorse.app.abc.operators import Operator
from greyhorse.app.builders.loader import ModuleLoader
from greyhorse.app.entities.components import Component, ModuleComponent
from greyhorse.app.entities.module import Module
from greyhorse.app.registries import MutDictRegistry
from greyhorse.app.schemas.components import ModuleConf, ComponentConf, ModuleComponentConf
from greyhorse.error import Error, ErrorCase
from greyhorse.logging import logger
from greyhorse.result import Result, Ok, Err


class ModuleBuildError(Error):
    namespace = 'greyhorse.app.builders.module'

    Disabled = ErrorCase(msg='Module is disabled: "{path}"', path=str)
    Factory = ErrorCase(
        msg='Module factory error: "{path}", details: "{details}"',
        path=str, details=str,
    )
    LoadError = ErrorCase(
        msg='Load error in component: "{path}", details: "{details}"',
        path=str, details=str,
    )
    UnloadError = ErrorCase(
        msg='Unload error in component: "{path}", details: "{details}"',
        path=str, details=str,
    )
    ComponentError = ErrorCase(
        msg='Component error in module: "{path}" "{name}", details: "{details}"',
        path=str, name=str, details=str,
    )


class ComponentBuildError(Error):
    namespace = 'greyhorse.app.builders.component'

    Disabled = ErrorCase(msg='Component is disabled: "{path}" "{name}"', path=str, name=str)
    Factory = ErrorCase(
        msg='Component factory error: "{path}" "{name}", details: "{details}"',
        path=str, name=str, details=str,
    )
    Submodule = ErrorCase(
        msg='Component submodule error: "{path}" "{name}", details: "{details}"',
        path=str, name=str, details=str,
    )


class ModuleBuilder:
    def __init__(self, conf: ModuleConf, path: str):
        self._conf = conf
        self._path = path

    def create_pass(self) -> Result[Module, ModuleBuildError]:
        if not self._conf.enabled:
            return ModuleBuildError.Disabled(path=self._path).to_result()

        logger.info(
            '{path}: Module "{name}" creation'
            .format(path=self._path, name=self._conf.name)
        )

        operator_reg = MutDictRegistry[type, Operator]()

        if not (res := self._create_components(operator_reg)):
            return res

        components = res.unwrap()

        try:
            instance = Module(
                name=self._conf.name, conf=self._conf, path=self._path,
                components=components, operator_reg=operator_reg,
            )

        except Exception as e:
            error = ModuleBuildError.Factory(path=self._path, details=str(e))
            logger.error(error.message)
            return error.to_result()

        logger.info(
            '{path}: Module "{name}" created successfully'
            .format(path=self._path, name=self._conf.name)
        )
        return Ok(instance)

    def _create_component(
        self, conf: ComponentConf, operator_reg: MutDictRegistry[type, Operator],
    ) -> Result[Component, ComponentBuildError]:
        if not conf.enabled:
            return ComponentBuildError.Disabled(path=self._path, name=conf.name).to_result()

        logger.info(
            '{path}: Component "{name}" creation'
            .format(path=self._path, name=conf.name)
        )

        try:
            instance = Component(
                name=conf.name, path=self._path,
                conf=conf, operator_reg=operator_reg,
            )

        except Exception as e:
            error = ComponentBuildError.Factory(path=self._path, name=conf.name, details=str(e))
            logger.error(error.message)
            return error.to_result()

        logger.info(
            '{path}: Component "{name}" created successfully'
            .format(path=self._path, name=conf.name)
        )

        return Ok(instance)

    def _create_module_component(
        self, conf: ModuleComponentConf,
    ) -> Result[ModuleComponent, ComponentBuildError]:
        if not conf.enabled:
            return ComponentBuildError.Disabled(path=self._path, name=conf.name).to_result()

        logger.info(
            '{path}: Module component "{name}" creation'
            .format(path=self._path, name=conf.name)
        )

        if not (res := load_module(f'{self._path}.{conf.name}', conf).map_err(
            lambda e: ComponentBuildError.Submodule(path=self._path, name=conf.name, details=e.message)
        )):
            return res

        module = res.unwrap()

        try:
            instance = ModuleComponent(
                name=conf.name, path=self._path,
                conf=conf, module=module,
            )

        except Exception as e:
            error = ComponentBuildError.Factory(path=self._path, name=conf.name, details=str(e))
            logger.error(error.message)
            return error.to_result()

        logger.info(
            '{path}: Module component "{name}" created successfully'
            .format(path=self._path, name=conf.name)
        )

        return Ok(instance)

    def _create_components(
        self, operator_reg: MutDictRegistry[type, Operator],
    ) -> Result[list[Component], ModuleBuildError]:
        result = []

        for conf in self._conf.components:
            match conf:
                case ComponentConf() as conf:
                    match self._create_component(conf, operator_reg):
                        case Ok(component):
                            result.append(component)

                        case Err(e):
                            match e:
                                case ComponentBuildError.Disabled(_):
                                    logger.info(e.message)
                                case _:
                                    error = ModuleBuildError.ComponentError(
                                        path=self._path, name=conf.name, details=e.message,
                                    )
                                    logger.error(error.message)
                                    return error.to_result()

                case ModuleComponentConf() as conf:
                    match self._create_module_component(conf):
                        case Ok(component):
                            result.append(component)

                        case Err(e):
                            match e:
                                case ComponentBuildError.Disabled(_):
                                    logger.info(e.message)
                                case _:
                                    error = ModuleBuildError.ComponentError(
                                        path=self._path, name=conf.name, details=e.message,
                                    )
                                    logger.error(error.message)
                                    return error.to_result()

        return Ok(result)


def load_module(
    path: str, conf: ModuleComponentConf,
) -> Result[Module, ModuleBuildError.LoadError]:
    loader = ModuleLoader()

    if not (res := loader.load_pass(conf).map_err(
        lambda e: ModuleBuildError.LoadError(path=conf.path, details=e.message)
    )):
        return res

    module_conf = res.unwrap()
    builder = ModuleBuilder(module_conf, path)

    if not (res := builder.create_pass().map_err(
        lambda e: ModuleBuildError.LoadError(path=conf.path, details=e.message)
    )):
        return res

    module = res.unwrap()
    return Ok(module)


def unload_module(
    conf: ModuleComponentConf,
) -> Result[None, ModuleBuildError.UnloadError]:
    loader = ModuleLoader()

    return loader.unload_pass(conf).map_err(
        lambda e: ModuleBuildError.UnloadError(path=conf.path, details=e.message)
    )
