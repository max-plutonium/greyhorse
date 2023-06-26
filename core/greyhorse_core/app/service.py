from abc import ABC
from typing import Mapping

from . import base


class Service(base.Service, ABC):
    def __init__(self, resources: Mapping[str, base.ResourceFactory] | None = None):
        super().__init__()
        self._resources: dict[str, base.Resource] = dict()
        self._resource_factories = resources or dict()

    @property
    def resources(self) -> list[base.Resource]:
        return list(self._resources.values())

    def get_resource(self, name) -> base.Resource | None:
        return self._resources.get(name)
