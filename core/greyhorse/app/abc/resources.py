from collections.abc import AsyncGenerator, Callable, Generator, Iterable
from functools import cache
from typing import TYPE_CHECKING, Self

from greyhorse.enum import Enum, Struct

type TypeFactoryFn[T] = (
    Callable[[T], T]
    | type[T]
    | T
    | Callable[[], Generator[T, T, None]]
    | Callable[[], AsyncGenerator[T, T]]
)


class Lifetime(Enum):
    ROOT = Struct(name='ROOT', order=0, autocreate=True)
    RUNTIME = Struct(name='RUNTIME', order=1, autocreate=True)
    COMPONENT = Struct(name='COMPONENT', order=2, autocreate=False)
    SESSION = Struct(name='SESSION', order=3, autocreate=True)
    REQUEST = Struct(name='REQUEST', order=4, autocreate=False)
    ACTION = Struct(name='ACTION', order=5, autocreate=True)
    STEP = Struct(name='STEP', order=6, autocreate=False)

    if TYPE_CHECKING:
        name: str
        order: int
        autocreate: str

    @classmethod
    @cache
    def all(cls) -> Iterable[Self]:
        lifetimes = [lifetime_class() for _, lifetime_class in Lifetime.items]
        lifetimes.sort(key=lambda lifetime: lifetime.order)
        return lifetimes
