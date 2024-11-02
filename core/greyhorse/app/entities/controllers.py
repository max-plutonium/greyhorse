from collections.abc import Callable, Iterable
from functools import partial
from typing import Any, cast, get_type_hints, override

from pydantic import BaseModel

from greyhorse.maybe import Maybe, Nothing
from greyhorse.result import Ok, Result

from ..abc.controllers import Controller, ControllerError, OperatorMember
from ..abc.operators import AssignOperator
from ..resources import Container


class ResConf(BaseModel, frozen=True):
    type: type
    name: str | None = None
    required: bool = True


def operator(resource_type: type) -> Callable[[classmethod], classmethod]:
    def decorator(func: classmethod) -> classmethod:
        hints = get_type_hints(func, include_extras=True)
        ret_type = hints.pop('return', None)
        func.__operator__ = OperatorMember(
            resource_type, method=func, params=hints, ret_type=ret_type
        )
        return func

    return decorator


class SyncController(Controller):
    @override
    def setup(self, *args, **kwargs) -> Result[bool, ControllerError]:  # noqa: ANN002,ANN003
        return Ok(True)

    @override
    def teardown(self, *args, **kwargs) -> Result[bool, ControllerError]:  # noqa: ANN002,ANN003
        return Ok(True)


class AsyncController(Controller):
    @override
    async def setup(self, *args, **kwargs) -> Result[bool, ControllerError]:  # noqa: ANN002,ANN003
        return Ok(True)

    @override
    async def teardown(self, *args, **kwargs) -> Result[bool, ControllerError]:  # noqa: ANN002,ANN003
        return Ok(True)


class ResourceController(SyncController):
    def __init__(self, resources: Iterable[ResConf]) -> None:
        super().__init__()
        self._res_types = resources
        self._values: list[Maybe[Any]] = [Nothing for _ in self._res_types]
        self._compile_operator_methods()

    def _getter(self, idx: int) -> Maybe[Any]:
        if 0 <= idx < len(self._values):
            return self._values[idx]
        return Nothing

    def _setter(self, idx: int, value: Maybe[Any]) -> None:
        if 0 <= idx < len(self._values):
            self._values[idx] = value

    @override
    def setup(self, container: Container) -> Result[bool, ControllerError]:
        for idx, res_conf in enumerate(self._res_types):
            type_ = res_conf.type

            if (
                not self._values[idx]
                .map(lambda value, type=type_: container.registry.add_factory(type, value))
                .map(lambda _: True)
                .unwrap_or(False)
                and res_conf.required
            ):
                return ControllerError.NoSuchResource(name=f'{type_.__name__}').to_result()

        return super().setup()

    @override
    def teardown(self, container: Container) -> Result[bool, ControllerError]:
        for idx, res_conf in enumerate(self._res_types):
            type_ = res_conf.type

            if (
                not self._values[idx]
                .map(lambda _, type=type_: container.registry.remove_factory(type))
                .map(lambda _: True)
                .unwrap_or(False)
                and res_conf.required
            ):
                return ControllerError.NoSuchResource(name=f'{type_.__name__}').to_result()

        return super().teardown()

    def _compile_operator_methods(self) -> None:
        for idx, res_conf in enumerate(self._res_types):
            method_name = f'_create_op_{res_conf.type.__name__}'

            def func(self, idx=idx, res_conf=res_conf):  # noqa
                return AssignOperator[res_conf.type](
                    partial(self._getter, idx), partial(self._setter, idx)
                )

            func.__qualname__ = f'{self.__class__.__name__}.{method_name}'
            func = cast(classmethod, partial(func, self=self))

            member = OperatorMember(res_conf.type, method=func, params={})
            self._operator_members[res_conf.type] = member
