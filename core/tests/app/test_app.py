from greyhorse.app.abc.providers import SharedProvider
from greyhorse.app.entities.application import Application
from greyhorse.app.schemas.components import ModuleComponentConf
from greyhorse.app.schemas.elements import CtrlConf, SvcConf

from .common.functional import FunctionalOperator
from .root import FunctionalOperatorCtrl, FunctionalOperatorService


def test_app() -> None:
    app_conf = ModuleComponentConf(
        enabled=True,
        path='..module.main',
        providers=[SharedProvider[FunctionalOperator]],
        services=[SvcConf(type=FunctionalOperatorService)],
        controllers=[CtrlConf(type=FunctionalOperatorCtrl)],
    )

    app = Application('TestApp')

    res = app.load(app_conf)
    assert res.is_ok()

    res = app.setup()
    assert res.is_ok()

    print('OK')

    prov = app.get_provider(SharedProvider[FunctionalOperator])
    assert prov.is_just()

    prov = prov.unwrap()
    op = prov.borrow().unwrap()

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

    res = app.teardown()
    assert res.is_ok()

    res = app.unload()
    assert res.is_ok()
