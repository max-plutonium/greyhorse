import sys
from itertools import chain

import pydantic

from greyhorse.result import Result
from greyhorse.utils.imports import import_path
from greyhorse.utils.injectors import ParamsInjector
from greyhorse.utils.invoke import invoke_sync
from ..entities.application import Application
from ..entities.controller import Controller, ControllerFactoryFn
from ..entities.module import Module, ModuleErrorsItem
from ..entities.service import Service, ServiceFactoryFn
from ..errors import ControllerCreationError, CtrlFactoryNotFoundError, InvalidModuleConfError, ModuleCreationError, \
    ModuleLoadError, ModuleUnloadError, ModuleValidationError, ServiceCreationError, ServiceFactoryNotFoundError
from ..schemas.controller import ControllerConf
from ..schemas.module import ModuleConf, ModuleDesc
from ..schemas.service import ServiceConf
from ...i18n import tr
from ...logging import logger


def _get_module_package(desc: ModuleDesc) -> str:
    if not desc.path.startswith('.'):
        return desc.path

    path = desc.path
    dots_count = 0

    for c in path[1:]:
        if '.' == c:
            dots_count += 1
        else:
            path = path[dots_count + 1:]
            break

    initpath = desc._initpath
    dots_count = min(dots_count, len(initpath))
    initpath = initpath[0:len(initpath) - dots_count]
    return '.'.join(initpath + [path])


class ModuleBuilder:
    def __init__(
        self, app: Application, root_desc: ModuleDesc,
    ):
        self._app = app
        self._injector = ParamsInjector()
        self._key_stack: list[str] = []
        self._root_desc = root_desc

    def load_pass(self, desc: ModuleDesc | None = None) -> Result[ModuleConf | None]:
        desc = desc or self._root_desc

        if not desc.enabled:
            return Result.from_ok()

        res = self._load_module(desc)
        if not res.success:
            return res

        assert desc._conf
        conf = desc._conf

        if not conf.enabled:
            return Result.from_ok()

        for mod_desc in conf.submodules:
            res = self.load_pass(mod_desc)
            if not res.success:
                return res

        return Result.from_ok(conf)

    def create_module_pass(self, desc: ModuleDesc | None = None) -> Result[Module | None]:
        desc = desc or self._root_desc

        if not desc._conf:
            return Result.from_ok()

        current_conf: ModuleConf = desc._conf

        if not current_conf.enabled:
            logger.warn(tr('app.builder.module-disabled').format(path=desc.path))
            return Result.from_ok()

        logger.info(tr('app.builder.try-create').format(path=desc.path))

        values = {
            'name': current_conf.name,
            'conf': current_conf,
        }

        injected_args = self._injector(current_conf.factory, values=values)

        try:
            instance = invoke_sync(current_conf.factory, *injected_args.args, **injected_args.kwargs)
            assert isinstance(instance, Module)

        except Exception as e:
            error = ModuleCreationError(exc=e)
            logger.error(error.message)
            return Result.from_error(error)

        if errors := self._create_controllers(current_conf, instance):
            return Result.from_errors(list(chain.from_iterable([e.errors for e in errors])))

        if errors := self._create_services(current_conf, instance):
            return Result.from_errors(list(chain.from_iterable([e.errors for e in errors])))

        self._key_stack.append(current_conf.name)

        for submodule_desc in current_conf.submodules:
            res = self.create_module_pass(submodule_desc)
            if not res.success:
                return res
            if not res.result:
                continue

            submodule = res.result
            # noinspection PyProtectedMember
            submodule._resolve_claims(instance)
            instance.add_module(submodule.name, submodule)

        submodule_key = '.'.join(self._key_stack)
        self._app.register_module(submodule_key, instance, desc)
        self._key_stack.pop()

        logger.info(tr('app.builder.create-success').format(path=desc.path))
        return Result.from_ok(instance)

    def _load_module(self, desc: ModuleDesc) -> Result:
        if desc._conf is not None:
            return Result.from_ok()

        module_path = _get_module_package(desc)
        logger.info(tr('app.builder.try-load').format(module_init_path=module_path))

        try:
            func = import_path(f'{module_path}:__init__')

        except (ImportError, AttributeError) as e:
            error = ModuleLoadError(exc=e)
            logger.error(error.message)
            return Result.from_error(error)

        injected_args = self._injector(func, values=desc.args)

        try:
            res = invoke_sync(func, *injected_args.args, **injected_args.kwargs)

        except pydantic.ValidationError as e:
            error = ModuleValidationError(detail=str(e))
            logger.error(error.message)
            return Result.from_error(error)
        except Exception as e:
            error = ModuleLoadError(exc=e)
            logger.error(error.message)
            return Result.from_error(error)

        if not isinstance(res, ModuleConf):
            error = InvalidModuleConfError(module_init_path=module_path)
            logger.error(error.message)
            return Result.from_error(error)

        logger.info(tr('app.builder.load-success').format(module_init_path=module_path))
        desc._conf = res
        return Result.from_ok()

    def _create_controller(
        self, module: Module, conf: ControllerConf, factory: ControllerFactoryFn,
    ) -> Result[Controller]:
        logger.info(tr('app.builder.try-ctrl').format(name=conf.name))
        values = {'name': conf.name, **conf.args}
        injected_args = self._injector(factory, values=values)

        try:
            res = factory(*injected_args.args, **injected_args.kwargs)

        except Exception as e:
            error = ControllerCreationError(exc=e)
            logger.error(error.message)
            return Result.from_error(error)

        if not res.success:
            return res

        instance = res.result

        res = instance.check_operator_mapping(conf.operator_mapping)
        if not res.success:
            return res

        key_mapping = res.result
        module.add_controller(
            conf.key, instance, name=conf.name,
            key_mapping=key_mapping,
            resources_read=conf.resources_read,
            resources_write=conf.resources_write,
            providers_read=conf.providers_read,
            operators_read=conf.operators_read,
        )

        logger.info(tr('app.builder.ctrl-success').format(name=conf.name))
        return Result.from_ok(instance)

    def _create_controllers(self, module_conf: ModuleConf, instance: Module) -> list[ModuleErrorsItem]:
        errors = []

        for conf in module_conf.controllers:
            if factory := module_conf.controller_factories.get(conf.key):
                res = self._create_controller(instance, conf, factory)
                if not res.success:
                    errors.append(ModuleErrorsItem(where='controller', name=conf.name, errors=res.errors))
            else:
                error = CtrlFactoryNotFoundError(key=str(conf.key.__name__))
                logger.error(error.message)
                errors.append(ModuleErrorsItem(where='controller', name=conf.name, errors=[error]))

        return errors

    def _create_service(
        self, module: Module, conf: ServiceConf, factory: ServiceFactoryFn,
    ) -> Result[Service]:
        logger.info(tr('app.builder.try-service').format(name=conf.name))
        values = {'name': conf.name, **conf.args}
        injected_args = self._injector(factory, values=values)

        try:
            res = factory(*injected_args.args, **injected_args.kwargs)

        except Exception as e:
            error = ServiceCreationError(exc=e)
            logger.error(error.message)
            return Result.from_error(error)

        if not res.success:
            return res

        instance = res.result

        res = instance.check_provider_mapping(conf.provider_mapping)
        if not res.success:
            return res

        prov_key_mapping = res.result

        res = instance.check_operator_mapping(conf.operator_mapping)
        if not res.success:
            return res

        op_key_mapping = res.result

        module.add_service(
            conf.key, instance, name=conf.name,
            op_key_mapping=op_key_mapping,
            prov_key_mapping=prov_key_mapping,
            resources_read=conf.resources_read,
            providers_read=conf.providers_read,
            operators_read=conf.operators_read,
        )

        submodule_key = '.'.join(self._key_stack)
        self._app.register_service(f'{submodule_key}.{conf.name}', instance)

        logger.info(tr('app.builder.service-success').format(name=conf.name))
        return Result.from_ok(instance)

    def _create_services(self, module_conf: ModuleConf, instance: Module) -> list[ModuleErrorsItem]:
        errors = []

        for conf in module_conf.services:
            if factory := module_conf.service_factories.get(conf.key):
                res = self._create_service(instance, conf, factory)
                if not res.success:
                    errors.append(ModuleErrorsItem(where='service', name=conf.name, errors=res.errors))
            else:
                error = ServiceFactoryNotFoundError(key=str(conf.key.__name__))
                logger.error(error.message)
                errors.append(ModuleErrorsItem(where='service', name=conf.name, errors=[error]))

        return errors


class ModuleTerminator:
    def __init__(
        self, app: Application, root_desc: ModuleDesc,
    ):
        self._app = app
        self._injector = ParamsInjector()
        self._key_stack: list[str] = []
        self._root_desc = root_desc

    def unload_pass(self, desc: ModuleDesc | None = None) -> Result:
        desc = desc or self._root_desc

        if not desc.enabled or not desc._conf:
            return Result.from_ok()

        conf = desc._conf

        if not conf.enabled:
            return Result.from_ok()

        for mod_desc in conf.submodules:
            res = self.unload_pass(mod_desc)
            if not res.success:
                return res

        return self._unload_module(desc)

    def destroy_module_pass(
        self, desc: ModuleDesc | None = None, parent: Module | None = None,
    ) -> Result:
        desc = desc or self._root_desc

        if not desc._conf:
            return Result.from_ok()

        logger.info(tr('app.builder.try-destroy').format(path=desc.path))

        current_conf: ModuleConf = desc._conf
        self._key_stack.append(current_conf.name)
        submodule_key = '.'.join(self._key_stack)
        current = self._app.get_module(submodule_key)

        for submodule_desc in current_conf.submodules:
            res = self.destroy_module_pass(submodule_desc, current)
            if not res.success:
                return res

        if parent:
            parent.remove_module(current_conf.name)

        for srv in current.service_list:
            self._app.unregister_service(f'{submodule_key}.{srv.name}')

        self._app.unregister_module(submodule_key)
        self._key_stack.pop()

        logger.info(tr('app.builder.destroy-success').format(path=desc.path))
        return Result.from_ok()

    def _unload_module(self, desc: ModuleDesc) -> Result:
        if desc._conf is None:
            return Result.from_ok()

        module_path = _get_module_package(desc)
        logger.info(tr('app.builder.try-unload').format(module_init_path=module_path))

        try:
            func = import_path(f'{module_path}:__fini__')

        except (ImportError, AttributeError):
            pass
        else:
            injected_args = self._injector(func, types={ModuleConf: desc._conf})

            try:
                invoke_sync(func, *injected_args.args, **injected_args.kwargs)

            except Exception as e:
                error = ModuleUnloadError(exc=e)
                logger.error(error.message)
                return Result.from_error(error)

        logger.info(tr('app.builder.unload-success').format(module_init_path=module_path))
        desc._conf = None
        del sys.modules[module_path]
        return Result.from_ok()
