# mypy: warn_no_return=false,disable_error_code="arg-type,valid-type"
from __future__ import annotations

from dataclasses import fields as dataclass_fields
from typing import TYPE_CHECKING, Any, ClassVar, Final, Self

from .enum import Enum, Struct
from .i18n import StaticTranslator

if TYPE_CHECKING:
    from .result import Result


class Error(Enum):
    _tr: ClassVar[StaticTranslator] | None = None
    namespace: ClassVar[str] = ''
    code: Final[str] = ''
    msg: Final[str] = ''

    @property
    def message(self) -> str:
        values = {}

        # noinspection PyDataclass
        for field in dataclass_fields(self):
            if not field.repr or not field.init:
                continue

            values[field.name] = getattr(self, field.name, '')

        if self.code and self._tr is not None:
            msg = self._tr('.'.join([self.namespace, self.code]), default=self.msg)
        else:
            msg = self.msg

        return msg.format(**values)

    def __init_subclass__(cls, **kwargs: dict[str, Any]) -> None:
        if 'tr' in kwargs:
            assert isinstance(kwargs['tr'], StaticTranslator)
            cls._tr = kwargs.pop('tr')
        super().__init_subclass__(**kwargs)

    def to_result(self) -> Result[Any, Self]:
        from .result import Err

        return Err(self)


class ErrorCase(Struct):
    __slots__ = ('msg', 'code')

    def _repr_fn(self, instance: Error) -> str:
        return f'{self._base.__name__}:{self._name}("{instance.message}")'
