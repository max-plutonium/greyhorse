import types
from typing import TypeVar

from .strings import capitalize

_TYPES_CACHE = {}


class TypeWrapper[T]:
    __wrapped_type__ = object

    @property
    def wrapped_type(self) -> type:
        return self.__wrapped_type__

    def __class_getitem__(cls, type_: type[T]):
        if isinstance(type_, TypeVar):
            # noinspection PyUnresolvedReferences
            return super(TypeWrapper, cls).__class_getitem__(type_)

        if hasattr(type_, '__args__'):
            type_args = [capitalize(a.__name__) for a in type_.__args__]
            type_name = f'{capitalize(type_.__name__)}{''.join(type_args)}{cls.__name__}'
        else:
            type_name = f'{capitalize(type_.__name__)}{cls.__name__}'

        if class_ := _TYPES_CACHE.get(type_name):
            return class_

        if hasattr(cls, '__slots__'):
            cls.__slots__ = (*cls.__slots__, '__wrapped_type__')
            attrs = {k: v for k, v in cls.__dict__.items() if k in cls.__slots__}
            attrs['__wrapped_type__'] = type_
            class_ = types.new_class(type_name, (cls,), exec_body=lambda d: d.update(attrs))

        else:
            attrs = dict(cls.__dict__)
            attrs.pop('__class_getitem__', None)
            attrs['__wrapped_type__'] = type_
            attrs['__module__'] = type_.__module__

            class_ = types.new_class(type_name, (cls,), exec_body=lambda d: d.update(attrs))

        _TYPES_CACHE[type_name] = class_
        return class_
