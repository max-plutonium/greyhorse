from typing import Any, override

from greyhorse.logging import logger
from greyhorse.maybe import Maybe, Nothing
from greyhorse.result import Ok, Result

from ..abc.module import Module, ModuleError
from ..abc.operators import Operator
from ..abc.providers import Provider
from ..abc.visitor import Visitor
from ..entities.components import Component
from ..registries import MutDictRegistry
from ..resources.manager import ResourceManager
from ..schemas.components import ModuleConf


class SyncModule(Module):
    def __init__(self, path: str, conf: ModuleConf, components: list[Component]) -> None:
        super().__init__(path)
        self._conf = conf
        self._rm = ResourceManager()

        self._operators: list[Operator] = []
        self._resources = MutDictRegistry[type, Any]()
        self._providers = MutDictRegistry[type[Provider], Provider]()
        self._components: dict[str, Component] = {c.name: c for c in components}

    @property
    def conf(self) -> ModuleConf:
        return self._conf

    @override
    def accept_visitor(self, visitor: Visitor) -> None:
        visitor.start_module(self)
        for comp in self._components.values():
            comp.accept_visitor(visitor)
        visitor.finish_module(self)

    @override
    def get_provider[P: Provider](self, prov_type: type[P]) -> Maybe[P]:
        if prov_type in self._conf.providers:
            return self._providers.get(prov_type)
        return Nothing

    @override
    def add_provider[T](self, prov_type: type[Provider[T]], provider: Provider[T]) -> bool:
        if prov_type in self._conf.provider_claims:
            return self._providers.add(prov_type, provider)
        return False

    @override
    def remove_provider[T](self, prov_type: type[Provider[T]]) -> bool:
        if prov_type in self._conf.provider_claims:
            return self._providers.remove(prov_type)
        return False

    @override
    def add_resource[T](self, res_type: type[T], resource: T) -> bool:
        if res_type in self._conf.resource_claims:
            return self._resources.add(res_type, resource)
        return False

    @override
    def remove_resource[T](self, res_type: type[T]) -> bool:
        if res_type in self._conf.resource_claims:
            return self._resources.remove(res_type)
        return False

    @override
    def add_operator[T](self, operator: Operator[T]) -> bool:
        for res_type in self._conf.operators:
            if issubclass(res_type, operator.wrapped_type):
                self._operators.append(operator)
                return True
        return False

    @override
    def remove_operator[T](self, operator: Operator[T]) -> bool:
        for res_type in self._conf.operators:
            if issubclass(res_type, operator.wrapped_type):
                self._operators.remove(operator)
                return True
        return False

    @override
    def create(self) -> Result[None, ModuleError]:
        logger.info('{path}: Module create'.format(path=self._path))

        for component in self._components.values():
            if not (
                res := component.create().map_err(
                    lambda e: ModuleError.Component(path=self._path, details=e.message)
                )
            ):
                return res

        logger.info('{path}: Module create successful'.format(path=self._path))
        return Ok()

    @override
    def setup(self) -> Result[None, ModuleError]:
        logger.info('{path}: Module setup'.format(path=self._path))

        for component in self._components.values():
            comp_conf = self._conf.components[component.name]

            for res_type in comp_conf.resource_claims:
                if res := self._resources.get(res_type):
                    component.add_resource(res_type, res.unwrap())

            for res_type in comp_conf.operators:
                for op in component.get_operators(res_type):  # type: ignore
                    if not (
                        res := self._rm.setup_operator(op, providers=self._providers).map_err(
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
                if prov := component.get_provider(prov_type):
                    self._providers.add(prov_type, prov.unwrap())

        for op in self._operators:
            if not (
                res := self._rm.setup_operator(op, providers=self._providers).map_err(
                    lambda e: ModuleError.Resource(path=self._path, details=e.message)
                )
            ):
                return res  # type: ignore

        logger.info('{path}: Module setup successful'.format(path=self._path))
        return Ok()

    @override
    def teardown(self) -> Result[None, ModuleError]:
        logger.info('{path}: Module teardown'.format(path=self._path))

        for op in reversed(self._operators):
            if not (
                res := self._rm.teardown_operator(op).map_err(
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
                        res := self._rm.teardown_operator(op).map_err(
                            lambda e: ModuleError.Resource(path=self._path, details=e.message)
                        )
                    ):
                        return res  # type: ignore

            for res_type in reversed(comp_conf.resource_claims):
                if self._resources.has(res_type):
                    component.remove_resource(res_type)

        logger.info('{path}: Module teardown successful'.format(path=self._path))
        return Ok()

    @override
    def destroy(self) -> Result[None, ModuleError]:
        logger.info('{path}: Module teardown'.format(path=self._path))

        for component in reversed(self._components.values()):
            if not (
                res := component.destroy().map_err(
                    lambda e: ModuleError.Component(path=self._path, details=e.message)
                )
            ):
                return res

        if not (
            res := self._rm.teardown().map_err(
                lambda e: ModuleError.Resource(path=self._path, details=e.message)
            )
        ):
            return res

        logger.info('{path}: Module teardown successful'.format(path=self._path))
        return Ok()
