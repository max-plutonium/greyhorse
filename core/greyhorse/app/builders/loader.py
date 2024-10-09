import sys
from collections.abc import Callable
from typing import cast

import pydantic

from greyhorse.app.schemas.components import ModuleComponentConf, ModuleConf
from greyhorse.error import Error, ErrorCase
from greyhorse.logging import logger
from greyhorse.result import Ok, Result
from greyhorse.utils.imports import import_path
from greyhorse.utils.injectors import ParamsInjector
from greyhorse.utils.invoke import invoke_sync


class ModuleLoadError(Error):
    namespace = 'greyhorse.app.builders.module'

    Disabled = ErrorCase(msg='Module is disabled: "{path}"', path=str)
    AlreadyLoaded = ErrorCase(msg='Module already loaded: "{path}"', path=str)
    WrongImport = ErrorCase(
        msg='Module import error: "{path}", details: "{details}"', path=str, details=str
    )
    Validation = ErrorCase(
        msg='Module validation error: "{path}", details: "{details}"', path=str, details=str
    )
    Unexpected = ErrorCase(
        msg='Module unexpected error: "{path}", details: "{details}"', path=str, details=str
    )
    InvalidConf = ErrorCase(msg='Module conf is invalid: "{path}"', path=str)


class ModuleUnloadError(Error):
    namespace = 'greyhorse.app.builders.module'

    Disabled = ErrorCase(msg='Module is disabled: "{path}"', path=str)
    AlreadyUnloaded = ErrorCase(msg='Module already unloaded: "{path}"', path=str)
    Unexpected = ErrorCase(
        msg='Module unexpected error: "{path}", details: "{details}"', path=str, details=str
    )


class ModuleLoader:
    def __init__(self) -> None:
        self._injector = ParamsInjector()

    # noinspection PyProtectedMember
    def load_pass(self, conf: ModuleComponentConf) -> Result[ModuleConf, ModuleLoadError]:
        if conf._conf is not None:
            return ModuleLoadError.AlreadyLoaded(path=conf.path).to_result()

        if not (res := self._load_module(conf)):
            return res

        conf._conf = res.unwrap()

        if not conf._conf.enabled:
            return ModuleLoadError.Disabled(path=conf.path).to_result()

        return Ok(conf._conf)

    # noinspection PyProtectedMember
    def unload_pass(self, conf: ModuleComponentConf) -> Result[None, ModuleUnloadError]:
        if conf._conf is None:
            return ModuleUnloadError.AlreadyUnloaded(path=conf.path).to_result()

        if not conf._conf.enabled:
            return ModuleUnloadError.Disabled(path=conf.path).to_result()

        return self._unload_module(conf)

    # noinspection PyProtectedMember
    @staticmethod
    def _get_module_package(conf: ModuleComponentConf) -> str:
        if not conf.path.startswith('.'):
            return conf.path

        path = conf.path
        dots_count = 0

        for c in path[1:]:
            if c == '.':
                dots_count += 1
            else:
                path = path[dots_count + 1 :]
                break

        init_path = conf._init_path
        dots_count = min(dots_count, len(init_path))
        init_path = init_path[0 : len(init_path) - dots_count]
        return '.'.join([*init_path, path])

    def _load_module(self, conf: ModuleComponentConf) -> Result[ModuleConf, ModuleLoadError]:
        module_path = self._get_module_package(conf)
        logger.info('ModuleLoader: Try to load module "{path}"'.format(path=module_path))

        try:
            func = cast(Callable[[...], ModuleConf], import_path(f'{module_path}:__init__'))

        except (ImportError, AttributeError) as e:
            error = ModuleLoadError.WrongImport(path=module_path, details=str(e))
            logger.error(error.message)
            return error.to_result()

        injected_args = self._injector(func, values=conf.args)

        try:
            res = invoke_sync(func, *injected_args.args, **injected_args.kwargs)

        except pydantic.ValidationError as e:
            error = ModuleLoadError.Validation(path=module_path, details=str(e))
            logger.error(error.message)
            return error.to_result()
        except Exception as e:
            error = ModuleLoadError.Unexpected(path=module_path, details=str(e))
            logger.error(error.message)
            return error.to_result()

        if not isinstance(res, ModuleConf):
            error = ModuleLoadError.InvalidConf(path=module_path)
            logger.error(error.message)
            return error.to_result()

        logger.info(
            'ModuleLoader: Module "{path}" loaded successfully'.format(path=module_path)
        )
        return Ok(res)

    # noinspection PyProtectedMember
    def _unload_module(self, conf: ModuleComponentConf) -> Result[None, ModuleUnloadError]:
        module_path = self._get_module_package(conf)
        logger.info('ModuleLoader: Try to unload module "{path}"'.format(path=module_path))

        try:
            func = cast(Callable[[...], None], import_path(f'{module_path}:__fini__'))

        except (ImportError, AttributeError):
            pass
        else:
            injected_args = self._injector(func, types={ModuleConf: conf._conf})

            try:
                invoke_sync(func, *injected_args.args, **injected_args.kwargs)

            except Exception as e:
                error = ModuleUnloadError.Unexpected(path=module_path, details=str(e))
                logger.error(error.message)
                return error.to_result()

        conf, conf._conf = conf._conf, None
        del conf
        del sys.modules[module_path]

        logger.info(
            'ModuleLoader: Module "{path}" unloaded successfully'.format(path=module_path)
        )
        return Ok()
