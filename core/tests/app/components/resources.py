from typing import override, Any

from greyhorse.app.abc.collectors import Collector, MutCollector
from greyhorse.app.abc.controllers import ControllerError
from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import BorrowError, BorrowMutError, SharedProvider, MutProvider, Provider
from greyhorse.app.abc.selectors import Selector
from greyhorse.app.context import ContextBuilder, SyncContext, SyncMutContext
from greyhorse.app.entities.controllers import SyncController
from greyhorse.app.entities.services import SyncService, provider
from greyhorse.maybe import Maybe, Just
from greyhorse.result import Result, Ok
from ..common.resources import DictResContext, MutDictResContext, DictResource


class DictResContextImpl(SyncContext[DictResource]):
    ...


class MutDictResContextImpl(SyncMutContext[DictResource]):
    def __init__(self, orig_dict: DictResource, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._orig_dict = orig_dict

    @override
    def _apply(self, instance: DictResource):
        self._orig_dict.clear()
        self._orig_dict.update(instance)


class DictProviderImpl(SharedProvider[DictResContext], MutProvider[MutDictResContext]):
    def __init__(self, orig_dict: dict[str, Any]):
        self._orig_dict = orig_dict

    @override
    def borrow(self) -> Result[DictResContext, BorrowError]:
        ctx_builder = ContextBuilder[DictResContextImpl, DictResource](self._orig_dict.copy)
        return Ok(ctx_builder.build())

    @override
    def reclaim(self, instance: DictResContext):
        del instance

    @override
    def acquire(self) -> Result[MutDictResContext, BorrowMutError]:
        ctx_builder = ContextBuilder[MutDictResContextImpl, DictResource](
            self._orig_dict.copy, orig_dict=self._orig_dict,
        )
        return Ok(ctx_builder.build())

    @override
    def release(self, instance: MutDictResContext):
        del instance


class DictResourceCtrl(SyncController, Operator[DictResource]):
    def __init__(self):
        self._dict: dict[str, Any] = {}

    @override
    def accept(self, instance: DictResource) -> bool:
        self._dict.update(instance)
        return True

    @override
    def revoke(self) -> Maybe[DictResource]:
        return Just(self._dict)

    @override
    def setup(
        self, selector: Selector[type[Provider], Provider],
        collector: Collector[type, Operator],
    ) -> Result[bool, ControllerError]:
        res = collector.add(DictResource, self)
        return Ok(res)

    @override
    def teardown(
        self, selector: Selector[type[Provider], Provider],
        collector: MutCollector[type, Operator],
    ) -> Result[bool, ControllerError]:
        res = collector.remove(DictResource, self)
        return Ok(res)


class DictProviderService(SyncService):
    def __init__(self, operator: Operator[DictResource]):
        super().__init__()
        self._dict: dict[str, Any] = {}
        self._provider = DictProviderImpl(self._dict)
        self._operator = operator

    @provider(SharedProvider[DictResContext])
    def create_dict(self):
        return self._provider

    @provider(MutProvider[MutDictResContext])
    def create_mut_dict(self):
        return Ok(self._provider)
