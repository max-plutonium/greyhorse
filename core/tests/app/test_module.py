from __future__ import annotations

from greyhorse.app.abc.providers import FactoryProvider
from greyhorse.app.builders.module import ModuleBuilder
from greyhorse.app.schemas.components import ModuleComponentConf, ModuleConf
from greyhorse.app.schemas.elements import CtrlConf, SvcConf

from .root import FunctionalOperatorCtrl, FunctionalOperatorService
from .testmodule.common.functional import FunctionalOperator


def __init__() -> ModuleConf:  # noqa: N807
    return ModuleConf(
        enabled=True,
        operators=[FunctionalOperator],
        providers=[FactoryProvider[FunctionalOperator]],
        components={
            'dict': ModuleComponentConf(
                enabled=True,
                path='..testmodule.module',
                providers=[FactoryProvider[FunctionalOperator]],
                services=[SvcConf(type=FunctionalOperatorService)],
                controllers=[CtrlConf(type=FunctionalOperatorCtrl)],
            )
        },
    )


def test_module() -> None:
    module_conf = __init__()

    module_builder = ModuleBuilder(module_conf, 'tests')
    res = module_builder.create_pass()
    assert res.is_ok()
    module = res.unwrap()

    res = module.create()
    assert res.is_ok()

    res = module.setup()
    assert res.is_ok()

    prov = module.get_provider(FactoryProvider[FunctionalOperator]).unwrap()

    print('OK')

    op = prov.create().unwrap()

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

    prov.destroy(op)

    res = module.teardown()
    assert res.is_ok()

    res = module.destroy()
    assert res.is_ok()
