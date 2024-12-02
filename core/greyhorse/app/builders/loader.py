import sys
import types
from collections.abc import Callable
from typing import cast

import pydantic

from greyhorse.error import Error, ErrorCase
from greyhorse.logging import logger
from greyhorse.result import Ok, Result
from greyhorse.utils.imports import get_relative_path, import_path
from greyhorse.utils.injectors import ParamsInjector
from greyhorse.utils.invoke import invoke_sync

from ..schemas.components import ModuleComponentConf, ModuleConf


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
    __slots__ = ('_injector', '_module')

    def __init__(self) -> None:
        self._injector = ParamsInjector()
        self._module: types.ModuleType | None = None

    @property
    def module(self) -> types.ModuleType:
        return self._module

    def load_pass(self, conf: ModuleComponentConf) -> Result[ModuleConf, ModuleLoadError]:
        if conf._conf is not None:  # noqa: SLF001
            return ModuleLoadError.AlreadyLoaded(path=conf.path).to_result()

        if not (res := self._load_module(conf)):
            return res

        conf._conf = res.unwrap()  # noqa: SLF001

        if not conf._conf.enabled:  # noqa: SLF001
            return ModuleLoadError.Disabled(path=conf.path).to_result()

        return Ok(conf._conf)  # noqa: SLF001

    def unload_pass(self, conf: ModuleComponentConf) -> Result[None, ModuleUnloadError]:
        if conf._conf is None:  # noqa: SLF001
            return ModuleUnloadError.AlreadyUnloaded(path=conf.path).to_result()

        if not conf._conf.enabled:  # noqa: SLF001
            return ModuleUnloadError.Disabled(path=conf.path).to_result()

        return self._unload_module(conf)

    def _load_module(self, conf: ModuleComponentConf) -> Result[ModuleConf, ModuleLoadError]:
        module_path = get_relative_path(conf._init_path, conf.path)  # noqa: SLF001
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

        self._module = sys.modules[sys.modules[module_path].__package__]

        logger.info(
            'ModuleLoader: Module "{path}" loaded successfully'.format(path=module_path)
        )
        return Ok(res)

    def _unload_module(self, conf: ModuleComponentConf) -> Result[None, ModuleUnloadError]:
        module_path = get_relative_path(conf._init_path, conf.path)  # noqa: SLF001
        logger.info('ModuleLoader: Try to unload module "{path}"'.format(path=module_path))

        try:
            func = cast(Callable[[...], None], import_path(f'{module_path}:__fini__'))

        except (ImportError, AttributeError):
            pass
        else:
            injected_args = self._injector(func, types={ModuleConf: conf._conf})  # noqa: SLF001

            try:
                invoke_sync(func, *injected_args.args, **injected_args.kwargs)

            except Exception as e:
                error = ModuleUnloadError.Unexpected(path=module_path, details=str(e))
                logger.error(error.message)
                return error.to_result()

        conf, conf._conf = conf._conf, None  # noqa: SLF001
        del conf
        del sys.modules[module_path]

        logger.info(
            'ModuleLoader: Module "{path}" unloaded successfully'.format(path=module_path)
        )
        return Ok()
