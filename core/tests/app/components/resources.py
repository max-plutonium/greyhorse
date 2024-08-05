from typing import override, Any

from greyhorse.app.abc.providers import BorrowError, BorrowMutError, SharedProvider, MutProvider
from greyhorse.app.context import ContextBuilder, SyncContext, SyncMutContext
from greyhorse.app.entities.controllers import SyncController
from greyhorse.app.entities.services import SyncService, provider
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


class DictResourceCtrl(SyncController):
    def __init__(self):
        self._dict: dict[str, Any] = {}
        self._provider = DictProviderImpl(self._dict)

    def get_provider(self):
        return self._provider


class DictProviderService(SyncService):
    def __init__(self, ctrl: DictResourceCtrl):
        super().__init__()
        self._ctrl = ctrl

    @provider(SharedProvider[DictResContext])
    def create_dict(self):
        return self._ctrl.get_provider()

    @provider(MutProvider[MutDictResContext])
    def create_mut_dict(self):
        return Ok(self._ctrl.get_provider())
