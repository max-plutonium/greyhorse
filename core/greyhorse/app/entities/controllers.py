from typing import Any, get_type_hints, override

from greyhorse.result import Ok, Result

from ..abc.collectors import Collector, MutCollector
from ..abc.controllers import Controller, ControllerError, OperatorMember


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
    def setup(self, collector: Collector[type, Any]) -> Result[bool, ControllerError]:
        return Ok(True)

    @override
    def teardown(self, collector: MutCollector[type, Any]) -> Result[bool, ControllerError]:
        return Ok(True)


class AsyncController(Controller):
    @override
    async def setup(self, collector: Collector[type, Any]) -> Result[bool, ControllerError]:
        return Ok(True)

    @override
    async def teardown(
        self, collector: MutCollector[type, Any],
    ) -> Result[bool, ControllerError]:
        return Ok(True)
