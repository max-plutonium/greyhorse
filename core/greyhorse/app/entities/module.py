from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import Provider
from greyhorse.app.entities.components import Component
from greyhorse.app.registries import MutDictRegistry
from greyhorse.app.schemas.components import ModuleConf
from greyhorse.error import Error, ErrorCase
from greyhorse.logging import logger
from greyhorse.maybe import Maybe
from greyhorse.result import Result, Ok


class ModuleError(Error):
    namespace = 'greyhorse.app.module'

    Component = ErrorCase(
        msg='{path}: Component error in module, details: "{details}"',
        path=str, details=str,
    )


class Module:
    def __init__(
        self, path: str, conf: ModuleConf, components: list[Component],
        operator_reg: MutDictRegistry[type, Operator],
    ):
        self._conf = conf
        self._path = path

        self._operator_reg = operator_reg
        self._private_providers = MutDictRegistry[type[Provider], Provider]()
        self._public_providers = MutDictRegistry[type[Provider], Provider]()
        self._components: dict[str, Component] = {c.name: c for c in components}

    @property
    def path(self) -> str:
        return self._path

    def get_component(self, name: str) -> Maybe[Component]:
        return Maybe(self._components.get(name))

    def get_provider[P: Provider](self, type_: type[P]) -> Maybe[P]:
        return self._public_providers.get(type_)

    def add_provider(self, type_: type[Provider], provider: Provider) -> bool:
        return self._public_providers.add(type_, provider)

    def remove_provider(self, type_: type[Provider], provider: Provider) -> bool:
        return self._public_providers.remove(type_, provider)

    def setup(self) -> Result[None, ModuleError]:
        logger.info('{path}: Module setup'.format(path=self._path))

        for prov_conf in self._conf.provider_claims:
            for prov_type in prov_conf.types:
                for _, prov in self._public_providers.items(lambda t: issubclass(t, prov_type)):
                    self._private_providers.add(prov_type, prov)

        for component in self._components.values():
            if not (res := component.setup(self._private_providers, self._private_providers).map_err(
                lambda e: ModuleError.Component(path=self._path, details=e.message)
            )):
                return res

        for prov_conf in self._conf.provider_exports:
            for prov_type in prov_conf.types:
                for _, prov in self._private_providers.items(lambda t: issubclass(t, prov_type)):
                    self._public_providers.add(prov_type, prov)

        logger.info('{path}: Module setup successful'.format(path=self._path))
        return Ok(None)

    def teardown(self) -> Result[None, ModuleError]:
        logger.info('{path}: Module teardown'.format(path=self._path))

        for prov_conf in reversed(self._conf.provider_exports):
            for prov_type in prov_conf.types:
                for _, prov in self._private_providers.items(lambda t: issubclass(t, prov_type)):
                    self._public_providers.remove(prov_type, prov)

        for component in reversed(self._components.values()):
            if not (res := component.teardown(self._private_providers, self._private_providers).map_err(
                lambda e: ModuleError.Component(path=self._path, details=e.message)
            )):
                return res

        for prov_conf in reversed(self._conf.provider_claims):
            for prov_type in prov_conf.types:
                for _, prov in self._public_providers.items(lambda t: issubclass(t, prov_type)):
                    self._private_providers.remove(prov_type, prov)

        logger.info('{path}: Module teardown successful'.format(path=self._path))
        return Ok(None)
