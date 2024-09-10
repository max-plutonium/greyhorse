from typing import get_type_hints, override

from greyhorse.result import Ok, Result
from ..abc.controllers import Controller, ControllerError, OperatorMember
from ..abc.providers import Provider
from ..abc.selectors import ListSelector


def operator(resource_type: type):
    def decorator(func: classmethod):
        class_name, method_name = func.__qualname__.split('.')
        hints = get_type_hints(func, include_extras=True)
        ret_type = hints.pop('return', None)
        func.__operator__ = OperatorMember(
            class_name, method_name, resource_type, method=func, params=hints, ret_type=ret_type,
        )
        return func

    return decorator


class SyncController(Controller):
    @override
    def setup(
        self, providers: ListSelector[type[Provider], Provider],
    ) -> Result[bool, ControllerError]:
        return Ok(True)

    @override
    def teardown(
        self, providers: ListSelector[type[Provider], Provider],
    ) -> Result[bool, ControllerError]:
        return Ok(True)


class AsyncController(Controller):
    @override
    async def setup(
        self, providers: ListSelector[type[Provider], Provider],
    ) -> Result[bool, ControllerError]:
        return Ok(True)

    @override
    async def teardown(
        self, providers: ListSelector[type[Provider], Provider],
    ) -> Result[bool, ControllerError]:
        return Ok(True)
