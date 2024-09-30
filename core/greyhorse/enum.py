from dataclasses import field as dataclass_field
from dataclasses import fields as dataclass_fields
from dataclasses import make_dataclass
from typing import Any, ClassVar, Generic, NoReturn, TypeVar

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
            name,
            fields,
            bases=tuple(bases),
            module=f'{'.'.join(caller_path(3))}.{self._base.__name__}',
            slots=True,
            frozen=True,
            repr=False,
            match_args=False,
        )

        dc.__orig_class__ = self.__class__  # type: ignore
        dc.__match_args__ = ()  # type: ignore
        dc.__repr__ = lambda _: f'{self._base.__name__}:{self._name}'  # type: ignore
        self._factory = dc()  # type: ignore
        return self._factory

    def __repr__(self) -> str:
        return f'{self._base.__name__}:{self._name}'

    def __call__(self):
        return self._factory


class Tuple[*Ts]:
    __slots__ = ('_name', '_base', '_factory', '_fields', '_types')

    def __init__(self, *types: *Ts) -> None:
        self._types: list[TypeVar] = []
        self._fields: list[type] = []

        for t in types:
            if isinstance(t, type):
                self._fields.append(t)
            elif isinstance(t, TypeVar):
                self._types.append(t)

    def _bind(self, name: str, base: type):
        self._name = name
        self._base = base

        bases = [base]

        if self._types:
            bases += [Generic[*self._types]]  # type: ignore

        fields = list(
            {f'_{i}': arg for i, arg in enumerate(self._types + self._fields)}.items()
        )  # type: ignore
        fields.append((
            '__orig_class__',
            Any,
            dataclass_field(default=self._base, init=True, repr=False),
        ))  # type: ignore

        dc = make_dataclass(
            name,
            fields,
            bases=tuple(bases),
            module=f'{'.'.join(caller_path(3))}.{self._base.__name__}',
            slots=True,
            frozen=True,
            repr=False,
            match_args=False,
        )

        dc.__orig_class__ = self.__class__  # type: ignore
        dc.__match_args__ = tuple([f'_{i}' for i, _ in enumerate(self._types + self._fields)])  # type: ignore
        dc.__repr__ = lambda self0: self._repr_fn(self0)  # type: ignore
        self._factory = dc  # type: ignore

        def __init__(self0, *args):
            if not args:
                args = (None,)
            types = tuple(type(arg) for arg in args)
            orig_class = self._factory[*types] if self._types else self.__class__  # type: ignore
            return old_init(self0, *args, __orig_class__=orig_class)

        old_init, dc.__init__ = dc.__init__, __init__  # type: ignore
        return self._factory

    def __repr__(self) -> str:
        return (
            f'{self._base.__name__}:{self._name}('
            f'{', '.join([t.__name__ for t in self._types])})'
        )

    def _repr_fn(self, instance) -> str:
        res = []
        for field, type_ in zip(
            dataclass_fields(instance), instance.__orig_class__.__args__, strict=False
        ):
            if not field.repr:
                continue

            if v := getattr(instance, field.name, ''):
                res.append(f'{type_.__name__}: {v!r}')
            else:
                res.append(f'{type_.__name__}')

        return f'{self._base.__name__}:{self._name}({', '.join(res)})'

    def __call__(self, *args):
        return self._factory(*args)


class Struct:
    __slots__ = ('_name', '_base', '_factory', '_fields', '_values')

    def __init__(self, **kwargs) -> None:
        self._values: dict[str, Any] = {}
        self._fields: dict[str, type] = {}

        for k, v in kwargs.items():
            if isinstance(v, type | TypeVar):
                self._fields[k] = v  # type: ignore
            else:
                self._values[k] = v

    def _bind(self, name: str, base: type):
        self._name = name
        self._base = base

        bases = [base]

        fields = list(self._fields.items())
        fields.append((
            '__orig_class__',
            Any,
            dataclass_field(default=self._base, init=True, repr=False),
        ))  # type: ignore

        for k, v in self._values.items():
            fields.append((k, type(v), dataclass_field(default=v, init=False, repr=True)))  # type: ignore

        dc = make_dataclass(
            name,
            fields,
            bases=tuple(bases),
            module=f'{'.'.join(caller_path(3))}.{self._base.__name__}',
            slots=True,
            frozen=True,
            repr=False,
            match_args=False,
        )

        dc.__orig_class__ = self.__class__  # type: ignore
        dc.__match_args__ = tuple([f'{k}' for k in self._fields])  # type: ignore
        dc.__repr__ = lambda self0: self._repr_fn(self0)  # type: ignore
        self._factory = dc  # type: ignore
        return self._factory

    def __repr__(self) -> str:
        return (
            f'{self._base.__name__}:{self._name}('
            f'{', '.join([f'{n}: {t.__name__}' for n, t in self._fields.items()])})'
        )

    def _repr_fn(self, instance) -> str:
        res = []
        for field in dataclass_fields(instance):
            if not field.repr:
                continue

            if v := getattr(instance, field.name, ''):
                res.append(f'{field.name}: {type(v).__name__} = {v!r}')
            else:
                res.append(f'{field.name}: {type(v).__name__}')

        return f'{self._base.__name__}:{self._name}({', '.join(res)})'

    def __call__(self, **kwargs):
        return self._factory(**kwargs)


class Enum:
    """
    Implements algebraic enumeration class.
    """

    def __init_subclass__(cls, allow_init: bool = False, **kwargs):
        fields: dict[str, ClassVar[Unit | Tuple | Struct]] = {}  # type: ignore

        for field_name in dir(cls):
            instance = getattr(cls, field_name)

            if isinstance(instance, Unit | Tuple | Struct):
                fields[field_name] = instance
                delattr(cls, field_name)
            else:
                continue

        for field_name, instance in fields.items():
            # noinspection PyProtectedMember
            factory = instance._bind(field_name, cls)
            setattr(cls, field_name, factory)

        if fields and not allow_init:

            def __init__(*_, **__) -> NoReturn:
                raise NotImplementedError()

            cls.__init__ = __init__  # type: ignore

        return super().__init_subclass__(**kwargs)


def enum(cls: type | None = None, allow_init: bool = False):
    """
    Create algebraic enumeration from class.
    """

    def decorator(cls):
        for field_name in dir(cls):
            instance = getattr(cls, field_name)

            if isinstance(instance, Unit | Tuple | Struct):
                # noinspection PyProtectedMember
                factory = instance._bind(field_name, cls)
                setattr(cls, field_name, factory)
            else:
                continue

        if not allow_init:

            def __init__(*_, **__) -> NoReturn:
                raise NotImplementedError()

            cls.__init__ = __init__

        return cls

    if cls is None:
        return decorator

    return decorator(cls)
