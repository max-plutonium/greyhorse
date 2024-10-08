from collections.abc import Callable, Iterable
from functools import partial
from pathlib import Path
from typing import Any, get_type_hints, override

from pydantic import BaseModel

from greyhorse.maybe import Maybe, Nothing
from greyhorse.result import Ok, Result

from ..abc.collectors import MutNamedCollector, NamedCollector
from ..abc.controllers import Controller, ControllerError, OperatorMember
from ..abc.operators import AssignOperator


class ResConf(BaseModel, frozen=True):
    type: type
    name: str | None = None
    required: bool = True


def operator(resource_type: type) -> Callable[[classmethod], classmethod]:
    def decorator(func: classmethod) -> classmethod:
        class_name, method_name = func.__qualname__.split('.')
        hints = get_type_hints(func, include_extras=True)
        ret_type = hints.pop('return', None)
        func.__operator__ = OperatorMember(
            class_name, method_name, resource_type, method=func, params=hints, ret_type=ret_type
        )
        return func

    return decorator


class SyncController(Controller):
    @override
    def setup(self, collector: NamedCollector[type, Any]) -> Result[bool, ControllerError]:
        return Ok(True)

    @override
    def teardown(
        self, collector: MutNamedCollector[type, Any]
    ) -> Result[bool, ControllerError]:
        return Ok(True)


class AsyncController(Controller):
    @override
    async def setup(
        self, collector: NamedCollector[type, Any]
    ) -> Result[bool, ControllerError]:
        return Ok(True)

    @override
    async def teardown(
        self, collector: MutNamedCollector[type, Any]
    ) -> Result[bool, ControllerError]:
        return Ok(True)


_FN_BODY_TEMPLATE_FILE = Path(__file__).parent.parent / 'private' / '_ctrl_method.py_'
_FN_BODY_TEMPLATE = _FN_BODY_TEMPLATE_FILE.read_text()


class ResourceController(SyncController):
    def __init__(self, resources: Iterable[ResConf]) -> None:
        super().__init__()
        self._res_types = resources
        self._values: list[Maybe[Any]] = [Nothing for _ in self._res_types]
        self._compile_operator_methods()
        self._init_operator_members()

    def _getter(self, idx: int) -> Maybe[Any]:
        if 0 <= idx < len(self._values):
            return self._values[idx]
        return Nothing

    def _setter(self, idx: int, value: Maybe[Any]) -> None:
        if 0 <= idx < len(self._values):
            self._values[idx] = value

    @override
    def setup(self, collector: NamedCollector[type, Any]) -> Result[bool, ControllerError]:
        for idx, res_conf in enumerate(self._res_types):
            if (
                not self._values[idx]
                .map(
                    lambda value, res_conf=res_conf: collector.add(
                        res_conf.type, value, name=res_conf.name
                    )
                )
                .unwrap_or(False)
                and res_conf.required
            ):
                return ControllerError.NoSuchResource(
                    name=f'{res_conf.type.__name__}'
                ).to_result()
        return super().setup(collector)

    @override
    def teardown(
        self, collector: MutNamedCollector[type, Any]
    ) -> Result[bool, ControllerError]:
        for idx, res_conf in enumerate(self._res_types):
            if (
                not self._values[idx]
                .map(
                    lambda value, res_conf=res_conf: collector.remove(
                        res_conf.type, value, name=res_conf.name
                    )
                )
                .unwrap_or(False)
                and res_conf.required
            ):
                return ControllerError.NoSuchResource(
                    name=f'{res_conf.type.__name__}'
                ).to_result()
        return super().teardown(collector)

    def _compile_operator_methods(self) -> None:
        for idx, res_conf in enumerate(self._res_types):
            method_name = f'_create_op_{res_conf.type.__name__}'
            fn_body = _FN_BODY_TEMPLATE.format(method_name=method_name)
            fn_code = compile(fn_body, _FN_BODY_TEMPLATE_FILE, 'exec', optimize=2)

            eval(
                fn_code,
                {
                    'AssignOperator': AssignOperator,
                    'res_conf': res_conf,
                    'idx': idx,
                    'self': self,
                    'partial': partial,
                },
                locals(),
            )
            fn = locals()[method_name]
            fn.__qualname__ = f'{self.__class__.__name__}.{method_name}'
            setattr(self, method_name, operator(res_conf.type)(fn))  # type: ignore
