from dataclasses import make_dataclass, fields as dataclass_fields, field as dataclass_field
from typing import Any, Generic

from greyhorse.utils.invoke import caller_path


class Unit:
    __slots__ = ('_name', '_base', '_factory')

    def _bind(self, name: str, base: type):
        self._name = name
        self._base = base

        bases = [base]

        fields = [
            ('__orig_class__', Any, dataclass_field(default=self._base, init=True, repr=False))
        ]

        dc = make_dataclass(
            name, fields, bases=tuple(bases),
            module=f'{'.'.join(caller_path(3))}.{self._base.__name__}',
            slots=True, frozen=True, repr=False, match_args=False,
        )

        dc.__orig_class__ = self.__class__
        dc.__match_args__ = ()
        dc.__repr__ = lambda _: f'{self._base.__name__}:{self._name}'
        self._factory = dc()
        return self._factory

    def __repr__(self):
        return f'{self._base.__name__}:{self._name}'

    def __call__(self):
        return self._factory


class Tuple[*Ts]:
    __slots__ = ('_name', '_base', '_factory', '_types')

    def __init__(self, *types: *Ts):
        self._types = types

    def _bind(self, name: str, base: type):
        self._name = name
        self._base = base

        bases = [base, Generic[*self._types]]

        fields = {
            f'_{i}': arg for i, arg in enumerate(self._types)
        }
        fields = list(fields.items())
        fields.append(
            ('__orig_class__', Any, dataclass_field(default=self._base, init=True, repr=False))
        )

        dc = make_dataclass(
            name, fields, bases=tuple(bases),
            module=f'{'.'.join(caller_path(3))}.{self._base.__name__}',
            slots=True, frozen=True, repr=False, match_args=False,
        )

        dc.__orig_class__ = self.__class__
        dc.__match_args__ = tuple([f'_{i}' for i, _ in enumerate(self._types)])
        dc.__repr__ = lambda self0: self._repr_fn(self0)
        self._factory = dc

        # noinspection PyUnresolvedReferences
        def _init(self0, *args):
            types = tuple(type(arg) for arg in args)
            return old_init(self0, *args, __orig_class__=self._factory[*types])

        old_init, dc.__init__ = dc.__init__, _init
        return self._factory

    def __repr__(self):
        return f'{self._base.__name__}:{self._name}(' \
               f'{", ".join([t.__name__ for t in self._types])})'

    def _repr_fn(self, instance):
        res = []
        for field, type_ in zip(dataclass_fields(instance), instance.__orig_class__.__args__):
            if not field.repr:
                continue

            if v := str(getattr(instance, field.name, '')):
                res.append(f'{type_.__name__}: {v}')
            else:
                res.append(f'{type_.__name__}')

        return f'{self._base.__name__}:{self._name}({", ".join(res)})'

    def __call__(self, *args):
        return self._factory(*args)


class Struct:
    __slots__ = ('_name', '_base', '_factory', '_kwargs')

    def __init__(self, **kwargs):
        self._kwargs: dict[str, type] = kwargs

    def _bind(self, name: str, base: type):
        self._name = name
        self._base = base

        bases = [base]

        fields = list(self._kwargs.items())
        fields.append(
            ('__orig_class__', Any, dataclass_field(default=self._base, init=True, repr=False))
        )

        dc = make_dataclass(
            name, fields, bases=tuple(bases),
            module=f'{'.'.join(caller_path(3))}.{self._base.__name__}',
            slots=True, frozen=True, repr=False, match_args=False,
        )

        dc.__orig_class__ = self.__class__
        dc.__match_args__ = tuple([f'{k}' for k in self._kwargs.keys()])
        dc.__repr__ = lambda self0: self._repr_fn(self0)
        self._factory = dc
        return self._factory

    def __repr__(self):
        return f'{self._base.__name__}:{self._name}(' \
               f'{", ".join([f'{n}: {t.__name__}' for n, t in self._kwargs.items()])})'

    def _repr_fn(self, instance):
        res = []
        for field in dataclass_fields(instance):
            if not field.repr:
                continue

            if v := str(getattr(instance, field.name, '')):
                res.append(f'{field.name}: {field.type.__name__} = {v}')
            else:
                res.append(f'{field.name}: {field.type.__name__}')

        return f'{self._base.__name__}:{self._name}({", ".join(res)})'

    def __call__(self, **kwargs):
        return self._factory(**kwargs)


def enum(cls):
    """
    Create algebraic enumeration from class.
    """
    for field_name in dir(cls):
        instance = getattr(cls, field_name)

        if isinstance(instance, (Unit, Tuple, Struct)):
            # noinspection PyProtectedMember
            factory = instance._bind(field_name, cls)
            setattr(cls, field_name, factory)
        else:
            continue

    return cls
