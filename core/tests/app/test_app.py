from greyhorse.app.abc.providers import FactoryProvider
from greyhorse.app.entities.application import Application
from greyhorse.app.schemas.components import ModuleComponentConf, ModuleConf
from greyhorse.app.schemas.elements import CtrlConf, SvcConf

from .root import FunctionalOperatorCtrl, FunctionalOperatorService
from .testmodule.common.functional import FunctionalOperator


def test_app() -> None:
    app_conf = ModuleConf(
        enabled=True,
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

    app = Application('TestApp')

    res = app.load(app_conf)
    assert res.is_ok()

    res = app.setup()
    assert res.is_ok()

    print('OK')

    prov = app.get_provider(FactoryProvider[FunctionalOperator])
    assert prov.is_just()

    prov = prov.unwrap()
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

    assert app.start()

    # with app.graceful_exit():
    # app.run_sync()
    # await app.run_async()

    assert app.stop()

    prov.destroy(op)

    res = app.teardown()
    assert res.is_ok()

    res = app.unload()
    assert res.is_ok()
