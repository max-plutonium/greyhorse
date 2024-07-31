import types
from typing import TypeVar

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
            type_args = [a.__name__.capitalize() for a in type_.__args__]
            type_name = f'{type_.__name__}{''.join(type_args)}{cls.__name__}'
        else:
            type_name = f'{type_.__name__}{cls.__name__}'

        if class_ := _TYPES_CACHE.get(type_name):
            return class_

        attrs = dict(cls.__dict__)
        attrs.pop('__class_getitem__', None)
        attrs['__wrapped_type__'] = type_
        attrs['__module__'] = type_.__module__

        class_ = types.new_class(type_name, (cls,), exec_body=lambda d: d.update(attrs))
        _TYPES_CACHE[type_name] = class_
        return class_
