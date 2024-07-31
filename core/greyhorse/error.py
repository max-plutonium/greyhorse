from __future__ import annotations

from dataclasses import fields as dataclass_fields
from typing import ClassVar, Final, TYPE_CHECKING, Any, Self

from .enum import Struct, Enum
from .i18n import StaticTranslator

if TYPE_CHECKING:
    from .result import Result


class Error(Enum):
    _tr: ClassVar[StaticTranslator] = None
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

        msg = msg.format(**values)
        return msg

    def __init_subclass__(cls, **kwargs):
        if 'tr' in kwargs:
            assert isinstance(kwargs['tr'], StaticTranslator)
            cls._tr = kwargs.pop('tr')
        return super().__init_subclass__(**kwargs)

    def to_result(self) -> 'Result[Any, Self]':
        from .result import Err

        return Err(self)


class ErrorCase(Struct):
    __slots__ = ('msg', 'code')

    def _repr_fn(self, instance):
        return f'{self._base.__name__}:{self._name}(\"{instance.message}\")'
