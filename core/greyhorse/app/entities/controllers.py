from typing import override

from greyhorse.result import Result, Ok
from ..abc.collectors import Collector, MutCollector
from ..abc.controllers import Controller, ControllerError
from ..abc.operators import Operator
from ..abc.providers import Provider
from ..abc.selectors import Selector


class SyncController(Controller):
    @override
    def setup(
        self, selector: Selector[type[Provider], Provider],
        collector: Collector[type, Operator],
    ) -> Result[bool, ControllerError]:
        return Ok(True)

    @override
    def teardown(
        self, selector: Selector[type[Provider], Provider],
        collector: MutCollector[type, Operator],
    ) -> Result[bool, ControllerError]:
        return Ok(True)


class AsyncController(Controller):
    @override
    async def setup(
        self, selector: Selector[type[Provider], Provider],
        collector: Collector[type, Operator],
    ) -> Result[bool, ControllerError]:
        return Ok(True)

    @override
    async def teardown(
        self, selector: Selector[type[Provider], Provider],
        collector: MutCollector[type, Operator],
    ) -> Result[bool, ControllerError]:
        return Ok(True)
