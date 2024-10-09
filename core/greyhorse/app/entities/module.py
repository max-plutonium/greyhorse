from typing import Any

from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import Provider
from greyhorse.app.abc.visitor import Visitor
from greyhorse.app.entities.components import Component
from greyhorse.app.private.res_manager import ResourceManager
from greyhorse.app.registries import MutDictRegistry, MutNamedDictRegistry
from greyhorse.app.schemas.components import ModuleConf
from greyhorse.error import Error, ErrorCase
from greyhorse.logging import logger
from greyhorse.maybe import Just, Maybe, Nothing
from greyhorse.result import Ok, Result


class ModuleError(Error):
    namespace = 'greyhorse.app.module'

    Component = ErrorCase(
        msg='{path}: Component error in module, details: "{details}"', path=str, details=str
    )

    Resource = ErrorCase(
        msg='{path}: Resource error in module: "{details}"', path=str, details=str
    )


class Module:
    def __init__(self, path: str, conf: ModuleConf, components: list[Component]) -> None:
        self._conf = conf
        self._path = path
        self._rm = ResourceManager()

        self._operators: list[Operator] = []

        self._resources = MutNamedDictRegistry[type, Any]()
        self._providers = MutDictRegistry[type[Provider], Provider]()
        self._components: dict[str, Component] = {c.name: c for c in components}

    @property
    def path(self) -> str:
        return self._path

    @property
    def conf(self) -> ModuleConf:
        return self._conf

    def accept_visitor(self, visitor: Visitor) -> None:
        visitor.start_module(self)
        for comp in self._components.values():
            comp.accept_visitor(visitor)
        visitor.finish_module(self)

    def get_provider[P: Provider](self, prov_type: type[P]) -> Maybe[P]:
        if prov_type in self._conf.providers:
            return (
                self._rm.find_provider(prov_type, self._providers).map(Just).unwrap_or(Nothing)
            )
        return Nothing

    def add_provider[T](self, prov_type: type[Provider[T]], provider: Provider[T]) -> bool:
        if prov_type in self._conf.provider_claims:
            return self._providers.add(prov_type, provider)
        return False

    def remove_provider[T](self, prov_type: type[Provider[T]]) -> bool:
        if prov_type in self._conf.provider_claims:
            return self._providers.remove(prov_type)
        return False

    def add_resource(self, res_type: type, resource: Any, name: str | None = None) -> bool:  # noqa: ANN401
        if res_type in self._conf.resource_claims:
            return self._resources.add(res_type, resource, name=name)
        return False

    def remove_resource(self, res_type: type, name: str | None = None) -> bool:
        if res_type in self._conf.resource_claims:
            return self._resources.remove(res_type, name=name)
        return False

    def add_operator[T](self, operator: Operator[T]) -> bool:
        for res_type in self._conf.operators:
            if issubclass(res_type, operator.wrapped_type):
                self._operators.append(operator)
                return True
        return False

    def remove_operator[T](self, operator: Operator[T]) -> bool:
        for res_type in self._conf.operators:
            if issubclass(res_type, operator.wrapped_type):
                self._operators.remove(operator)
                return True
        return False

    def setup(self) -> Result[None, ModuleError]:
        logger.info('{path}: Module setup'.format(path=self._path))

        for component in self._components.values():
            comp_conf = self._conf.components[component.name]

            for res_type in comp_conf.resource_claims:
                if res := self._resources.get(res_type).unwrap_or_none():
                    component.add_resource(res_type, res)

            # XXX: component providers
            # for prov_type in prov_conf.providers:
            #     for _, prov in self._providers.items(
            #         lambda t, pt=prov_type: issubclass(t, pt)
            #     ):
            #         component.add_provider(prov_type, prov)

            if not (
                res := component.create().map_err(
                    lambda e: ModuleError.Component(path=self._path, details=e.message)
                )
            ):
                return res

            for res_type in comp_conf.operators:
                for op in component.get_operators(res_type):  # type: ignore
                    if not (
                        res := self._rm.setup_resource(op, self._providers).map_err(
                            lambda e: ModuleError.Resource(path=self._path, details=e.message)
                        )
                    ):
                        return res  # type: ignore

            if not (
                res := component.setup().map_err(
                    lambda e: ModuleError.Component(path=self._path, details=e.message)
                )
            ):
                return res

            for prov_type in comp_conf.providers:
                if prov := component.get_provider(prov_type).unwrap_or_none():
                    self._providers.add(prov_type, prov)

        for op in self._operators:
            if not (
                res := self._rm.setup_resource(op, self._providers).map_err(
                    lambda e: ModuleError.Resource(path=self._path, details=e.message)
                )
            ):
                return res  # type: ignore

        logger.info('{path}: Module setup successful'.format(path=self._path))
        return Ok()

    def teardown(self) -> Result[None, ModuleError]:
        logger.info('{path}: Module teardown'.format(path=self._path))

        for op in reversed(self._operators):
            if not (
                res := self._rm.teardown_resource(op).map_err(
                    lambda e: ModuleError.Resource(path=self._path, details=e.message)
                )
            ):
                return res  # type: ignore

        for component in reversed(self._components.values()):
            comp_conf = self._conf.components[component.name]

            for prov_type in reversed(comp_conf.providers):
                self._providers.remove(prov_type)

            if not (
                res := component.teardown().map_err(
                    lambda e: ModuleError.Component(path=self._path, details=e.message)
                )
            ):
                return res

            for res_type in reversed(comp_conf.operators):
                for op in component.get_operators(res_type):  # type: ignore
                    if not (
                        res := self._rm.teardown_resource(op).map_err(
                            lambda e: ModuleError.Resource(path=self._path, details=e.message)
                        )
                    ):
                        return res  # type: ignore

            if not (
                res := component.destroy().map_err(
                    lambda e: ModuleError.Component(path=self._path, details=e.message)
                )
            ):
                return res

            # XXX: component providers
            # for prov_type in reversed(comp_conf.provider_grants):
            #     component.remove_provider(prov_type)

            for res_type in reversed(comp_conf.resource_claims):
                component.remove_resource(res_type)

        if not (
            res := self._rm.teardown().map_err(
                lambda e: ModuleError.Resource(path=self._path, details=e.message)
            )
        ):
            return res

        logger.info('{path}: Module teardown successful'.format(path=self._path))
        return Ok()
