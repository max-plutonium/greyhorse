from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, Mapping, Sequence, Tuple, Type, TypeVar

from ..models.model import Model
from ...utils.invoke import is_awaitable

IdType = TypeVar('IdType')
EntityType = TypeVar('EntityType')
ModelType = TypeVar('ModelType', bound=Model, covariant=True)
EntityFactory = Callable[..., EntityType]
ModelFactory = Callable[..., ModelType]


class Repository(Generic[IdType, EntityType], ABC):
    def __init__(self, class_: Type[EntityType], factory: EntityFactory | None = None):
        self._class = class_
        self._factory = factory or class_

    @property
    def entity_class(self):
        return self._class

    @property
    def entity_factory(self):
        return self._factory

    async def construct(self, data: Mapping[str, Any], **kwargs) -> EntityType:
        result = self.entity_factory(**data)
        if is_awaitable(result):
            return await result
        return result

    @abstractmethod
    async def get(self, id_value: IdType, **kwargs) -> EntityType | None:
        ...

    @abstractmethod
    async def get_any(self, indices: Sequence[IdType], **kwargs) -> Sequence[EntityType | None]:
        ...

    @abstractmethod
    async def exists(self, id_value: IdType, **kwargs) -> bool:
        ...

    @abstractmethod
    async def load(self, instance: EntityType, only: Sequence[str] | None = None) -> bool:
        ...

    @abstractmethod
    async def create(self, data: Mapping[str, Any], **kwargs) -> EntityType | None:
        ...

    async def get_or_create(
        self, id_value: IdType, data: Mapping[str, Any], **kwargs,
    ) -> Tuple[EntityType | None, bool]:
        if instance := await self.get(id_value, **kwargs):
            return instance, False
        else:
            return await self.create(data, **kwargs), True

    @abstractmethod
    async def update_by_id(self, id_value: IdType, data: Mapping[str, Any], **kwargs) -> bool:
        ...

    @abstractmethod
    async def save(self, instance: EntityType, **kwargs) -> bool:
        ...

    @abstractmethod
    async def save_all(self, objects: Sequence[EntityType], **kwargs) -> bool:
        ...

    @abstractmethod
    async def delete(self, instance: EntityType) -> bool:
        ...

    @abstractmethod
    async def delete_all(self, indices: Sequence[IdType] | None = None) -> int:
        ...

    @abstractmethod
    async def delete_by_id(self, id_value: IdType) -> bool:
        ...


class ModelRepository(Repository[IdType, ModelType], ABC):
    def __init__(
        self, model_class: Type[ModelType],
        model_factory: ModelFactory | None = None,
    ):
        super().__init__(model_class, model_factory)
        model_class.bind(self)
