import dataclasses
import enum
from functools import wraps
from typing import Callable, Container, Optional, Protocol, Self, Sequence, Type

from .i18n import tr


class ResultProtocol[T](Protocol):
    success: bool
    result: T | None
    errors: Sequence['Error'] | None


class ResultStatus(str, enum.Enum):
    OK: str = 'ok'
    PARTIAL: str = 'partial'
    ERROR: str = 'error'


@dataclasses.dataclass(slots=True, frozen=True)
class Result[T]:
    success: bool
    result: T | None = None
    errors: Sequence['Error'] | None = dataclasses.field(default_factory=list)

    @classmethod
    def from_ok(cls, value: T | None = None):
        return cls(success=True, result=value, errors=[])

    @classmethod
    def from_error(cls, error: 'Error'):
        return cls(success=False, result=None, errors=[error])

    @classmethod
    def from_errors(cls, errors: Sequence['Error']):
        return cls(success=False, result=None, errors=errors)

    @property
    def error(self) -> Optional['Error']:
        return self.errors[0] if len(self.errors) else None

    @property
    def error_count(self) -> int:
        return len(self.errors)


@dataclasses.dataclass(slots=True, frozen=True)
class ComplexResult[T: Container]:
    status: ResultStatus
    result: T | None = None
    errors: Sequence['Error'] | None = dataclasses.field(default_factory=list)

    @classmethod
    def from_ok(cls, values: T | None = None):
        return cls(status=ResultStatus.OK, result=values, errors=[])

    @classmethod
    def from_partial(
        cls, values: T | None = None, error: Optional['Error'] = None,
        errors: Sequence['Error'] | None = None,
    ):
        errors = errors if errors else [error] if error else []
        return cls(status=ResultStatus.PARTIAL, result=values, errors=errors)

    @classmethod
    def from_error(cls, error: 'Error'):
        return cls(status=ResultStatus.ERROR, result=None, errors=[error])

    @classmethod
    def from_errors(cls, errors: Sequence['Error']):
        return cls(status=ResultStatus.ERROR, result=None, errors=errors)

    @property
    def error(self) -> Optional['Error']:
        return self.errors[0] if len(self.errors) else None

    @property
    def error_count(self) -> int:
        return len(self.errors)


type ListResult[T] = ComplexResult[list[T]]
type DictResult[K, V] = ComplexResult[dict[K, V]]


class Error:
    _type_classes: dict[str, type[Self]] = dict()

    app: str = ''
    type: str
    msg: str = ''
    tr_key: str = ''

    @property
    def message(self):
        if self.tr_key:
            return tr('.'.join([self.app, self.tr_key]))
        return tr('.'.join([self.app, self.type]), default=self.msg)

    def __repr__(self):
        return f'Error [{self.app}] ({self.type}): \"{self.message}\"'

    def __eq__(self, other: Self):
        return (self.app, self.type) == (other.app, other.type)

    def __hash__(self):
        return hash((self.app, self.type))

    @property
    def dict(self):
        return dict(app=self.app, type=self.type, message=self.message)

    @classmethod
    def get_by_type(cls, type_: str) -> Type[Self] | None:
        return cls._type_classes.get(type_)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'type'):
            cls._type_classes[cls.type] = cls


class ErrorKwargsMixin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    # noinspection PyUnresolvedReferences
    @property
    def message(self):
        message = super(ErrorKwargsMixin, self).message
        return message.format(**self.kwargs)


def result_or(result, error):
    if callable(result):
        result = result()
    if result:
        return result
    if isinstance(error, Exception):
        if callable(error):
            raise error()
        raise error
    return error


# noinspection PyPep8Naming
def F[T, **P](func: Callable[P, T]) -> Callable[P, Result[T]]:
    @wraps(func)
    def inner(*args: P.args, **kwargs: P.kwargs) -> Result[T]:
        return Result.from_ok(func(*args, **kwargs))
    return inner
