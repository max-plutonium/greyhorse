import inspect
from asyncio import iscoroutinefunction
from functools import partial
from types import EllipsisType, NoneType, UnionType, new_class
from typing import Any, TypeVar, TypeVarTuple, Union, get_args, get_origin

from .strings import capitalize

_TYPES_CACHE = {}


class TypeWrapper[T]:
    __wrapped_type__: type | tuple[type, ...] = type

    @property
    def wrapped_type(self) -> type | tuple[type, ...]:
        return self.__wrapped_type__

    @classmethod
    def __generate_typename__(
        cls,
        types: type | TypeVar | TypeVarTuple | tuple[type | TypeVar | TypeVarTuple, ...],
        include_base_name: bool = True,
    ) -> str:
        if isinstance(types, tuple):
            type_args = [cls.__generate_typename__(a, False) for a in types]
            type_name = f'{''.join(type_args)}'
        elif isinstance(types, TypeVar):
            type_name = '~'
        elif isinstance(types, NoneType):
            type_name = 'None'
        elif isinstance(types, UnionType):
            type_args = [cls.__generate_typename__(a, False) for a in types.__args__]
            type_name = f'{''.join(type_args)}Union'
        elif isinstance(types, EllipsisType):
            type_name = '...'
        elif hasattr(types, '__args__'):
            type_args = [cls.__generate_typename__(a, False) for a in types.__args__]
            type_name = f'{''.join(type_args)}{capitalize(types.__name__)}'
        else:
            type_name = f'{capitalize(types.__name__)}'

        if include_base_name:
            if cls.__name__.startswith('_'):
                type_name = f'_{type_name}{cls.__name__[1:]}'
            else:
                type_name = f'{type_name}{cls.__name__}'

        return type_name

    def __init_subclass__(cls, **kwargs: dict[str, Any]) -> None:
        if spec := kwargs.pop('spec', None):
            if not isinstance(spec, list):
                spec = [spec]

            for spec_class in spec:  # type: type
                type_name = cls.__generate_typename__(spec_class, False)
                _TYPES_CACHE[type_name] = cls

        super().__init_subclass__(**kwargs)

    def __class_getitem__(
        cls, types: type | TypeVar | TypeVarTuple | tuple[type | TypeVar | TypeVarTuple, ...]
    ) -> type:
        if isinstance(types, TypeVar | TypeVarTuple):
            # noinspection PyUnresolvedReferences
            return super().__class_getitem__(types)

        type_name = cls.__generate_typename__(types)

        if class_ := _TYPES_CACHE.get(type_name):
            return class_

        bases = [cls]

        if not isinstance(types, tuple) and hasattr(types, '__base__'):
            base_type_name = '~' + cls.__generate_typename__(types.__base__)
            if base_class := _TYPES_CACHE.get(base_type_name):
                bases = [base_class, *bases]

        if hasattr(cls, '__slots__'):
            cls.__slots__ = (*cls.__slots__, '__wrapped_type__')
            attrs = {k: v for k, v in cls.__dict__.items() if k in cls.__slots__}
            attrs['__wrapped_type__'] = types
            attrs['__module__'] = cls.__module__
            class_ = new_class(type_name, tuple(bases), exec_body=lambda d: d.update(attrs))

        else:
            attrs = dict(cls.__dict__)
            attrs.pop('__class_getitem__', None)
            attrs['__wrapped_type__'] = types
            attrs['__module__'] = cls.__module__

            class_ = new_class(type_name, tuple(bases), exec_body=lambda d: d.update(attrs))

        _TYPES_CACHE[type_name] = class_
        return class_


def is_optional[T](value: type[T]) -> bool:
    if get_origin(value) is Union or isinstance(value, UnionType):
        type_args = get_args(value)
        if len(type_args) > 1:
            return type_args[1] is NoneType
    return False


def is_maybe[T](value: type[T]) -> bool:
    from greyhorse.maybe import Maybe

    return get_origin(value) is Maybe or isinstance(value, Maybe)


def is_awaitable(f: object) -> bool:
    while isinstance(f, partial):
        f = f.func
    f = inspect.unwrap(f)
    return iscoroutinefunction(f) or inspect.isawaitable(f)


def unwrap_optional[T](value: type[T]) -> type[T]:
    if get_origin(value) is Union or isinstance(value, UnionType):
        type_args = get_args(value)
        if len(type_args) >= 1:
            return type_args[0]
    return value


def unwrap_maybe[T](value: type[T]) -> type[T]:
    from greyhorse.maybe import Maybe

    if get_origin(value) is Maybe or isinstance(value, Maybe):
        type_args = get_args(value)
        if len(type_args) >= 1:
            return type_args[0]
    return value
