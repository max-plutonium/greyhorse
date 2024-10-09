from copy import deepcopy
from functools import partial

from greyhorse.app.abc.providers import BorrowMutError, MutProvider, SharedProvider
from greyhorse.app.boxes import OwnerCtxRefBox
from greyhorse.app.contexts import MutCtxCallbacks, SyncContext, SyncMutContextWithCallbacks
from greyhorse.app.entities.services import SyncService, provider
from greyhorse.maybe import Just
from greyhorse.result import Ok, Result

from ..common.resources import DictResContext, DictResource, MutDictResContext


class DictResourceBox(OwnerCtxRefBox[DictResource, DictResource]):
    allow_borrow_when_acquired = True
    allow_acq_when_borrowed = True
    allow_multiple_acquisition = False


class DictProviderService(SyncService):
    def __init__(self) -> None:
        super().__init__()
        self._value = {}
        self._box = DictResourceBox(
            SyncContext,
            SyncMutContextWithCallbacks,
            partial(deepcopy, self._value),
            partial(deepcopy, self._value),
            mut_params=dict(callbacks=MutCtxCallbacks(on_apply=Just(self._setter))),
        )

    def _setter(self, value: DictResource) -> None:
        self._value.clear()
        self._value.update(value)

    @provider(SharedProvider[DictResContext])
    def create_dict(self) -> SharedProvider[DictResContext]:
        return self._box

    @provider(MutProvider[MutDictResContext])
    def create_mut_dict(self) -> Result[MutProvider[MutDictResContext], BorrowMutError]:
        return Ok(self._box)
