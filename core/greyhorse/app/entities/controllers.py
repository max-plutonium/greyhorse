from typing import override

from greyhorse.result import Result, Ok
from ..abc.collectors import Collector, MutCollector
from ..abc.controllers import Controller, ControllerError
from ..abc.operators import Operator


class SyncController(Controller):
    @override
    def setup(
        self, collector: Collector[type, Operator],
    ) -> Result[bool, ControllerError]:
        return Ok(True)

    @override
    def teardown(
        self, collector: MutCollector[type, Operator],
    ) -> Result[bool, ControllerError]:
        return Ok(True)


class AsyncController(Controller):
    @override
    async def setup(
        self, collector: Collector[type, Operator],
    ) -> Result[bool, ControllerError]:
        return Ok(True)

    @override
    async def teardown(
        self, collector: MutCollector[type, Operator],
    ) -> Result[bool, ControllerError]:
        return Ok(True)
