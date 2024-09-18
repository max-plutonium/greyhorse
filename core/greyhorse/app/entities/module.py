from typing import Any

from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import Provider
from greyhorse.app.abc.visitor import Visitor
from greyhorse.app.entities.components import Component
from greyhorse.app.private.res_manager import ResourceManager
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

        self._resources = MutDictRegistry[type, Any]()
        self._providers = MutDictRegistry[type[Provider], Provider]()
        self._components: dict[str, Component] = {c.name: c for c in components}

    @property
    def path(self) -> str:
        return self._path

    def accept_visitor(self, visitor: Visitor) -> None:
        visitor.start_module(self)
        for comp in self._components.values():
            comp.accept_visitor(visitor)
        visitor.finish_module(self)

    def add_provider[T](self, prov_type: type[Provider[T]], provider: Provider[T]) -> bool:
        for prov_claim in self._conf.provider_claims:
            if prov_type in prov_claim.providers:
                return self._providers.add(prov_type, provider)
        return False

    def remove_provider[T](self, prov_type: type[Provider[T]]) -> bool:
        for prov_claim in self._conf.provider_claims:
            if prov_type in prov_claim.providers:
                return self._providers.remove(prov_type)
        return False

    def add_resource(self, res_type: type, resource: Any) -> bool:
        if res_type in self._conf.resource_claims:
            return self._resources.add(res_type, resource)
        return False

    def remove_resource(self, res_type: type) -> bool:
        if res_type in self._conf.resource_claims:
            return self._resources.remove(res_type)
        return False

    def add_operator[T](self, operator: Operator[T]) -> bool:
        for res_type in self._conf.can_provide:
            if issubclass(res_type, operator.wrapped_type):
                self._operators.append(operator)
                return True
        return False

    def remove_operator[T](self, operator: Operator[T]) -> bool:
        for res_type in self._conf.can_provide:
            if issubclass(res_type, operator.wrapped_type):
                self._operators.remove(operator)
                return True
        return False

    def setup(self) -> Result[None, ModuleError]:
        logger.info('{path}: Module setup'.format(path=self._path))

        for component in self._components.values():
            comp_conf = self._conf.components[component.name]

            for res_type in comp_conf.resource_grants:
                if res := self._resources.get(res_type).unwrap_or_none():
                    component.add_resource(res_type, res)

            for prov_conf in comp_conf.provider_grants:
                for prov_type in prov_conf.providers:
                    for _, prov in self._providers.items(
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
                for prov_type in prov_conf.providers:
                    if prov := component.get_provider(prov_type).unwrap_or_none():
                        self._providers.add(prov_type, prov)

        for op in self._operators:
            if not (
                res := self._rm.setup_resource(op, self._providers).map_err(
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
                for prov_type in reversed(prov_conf.providers):
                    if prov := component.get_provider(prov_type).unwrap_or_none():
                        self._providers.remove(prov_type, prov)

            if not (
                res := component.teardown().map_err(
                    lambda e: ModuleError.Component(path=self._path, details=e.message),
                )
            ):
                return res

            for prov_conf in reversed(comp_conf.provider_grants):
                for prov_type in reversed(prov_conf.providers):
                    component.remove_provider(prov_type)

            for res_type in reversed(comp_conf.resource_grants):
                component.remove_resource(res_type)

        logger.info('{path}: Module teardown successful'.format(path=self._path))
        return Ok(None)
