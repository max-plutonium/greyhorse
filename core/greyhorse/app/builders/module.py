from greyhorse.app.builders.loader import ModuleLoader
from greyhorse.app.entities.components import Component, ModuleComponent
from greyhorse.app.entities.module import Module
from greyhorse.app.schemas.components import ComponentConf, ModuleComponentConf, ModuleConf
from greyhorse.error import Error, ErrorCase
from greyhorse.logging import logger
from greyhorse.result import Err, Ok, Result


class ModuleBuildError(Error):
    namespace = 'greyhorse.app.builders.module'

    Disabled = ErrorCase(msg='Module is disabled: "{path}"', path=str)
    Factory = ErrorCase(
        msg='Module factory error: "{path}", details: "{details}"', path=str, details=str
    )
    LoadError = ErrorCase(
        msg='Load error in component: "{path}", details: "{details}"', path=str, details=str
    )
    UnloadError = ErrorCase(
        msg='Unload error in component: "{path}", details: "{details}"', path=str, details=str
    )
    ComponentError = ErrorCase(
        msg='Component error in module: "{path}" "{name}", details: "{details}"',
        path=str,
        name=str,
        details=str,
    )


class ComponentBuildError(Error):
    namespace = 'greyhorse.app.builders.component'

    Disabled = ErrorCase(msg='Component is disabled: "{path}" "{name}"', path=str, name=str)
    Factory = ErrorCase(
        msg='Component factory error: "{path}" "{name}", details: "{details}"',
        path=str,
        name=str,
        details=str,
    )
    Submodule = ErrorCase(
        msg='Component submodule error: "{path}" "{name}", details: "{details}"',
        path=str,
        name=str,
        details=str,
    )


class ModuleBuilder:
    def __init__(self, conf: ModuleConf, path: str) -> None:
        self._conf = conf
        self._path = path

    def create_pass(self) -> Result[Module, ModuleBuildError]:
        if not self._conf.enabled:
            return ModuleBuildError.Disabled(path=self._path).to_result()

        logger.info('{path}: Module create'.format(path=self._path))

        if not (res := self._create_components()):
            return res  # type: ignore

        components = res.unwrap()

        try:
            instance = Module(path=self._path, conf=self._conf, components=components)

        except Exception as e:
            error = ModuleBuildError.Factory(path=self._path, details=str(e))
            logger.error(error.message)
            return error.to_result()

        logger.info('{path}: Module created successfully'.format(path=self._path))
        return Ok(instance)

    def destroy_pass(self) -> Result[None, ModuleBuildError]:
        if not self._conf.enabled:
            return ModuleBuildError.Disabled(path=self._path).to_result()

        logger.info('{path}: Module destroy'.format(path=self._path))

        if not (res := self._destroy_components()):
            return res

        logger.info('{path}: Module destroyed successfully'.format(path=self._path))
        return Ok()

    def _create_component(
        self, name: str, conf: ComponentConf
    ) -> Result[Component, ComponentBuildError]:
        if not conf.enabled:
            return ComponentBuildError.Disabled(path=self._path, name=name).to_result()

        logger.info('{path}: Component "{name}" creation'.format(path=self._path, name=name))

        try:
            instance = Component(name=name, path=self._path, conf=conf)

        except Exception as e:
            error = ComponentBuildError.Factory(path=self._path, name=name, details=str(e))
            logger.error(error.message)
            return error.to_result()

        logger.info(
            '{path}: Component "{name}" created successfully'.format(path=self._path, name=name)
        )

        return Ok(instance)

    def _create_module_component(
        self, name: str, conf: ModuleComponentConf
    ) -> Result[ModuleComponent, ComponentBuildError]:
        if not conf.enabled:
            return ComponentBuildError.Disabled(path=self._path, name=name).to_result()

        logger.info(
            '{path}: Module component "{name}" create'.format(path=self._path, name=name)
        )

        if not (
            res := load_module(f'{self._path}.{name}', conf).map_err(
                lambda err: ComponentBuildError.Submodule(
                    path=self._path, name=name, details=err.message
                )
            )
        ):
            return res  # type: ignore

        module = res.unwrap()

        try:
            instance = ModuleComponent(name=name, path=self._path, conf=conf, module=module)

        except Exception as e:
            error = ComponentBuildError.Factory(path=self._path, name=name, details=str(e))
            logger.error(error.message)
            return error.to_result()

        logger.info(
            '{path}: Module component "{name}" created successfully'.format(
                path=self._path, name=name
            )
        )

        return Ok(instance)

    def _create_components(self) -> Result[list[Component], ModuleBuildError]:
        result = []

        for name, conf in self._conf.components.items():
            match conf:
                case ModuleComponentConf() as conf:
                    match self._create_module_component(name, conf):
                        case Ok(component):
                            result.append(component)

                        case Err(e):
                            match e:
                                case ComponentBuildError.Disabled(_):
                                    logger.info(e.message)
                                case _:
                                    error = ModuleBuildError.ComponentError(
                                        path=self._path, name=name, details=e.message
                                    )
                                    logger.error(error.message)
                                    return error.to_result()

                case ComponentConf() as conf:
                    match self._create_component(name, conf):
                        case Ok(component):
                            result.append(component)

                        case Err(e):
                            match e:
                                case ComponentBuildError.Disabled(_):
                                    logger.info(e.message)
                                case _:
                                    error = ModuleBuildError.ComponentError(
                                        path=self._path, name=name, details=e.message
                                    )
                                    logger.error(error.message)
                                    return error.to_result()

        return Ok(result)

    def _destroy_components(self) -> Result[None, ModuleBuildError]:
        for name, conf in reversed(self._conf.components.items()):
            if not conf.enabled:
                return ComponentBuildError.Disabled(path=self._path, name=name).to_result()

            match conf:
                case ComponentConf():
                    pass

                case ModuleComponentConf() as conf:
                    logger.info(
                        '{path}: Module component "{name}" destroy'.format(
                            path=self._path, name=name
                        )
                    )

                    if not (
                        res := unload_module(f'{self._path}.{name}', conf).map_err(
                            lambda e: ModuleBuildError.UnloadError(
                                path=self._path, details=e.message
                            )
                        )
                    ):
                        return res

                    logger.info(
                        '{path}: Module component "{name}" destroyed successfully'.format(
                            path=self._path, name=name
                        )
                    )

        return Ok()


def load_module(path: str, conf: ModuleComponentConf) -> Result[Module, ModuleBuildError]:
    loader = ModuleLoader()

    if not (
        res := loader.load_pass(conf).map_err(
            lambda e: ModuleBuildError.LoadError(path=conf.path, details=e.message)
        )
    ):
        return res  # type: ignore

    module_conf = res.unwrap()
    builder = ModuleBuilder(module_conf, path)

    if not (res := builder.create_pass()):
        return res

    module = res.unwrap()
    return Ok(module)


def unload_module(path: str, conf: ModuleComponentConf) -> Result[None, ModuleBuildError]:
    builder = ModuleBuilder(conf._conf, path)  # noqa

    if not (res := builder.destroy_pass()):
        return res

    loader = ModuleLoader()

    return loader.unload_pass(conf).map_err(
        lambda e: ModuleBuildError.UnloadError(path=conf.path, details=e.message)
    )
