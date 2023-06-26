from abc import ABC
from typing import Dict, Mapping

from . import base, service


class Module(base.Module, ABC):
    def __init__(
        self, name: str,
        resources: Mapping[str, base.ResourceFactory] | None = None,
        services: Mapping[str, base.ServiceFactory] | None = None,
        modules: Mapping[str, base.ModuleFactory] | None = None, *args, **kwargs,
    ):
        super().__init__(name)

        self._resources: Dict[str, base.Resource] = dict()
        self._services: Dict[str, service.Service] = dict()
        self._modules: Dict[str, Module] = dict()
        self._resource_factories = resources or dict()
        self._service_factories = services or dict()
        self._module_factories = modules or dict()

    @property
    def resources(self) -> list[base.Resource]:
        return list(self._resources.values())

    def get_resource(self, name) -> base.Resource | None:
        return self._resources.get(name)

    @property
    def services(self) -> list[base.Service]:
        return list(self._services.values())

    def get_service(self, name) -> base.Service | None:
        return self._services.get(name)

    @property
    def modules(self) -> list[base.Module]:
        return list(self._modules.values())

    def get_module(self, name) -> base.Module | None:
        return self._modules.get(name)
