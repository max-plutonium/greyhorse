from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Generic, Mapping, Optional, Sequence, Tuple, Type, TypeVar, Union, \
    cast


IdType = TypeVar('IdType')
ModelType = TypeVar('ModelType')
ModelFactory = Callable[..., ModelType]


class Repository(Generic[IdType, ModelType], ABC):
    def __init__(self, model_class: Type[ModelType], model_factory: ModelFactory | None = None):
        self._model_class = model_class
        self._model_factory = model_factory or model_class
        model_class.bind(self)

    @property
    def model_class(self):
        return self._model_class

    @property
    def model_factory(self):
        return self._model_factory

    @abstractmethod
    async def get(self, id_value: IdType, **kwargs) -> ModelType | None:
        ...

    @abstractmethod
    async def get_any(self, indices: Sequence[IdType], **kwargs) -> Sequence[ModelType | None]:
        ...

    @abstractmethod
    async def exists(self, id_value: IdType, **kwargs) -> bool:
        ...

    @abstractmethod
    async def load(self, instance: ModelType, only: Sequence[str] | None = None) -> bool:
        ...

    @abstractmethod
    async def create(self, data: Mapping[str, Any], **kwargs) -> ModelType | None:
        ...

    async def get_or_create(
        self, id_value: IdType, data: Mapping[str, Any], **kwargs,
    ) -> Tuple[ModelType | None, bool]:
        if instance := await self.get(id_value, **kwargs):
            return instance, False
        else:
            return await self.create(data, **kwargs), True

    @abstractmethod
    async def update_by_id(self, id_value: IdType, data: Mapping[str, Any], **kwargs) -> bool:
        ...

    @abstractmethod
    async def save(self, instance: ModelType, **kwargs) -> bool:
        ...

    @abstractmethod
    async def save_all(self, objects: Sequence[ModelType], **kwargs) -> bool:
        ...

    @abstractmethod
    async def delete(self, instance: ModelType) -> bool:
        ...

    @abstractmethod
    async def delete_all(self, indices: Sequence[IdType] | None = None) -> int:
        ...

    @abstractmethod
    async def delete_by_id(self, id_value: IdType) -> bool:
        ...
