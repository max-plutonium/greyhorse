import dataclasses
from typing import Dict, Generic, Optional, Protocol, Sequence, Type, TypeVar, Self

from greyhorse_core.i18n import tr

GenericType = TypeVar('GenericType')


class ResultProtocol(Protocol[GenericType]):
    success: bool
    result: GenericType | None
    errors: Sequence['Error'] | None


@dataclasses.dataclass
class Result(Generic[GenericType]):
    success: bool
    result: GenericType | None = None
    errors: Sequence['Error'] | None = dataclasses.field(default_factory=list)

    @classmethod
    def from_ok(cls, value: GenericType | None = None):
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


class Error:
    _code_classes: dict[int, Type[Self]] = dict()
    _type_classes: dict[str, Type[Self]] = dict()

    code: int
    type: str
    msg: str | None = ''
    tr_key: str | None = ''

    @property
    def message(self):
        if self.tr_key:
            return tr(self.tr_key)
        return tr(self.type, default=self.msg)

    def __repr__(self):
        return f"Error[{self.code}] ({self.type}): \"{self.message}\""

    def __eq__(self, other: Self):
        return self.code == other.code

    def __hash__(self):
        return self.code

    @property
    def dict(self):
        return dict(code=self.code, type=self.type, message=self.message)

    @classmethod
    def get_by_code(cls, code: int) -> Type[Self] | None:
        return cls._code_classes.get(code)

    @classmethod
    def get_by_type(cls, type_: str) -> Type[Self] | None:
        return cls._type_classes.get(type_)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._code_classes[cls.code] = cls
        cls._type_classes[cls.type] = cls


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
