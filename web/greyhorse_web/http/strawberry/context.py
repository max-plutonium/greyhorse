from functools import cached_property

from greyhorse.app.registries import MutDictRegistry
from greyhorse.app.resources import Container
from greyhorse.maybe import Maybe
from strawberry.fastapi import BaseContext


class Context(BaseContext):
    __slots__ = ('_containers_map',)

    def __init__(self) -> None:
        super().__init__()
        self._containers_map = MutDictRegistry[type, Container]()

    def get[T](self, hint: type[T]) -> Maybe[T]:
        return self._request_container.get(hint)

    @cached_property
    def _request_container(self) -> Container:
        return self.request.state.container

    def container_for(self, source: object) -> Container:
        return self._containers_map.get(type(source)).unwrap_or_else(
            lambda: self._request_container
        )

    def add_source_container(self, source: object, container: Container) -> bool:
        return self._containers_map.add(type(source), container)

    def remove_source_container(self, source: object, container: Container) -> bool:
        return self._containers_map.remove(type(source), container)
