from __future__ import annotations

from greyhorse.app.abc.operators import AssignOperator
from greyhorse.app.abc.providers import SharedProvider
from greyhorse.app.boxes import SharedRefBox
from greyhorse.app.builders.module import ModuleBuilder
from greyhorse.app.entities.controllers import SyncController, operator
from greyhorse.app.entities.services import SyncService, provider
from greyhorse.app.schemas.components import ModuleComponentConf, ModuleConf, ProvidersConf
from greyhorse.app.schemas.elements import CtrlConf, SvcConf
from greyhorse.maybe import Maybe, Nothing

from .common.functional import FunctionalOperator


class FunctionalOperatorService(SyncService):
    def __init__(self) -> None:
        super().__init__()
        self._res = None

    def set_res(self, res) -> None:
        self._res = res

    @provider(SharedProvider[FunctionalOperator])
    def create_op(self):
        if not self._res:
            return None
        return SharedRefBox(lambda: self._res, lambda v: v)


class FunctionalOperatorCtrl(SyncController):
    def __init__(self, svc: FunctionalOperatorService) -> None:
        super().__init__()
        self._a = Nothing
        self._svc = svc

    def _setter(self, value) -> None:
        self._a = value
        self._svc.set_res(value.unwrap_or_none())

    @operator(FunctionalOperator)
    def create_op(self):
        return AssignOperator[FunctionalOperator](lambda: self._a, self._setter)


def __init__():
    return ModuleConf(
        enabled=True,
        can_provide=[FunctionalOperator],
        components={
            'dict': ModuleComponentConf(
                enabled=True,
                path='..module.main',
                provider_imports=[
                    ProvidersConf(
                        resource=FunctionalOperator,
                        providers=[SharedProvider[FunctionalOperator]],
                    ),
                ],
                services=[SvcConf(type=FunctionalOperatorService)],
                controllers=[CtrlConf(type=FunctionalOperatorCtrl)],
            ),
        },
    )


def test_module() -> None:
    test_module_conf = __init__()

    module_builder = ModuleBuilder(test_module_conf, 'tests')
    res = module_builder.create_pass()
    assert res.is_ok()
    module = res.unwrap()

    op_maybe: Maybe[FunctionalOperator] = Nothing

    def assign(value) -> None:
        nonlocal op_maybe
        op_maybe = value

    sub_operator = AssignOperator[FunctionalOperator](lambda: op_maybe, assign)

    assert module.add_operator(sub_operator)

    res = module.setup()
    assert res.is_ok()

    print('OK')

    op = op_maybe.unwrap()

    res = op.add_number(123)
    assert res.is_ok()

    res = op.get_number()
    assert res.is_ok()
    assert res.unwrap() == 123

    res = op.remove_number()
    assert res.is_ok()
    assert res.unwrap() is True

    res = op.get_number()
    assert res.is_err()
    assert res.unwrap_err() == 'Number is not initialized'

    res = module.teardown()
    assert res.is_ok()
