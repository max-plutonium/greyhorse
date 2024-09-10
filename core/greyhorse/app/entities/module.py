from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import Provider
from greyhorse.app.entities.components import Component
from greyhorse.app.private.component import ResourceManager
from greyhorse.app.registries import MutDictRegistry
from greyhorse.app.schemas.components import ModuleConf
from greyhorse.error import Error, ErrorCase
from greyhorse.logging import logger
from greyhorse.result import Ok, Result


class ModuleError(Error):
    namespace = 'greyhorse.app.module'

    Component = ErrorCase(
        msg='{path}: Component error in module, details: "{details}"', path=str, details=str,
    )

    Resource = ErrorCase(
        msg='{path}: Resource error in module: "{details}"', path=str, details=str,
    )


class Module:
    def __init__(self, path: str, conf: ModuleConf, components: list[Component]) -> None:
        self._conf = conf
        self._path = path
        self._rm = ResourceManager()

        self._operators: list[Operator] = []

        self._imported_providers = MutDictRegistry[type[Provider], Provider]()
        self._private_providers = MutDictRegistry[type[Provider], Provider]()
        self._components: dict[str, Component] = {c.name: c for c in components}

    @property
    def path(self) -> str:
        return self._path

    def add_provider[T](self, prov_type: type[Provider[T]], provider: Provider[T]) -> bool:
        return self._imported_providers.add(prov_type, provider)

    def remove_provider[T](self, prov_type: type[Provider[T]]) -> bool:
        return self._imported_providers.remove(prov_type)

    def add_operator[T](self, operator: Operator[T]) -> bool:
        for prov_conf in self._conf.provider_exports:
            if issubclass(prov_conf.resource, operator.wrapped_type):
                self._operators.append(operator)
                return True
        return False

    def remove_operator[T](self, operator: Operator[T]) -> bool:
        for prov_conf in self._conf.provider_exports:
            if issubclass(prov_conf.resource, operator.wrapped_type):
                self._operators.remove(operator)
                return True
        return False

    def setup(self) -> Result[None, ModuleError]:
        logger.info('{path}: Module setup'.format(path=self._path))

        for prov_conf in self._conf.provider_claims:
            for prov_type in prov_conf.types:
                for _, prov in self._imported_providers.items(
                    lambda t, pt=prov_type: issubclass(t, pt),
                ):
                    self._private_providers.add(prov_type, prov)

        for component in self._components.values():
            comp_conf = self._conf.components[component.name]

            for prov_conf in comp_conf.provider_grants:
                for prov_type in prov_conf.types:
                    for _, prov in self._private_providers.items(
                        lambda t, pt=prov_type: issubclass(t, pt),
                    ):
                        component.add_provider(prov_type, prov)

            if not (
                res := component.setup().map_err(
                    lambda e: ModuleError.Component(path=self._path, details=e.message),
                )
            ):
                return res

            for prov_conf in comp_conf.provider_imports:
                for prov_type in prov_conf.types:
                    if prov := component.get_provider(prov_type).unwrap_or_none():
                        self._private_providers.add(prov_type, prov)

        for op in self._operators:
            if not (
                res := self._rm.setup_resource(op, self._private_providers).map_err(
                    lambda e: ModuleError.Resource(path=self._path, details=e.message),
                )
            ):
                return res

        logger.info('{path}: Module setup successful'.format(path=self._path))
        return Ok(None)

    def teardown(self) -> Result[None, ModuleError]:
        logger.info('{path}: Module teardown'.format(path=self._path))

        if not (
            res := self._rm.teardown().map_err(
                lambda e: ModuleError.Resource(path=self._path, details=e.message),
            )
        ):
            return res

        for component in reversed(self._components.values()):
            comp_conf = self._conf.components[component.name]

            for prov_conf in reversed(comp_conf.provider_imports):
                for prov_type in reversed(prov_conf.types):
                    if prov := component.get_provider(prov_type).unwrap_or_none():
                        self._private_providers.remove(prov_type, prov)

            if not (
                res := component.teardown().map_err(
                    lambda e: ModuleError.Component(path=self._path, details=e.message),
                )
            ):
                return res

            for prov_conf in reversed(comp_conf.provider_grants):
                for prov_type in reversed(prov_conf.types):
                    component.remove_provider(prov_type)

        for prov_conf in reversed(self._conf.provider_claims):
            for prov_type in reversed(prov_conf.types):
                for _, prov in self._imported_providers.items(
                    lambda t, pt=prov_type: issubclass(t, pt),
                ):
                    self._private_providers.remove(prov_type, prov)

        logger.info('{path}: Module teardown successful'.format(path=self._path))
        return Ok(None)
