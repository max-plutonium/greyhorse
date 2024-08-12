import types
from typing import TypeVar

from .strings import capitalize

_TYPES_CACHE = {}


class TypeWrapper[T]:
    __wrapped_type__ = type

    @property
    def wrapped_type(self) -> type:
        return self.__wrapped_type__

    @classmethod
    def __generate_typename__(cls, type_: type, include_base_name: bool = True) -> str:
        if isinstance(type_, TypeVar):
            type_name = '~'
        elif hasattr(type_, '__args__'):
            type_args = [cls.__generate_typename__(a, False) for a in type_.__args__]
            type_name = f'{''.join(type_args)}{capitalize(type_.__name__)}'
        else:
            type_name = f'{capitalize(type_.__name__)}'

        if include_base_name:
            type_name = type_name + cls.__name__
        return type_name

    def __init_subclass__(cls, **kwargs):
        if spec := kwargs.pop('spec', None):
            if not isinstance(spec, list):
                spec = [spec]

            for spec_class in spec:
                type_name = cls.__generate_typename__(spec_class, False)
                _TYPES_CACHE[type_name] = cls

        super().__init_subclass__(**kwargs)

    def __class_getitem__(cls, type_: type[T]):
        if isinstance(type_, TypeVar):
            # noinspection PyUnresolvedReferences
            return super(TypeWrapper, cls).__class_getitem__(type_)

        type_name = cls.__generate_typename__(type_)

        if class_ := _TYPES_CACHE.get(type_name):
            return class_

        bases = [cls]
        base_type_name = '~' + cls.__generate_typename__(type_.__base__)
        if base_class := _TYPES_CACHE.get(base_type_name):
            bases = [base_class] + bases

        if hasattr(cls, '__slots__'):
            cls.__slots__ = (*cls.__slots__, '__wrapped_type__')
            attrs = {k: v for k, v in cls.__dict__.items() if k in cls.__slots__}
            attrs['__wrapped_type__'] = type_
            attrs['__module__'] = type_.__module__
            class_ = types.new_class(type_name, tuple(bases), exec_body=lambda d: d.update(attrs))

        else:
            attrs = dict(cls.__dict__)
            attrs.pop('__class_getitem__', None)
            attrs['__wrapped_type__'] = type_
            attrs['__module__'] = type_.__module__

            class_ = types.new_class(type_name, tuple(bases), exec_body=lambda d: d.update(attrs))

        _TYPES_CACHE[type_name] = class_
        return class_
