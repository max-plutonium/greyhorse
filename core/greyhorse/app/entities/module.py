from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Self, TYPE_CHECKING, cast, override

from greyhorse.result import Error, Result
from greyhorse.utils.invoke import invoke_sync
from .controller import Controller, ControllerKey
from .deps import DepsOperator, DepsProvider
from .operator import OperatorFactoryFn, OperatorFactoryRegistry, OperatorKey
from .providers import ProviderFactoryFn, ProviderFactoryRegistry, ProviderKey
from .service import Service, ServiceKey
from ..errors import NoOpFoundForPattern, OpPolicyViolation, ProvClaimPolicyViolation
from ..schemas.components import OperatorPolicy, ProviderPolicy, ResourcePolicy
from ..utils.registry import DictRegistry, KeyMapping, ReadonlyRegistry
from ...i18n import tr
from ...logging import logger

if TYPE_CHECKING:
    from ..schemas.module import ModuleConf


@dataclass(slots=True, frozen=True)
class ModuleProviderItem:
    key: ProviderKey
    instance: ProviderFactoryFn
    name: str | None = None


@dataclass(slots=True, frozen=True)
class ModuleErrorsItem:
    where: Literal['module'] | Literal['controller'] | Literal['service'] | Literal['provider']
    name: str
    errors: list[Error] | None = None


class ModuleDepsProvider(DepsProvider):
    def __init__(
        self, op_registry: OperatorFactoryRegistry,
        prov_registry: ProviderFactoryRegistry,
        deps_registry: ReadonlyRegistry[Any, Any],
        resources_read: list[ResourcePolicy],
        providers_read: list[ProviderPolicy],
        operators_read: list[OperatorPolicy],
    ):
        self._op_registry = op_registry
        self._prov_registry = prov_registry
        self._deps_registry = deps_registry
        self._resources_read = {p.key: p.name_pattern for p in resources_read}
        self._providers_read = {p.key: p.name_pattern for p in providers_read}
        self._operators_read = {p.key: p.name_pattern for p in operators_read}

    @override
    def get_operator_factory(
        self, key: OperatorKey, name: str | None = None,
    ) -> OperatorFactoryFn | None:
        if key in self._operators_read:
            name_pattern = self._operators_read[key]
            if name_pattern is not None:
                if name is None or not name_pattern.match(name):
                    return None
            return self._op_registry.get(key, name)
        return None

    @override
    def get_provider_factory(
        self, key: ProviderKey, name: str | None = None,
    ) -> ProviderFactoryFn | None:
        if key in self._providers_read:
            name_pattern = self._providers_read[key]
            if name_pattern is not None:
                if name is None or not name_pattern.match(name):
                    return None
            return self._prov_registry.get(key, name)
        return None

    @override
    def get_resource(
        self, key: Any, name: str | None = None,
    ) -> Any | None:
        if key in self._resources_read:
            name_pattern = self._resources_read[key]
            if name_pattern is not None:
                if name is None or not name_pattern.match(name):
                    return None
            return self._deps_registry.get(key, name)
        return None


class ModuleDepsOperator(DepsOperator):
    def __init__(
        self, deps_registry: DictRegistry[Any, Any],
        resources_write: list[ResourcePolicy],
    ):
        self._deps_registry = deps_registry
        self._resources_write = {p.key: p.name_pattern for p in resources_write}

    @override
    def set_resource(
        self, key: Any, instance: Any, name: str | None = None,
    ) -> bool:
        if key in self._resources_write:
            name_pattern = self._resources_write[key]
            if name_pattern is not None:
                if name is None or not name_pattern.match(name):
                    return False
            return self._deps_registry.set(key, instance, name)
        return False

    @override
    def reset_resource(
        self, key: Any, name: str | None = None,
    ) -> bool:
        if key in self._resources_write:
            name_pattern = self._resources_write[key]
            if name_pattern is not None:
                if name is None or not name_pattern.match(name):
                    return False
            return self._deps_registry.reset(key, name)
        return False


class Module:
    def __init__(self, name: str, conf: 'ModuleConf'):
        self._name = name
        self._conf = conf
        self._modules: dict[str, Self] = {}
        self._controllers = DictRegistry[ControllerKey, Controller]()
        self._services = DictRegistry[ServiceKey, Service]()
        self._provider_factories = DictRegistry[ProviderKey, ProviderFactoryFn]()
        self._operator_factories = DictRegistry[OperatorKey, OperatorFactoryFn]()
        self._deps_registry = DictRegistry[Any, Any]()

    @property
    def name(self) -> str:
        return self._name

    @property
    def config(self) -> 'ModuleConf':
        return self._conf

    def _create_module_deps_provider(
        self, resources_read: list[ResourcePolicy] | None = None,
        providers_read: list[ProviderPolicy] | None = None,
        operators_read: list[OperatorPolicy] | None = None,
    ):
        return ModuleDepsProvider(
            op_registry=self._operator_factories,
            prov_registry=self._provider_factories,
            deps_registry=self._deps_registry,
            resources_read=resources_read or [],
            providers_read=providers_read or [],
            operators_read=operators_read or [],
        )

    def add_controller(
        self, key: ControllerKey, instance: Controller, name: str | None = None,
        key_mapping: Mapping[OperatorKey, KeyMapping[OperatorKey]] | None = None,
        resources_read: list[ResourcePolicy] | None = None,
        resources_write: list[ResourcePolicy] | None = None,
        providers_read: list[ProviderPolicy] | None = None,
        operators_read: list[OperatorPolicy] | None = None,
    ):
        if self._controllers.set(key, instance, name=name):
            self._operator_factories.merge(instance.operator_factories, key_mapping)

        deps_prov = self._create_module_deps_provider(resources_read, providers_read, operators_read)
        instance.set_deps_provider(deps_prov)

        deps_op = ModuleDepsOperator(self._deps_registry, resources_write or [])
        instance.set_deps_operator(deps_op)

    def remove_controller(
        self, key: ControllerKey,
        key_mapping: Mapping[OperatorKey, KeyMapping[OperatorKey]] | None = None,
        name: str | None = None,
    ):
        if instance := self._controllers.get(key, name=name):
            self._operator_factories.subtract(instance.operator_factories, key_mapping)
        self._controllers.reset(key, name=name)
        instance.reset_deps_provider()

    def get_controller(self, key: ControllerKey, name: str | None = None) -> Controller | None:
        if instance := self._controllers.get(key, name=name):
            return cast(key, instance)
        return None

    def add_service(
        self, key: ServiceKey, instance: Service, name: str | None = None,
        op_key_mapping: Mapping[OperatorKey, KeyMapping[OperatorKey]] | None = None,
        prov_key_mapping: Mapping[ProviderKey, KeyMapping[ProviderKey]] | None = None,
        resources_read: list[ResourcePolicy] | None = None,
        providers_read: list[ProviderPolicy] | None = None,
        operators_read: list[OperatorPolicy] | None = None,
    ):
        if self._services.set(key, instance, name=name):
            self._operator_factories.merge(instance.operator_factories, op_key_mapping)
            self._provider_factories.merge(instance.provider_factories, prov_key_mapping)

        deps_prov = self._create_module_deps_provider(resources_read, providers_read, operators_read)
        instance.set_deps_provider(deps_prov)

    def remove_service(
        self, key: ServiceKey,
        op_key_mapping: Mapping[OperatorKey, KeyMapping[OperatorKey]] | None = None,
        prov_key_mapping: Mapping[ProviderKey, KeyMapping[ProviderKey]] | None = None,
        name: str | None = None,
    ):
        if instance := self._services.get(key, name=name):
            self._operator_factories.subtract(instance.operator_factories, op_key_mapping)
            self._provider_factories.subtract(instance.provider_factories, prov_key_mapping)
        self._services.reset(key, name=name)
        instance.reset_deps_provider()

    def get_service(self, key: ServiceKey, name: str | None = None) -> Service | None:
        if instance := self._services.get(key, name=name):
            return cast(key, instance)
        return None

    @property
    def module_names(self) -> list[str]:
        return list(self._modules.keys())

    @property
    def controllers_list(self) -> list[Controller]:
        result = []

        for key in self._controllers.list_keys():
            for name in self._controllers.get_names(key):
                result.append(self._controllers.get(key, name))

        return result

    @property
    def service_list(self) -> list[Service]:
        result = []

        for key in self._services.list_keys():
            for name in self._services.get_names(key):
                result.append(self._services.get(key, name))

        return result

    def add_module(self, name: str, instance: Self):
        if name not in self._modules:
            self._modules[name] = instance
            res = self._get_sub_exports(instance)
            if res.success:
                self._operator_factories.merge(instance.operator_factories, res.result)

    def remove_module(self, name: str):
        if instance := self._modules.pop(name, None):
            res = self._get_sub_exports(instance)
            if res.success:
                self._operator_factories.subtract(instance.operator_factories, res.result)

    def get_module(self, name) -> Self | None:
        return self._modules.get(name)

    @property
    def provider_factories(self) -> ProviderFactoryRegistry:
        return self._provider_factories

    @property
    def operator_factories(self) -> OperatorFactoryRegistry:
        return self._operator_factories

    def satisfy_provider_claims(self, items: list[ModuleProviderItem]) -> list[ModuleErrorsItem]:
        errors: list[ModuleErrorsItem] = []
        items_set: dict[ProviderKey, dict[str | None, ProviderFactoryFn]] = defaultdict(dict)
        for item in items:
            items_set[item.key][item.name] = item.instance

        for claim in self.config.provider_claims:
            result = False

            for name, instance in items_set.get(claim.key, {}).items():
                if claim.name_pattern is not None:
                    if claim.name_pattern.match(name):
                        result = self._provider_factories.set(claim.key, instance, name=name)
                        break
                else:
                    result = self._provider_factories.set(claim.key, instance, name=name)

            if not result:
                claim_name = f'{claim.key}' + (f' ("{claim.name_pattern}")' if claim.name_pattern else '')
                error = ProvClaimPolicyViolation(type='module', name=self.name, claim_name=claim_name)
                errors.append(ModuleErrorsItem(
                    where='provider', name=claim_name, errors=[error],
                ))

        for module in self._modules.values():
            sub_errors = module._resolve_claims(self)
            for error_item in sub_errors:
                errors.append(ModuleErrorsItem(
                    where='module', name=module.name, errors=error_item.errors,
                ))

        return errors

    def _resolve_claims(self, parent: Self) -> list[ModuleErrorsItem]:
        errors: list[ModuleErrorsItem] = []

        for claim in self.config.provider_claims:
            result = False
            if claim.name_pattern is not None:
                for name in parent.provider_factories.get_names(claim.key):
                    if claim.name_pattern.match(name):
                        instance = parent.provider_factories.get(claim.key, name)
                        result = self._provider_factories.set(claim.key, instance, name=name)
                        break

            elif instance := parent.provider_factories.get(claim.key):
                result = self._provider_factories.set(claim.key, instance)

            if not result:
                claim_name = f'{claim.key}' + (f' ("{claim.name_pattern}")' if claim.name_pattern else '')
                error = ProvClaimPolicyViolation(type='module', name=self.name, claim_name=claim_name)
                errors.append(ModuleErrorsItem(
                    where='provider', name=claim_name, errors=[error],
                ))

        for module in self._modules.values():
            sub_errors = module._resolve_claims(self)
            for error_item in sub_errors:
                errors.append(ModuleErrorsItem(
                    where='module', name=module.name, errors=error_item.errors,
                ))

        return errors

    def _get_sub_exports(self, submodule: Self) -> Result[Mapping[OperatorKey, KeyMapping[OperatorKey]]]:
        policies_dict = {p.key: p for p in submodule.config.operator_exports}
        key_mapping = {}

        for key in submodule._operator_factories.list_keys():
            if key not in policies_dict:
                error = OpPolicyViolation(type='module', name=self.name, key=str(key.__name__))
                logger.error(error.message)
                return Result.from_error(error)

            name_pattern = policies_dict[key].name_pattern

            if name_pattern is None:
                key_mapping[key] = KeyMapping[OperatorKey](map_to=key)
                continue

            names = []

            for name in submodule._operator_factories.get_names(key):
                if name_pattern.match(name):
                    names.append(name)

            if not names:
                error = NoOpFoundForPattern(
                    type='module', name=self.name, key=str(key.__name__), pattern=name_pattern,
                )
                logger.error(error.message)
                return Result.from_error(error)

            key_mapping[key] = KeyMapping[OperatorKey](map_to=key, names=names)

        return Result.from_ok(key_mapping)

    def create(self) -> list[ModuleErrorsItem]:
        errors: list[ModuleErrorsItem] = []
        logger.info(tr('app.entities.module.create-start').format(name=self.name))

        for key in self._services.list_keys():
            for name in self._services.get_names(key):
                instance = self._services.get(key, name)
                res = invoke_sync(instance.create)
                if not res.success:
                    errors.append(ModuleErrorsItem(
                        where='service', name=name, errors=res.errors,
                    ))
                else:
                    logger.info(tr('app.entities.module.service-created').format(name=name))

        for module in self._modules.values():
            sub_errors = invoke_sync(module.create)
            for error_item in sub_errors:
                errors.append(ModuleErrorsItem(
                    where='module', name=module.name, errors=error_item.errors,
                ))

        for key in self._controllers.list_keys():
            for name in self._controllers.get_names(key):
                instance = self._controllers.get(key, name)
                res = invoke_sync(instance.create)
                if not res.success:
                    errors.append(ModuleErrorsItem(
                        where='controller', name=name, errors=res.errors,
                    ))
                else:
                    logger.info(tr('app.entities.module.ctrl-created').format(name=name))

        logger.info(tr('app.entities.module.create-finish').format(name=self.name))
        return errors

    def destroy(self) -> list[ModuleErrorsItem]:
        errors: list[ModuleErrorsItem] = []
        logger.info(tr('app.entities.module.destroy-start').format(name=self.name))

        for key in self._controllers.list_keys():
            for name in self._controllers.get_names(key):
                instance = self._controllers.get(key, name)
                res = invoke_sync(instance.destroy)
                if not res.success:
                    errors.append(ModuleErrorsItem(
                        where='controller', name=name, errors=res.errors,
                    ))
                else:
                    logger.info(tr('app.entities.module.ctrl-destroyed').format(name=name))

        for module in self._modules.values():
            sub_errors = invoke_sync(module.destroy)
            for error_item in sub_errors:
                errors.append(ModuleErrorsItem(
                    where='module', name=module.name, errors=error_item.errors,
                ))

        for key in self._services.list_keys():
            for name in self._services.get_names(key):
                instance = self._services.get(key, name)
                res = invoke_sync(instance.destroy)
                if not res.success:
                    errors.append(ModuleErrorsItem(
                        where='service', name=name, errors=res.errors,
                    ))
                else:
                    logger.info(tr('app.entities.module.service-destroyed').format(name=name))

        logger.info(tr('app.entities.module.destroy-finish').format(name=self.name))
        return errors

    def start(self):
        logger.info(tr('app.entities.module.start-start').format(name=self.name))

        for key in self._controllers.list_keys():
            for name in self._controllers.get_names(key):
                instance = self._controllers.get(key, name)
                invoke_sync(instance.start)
                logger.info(tr('app.entities.module.ctrl-started').format(name=name))

        for module in self._modules.values():
            module.start()

        for key in self._services.list_keys():
            for name in self._services.get_names(key):
                instance = self._services.get(key, name)
                invoke_sync(instance.start)
                logger.info(tr('app.entities.module.service-started').format(name=name))

        logger.info(tr('app.entities.module.start-finish').format(name=self.name))

    def stop(self):
        logger.info(tr('app.entities.module.stop-start').format(name=self.name))

        for key in self._services.list_keys():
            for name in self._services.get_names(key):
                instance = self._services.get(key, name)
                invoke_sync(instance.stop)
                logger.info(tr('app.entities.module.service-stopped').format(name=name))

        for module in reversed(self._modules.values()):
            module.stop()

        for key in self._controllers.list_keys():
            for name in self._controllers.get_names(key):
                instance = self._controllers.get(key, name)
                invoke_sync(instance.stop)
                logger.info(tr('app.entities.module.ctrl-stopped').format(name=name))

        logger.info(tr('app.entities.module.stop-finish').format(name=self.name))
