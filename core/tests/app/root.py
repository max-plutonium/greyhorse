from greyhorse.app.abc.operators import AssignOperator
from greyhorse.app.abc.providers import SharedProvider
from greyhorse.app.boxes import SharedRefBox
from greyhorse.app.entities.controllers import SyncController, operator
from greyhorse.app.entities.services import SyncService, provider
from greyhorse.maybe import Maybe, Nothing

from .common.functional import FunctionalOperator


class FunctionalOperatorService(SyncService):
    def __init__(self) -> None:
        super().__init__()
        self._res = Nothing

    def get_res(self) -> Maybe[FunctionalOperator]:
        return self._res

    def set_res(self, res: Maybe[FunctionalOperator]) -> None:
        self._res = res

    @provider(SharedProvider[FunctionalOperator])
    def create_op(self):
        if not self._res:
            return None
        return SharedRefBox(self.get_res, lambda v: v)


class FunctionalOperatorCtrl(SyncController):
    def __init__(self, svc: FunctionalOperatorService) -> None:
        super().__init__()
        self._svc = svc

    @operator(FunctionalOperator)
    def create_op(self):
        return AssignOperator[FunctionalOperator](self._svc.get_res, self._svc.set_res)
