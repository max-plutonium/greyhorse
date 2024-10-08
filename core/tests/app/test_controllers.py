from typing import Any

from greyhorse.app.abc.controllers import ControllerError
from greyhorse.app.abc.operators import Operator
from greyhorse.app.entities.controllers import ResConf, ResourceController
from greyhorse.app.registries import MutNamedDictRegistry
from greyhorse.maybe import Just, Maybe


def test_res_controller() -> None:
    confs = [
        ResConf(type=int, required=True),
        ResConf(type=str, required=False),
        ResConf(type=Maybe, required=True),
    ]

    instance = ResourceController(confs)

    registry = MutNamedDictRegistry[type, Any]()

    res = instance.setup(registry)
    assert res.is_err()
    assert res.unwrap_err() == ControllerError.NoSuchResource(name='int')

    res = instance.teardown(registry)
    assert res.is_err()
    assert res.unwrap_err() == ControllerError.NoSuchResource(name='int')

    int_op: Operator[int] = instance._create_op_int()  # noqa
    str_op: Operator[str] = instance._create_op_str()  # noqa
    maybe_op: Operator[Maybe] = instance._create_op_Maybe()  # noqa

    assert len(registry) == 0

    assert int_op.accept(123)
    assert instance.setup(registry).unwrap_err() == ControllerError.NoSuchResource(name='Maybe')
    assert len(registry) == 1

    assert str_op.accept('123')
    assert instance.setup(registry).unwrap_err() == ControllerError.NoSuchResource(name='Maybe')
    assert len(registry) == 2

    assert maybe_op.accept(Just(123))
    assert instance.setup(registry).is_ok()
    assert len(registry) == 3

    assert int_op.revoke().unwrap() == 123
    assert instance.teardown(registry).unwrap_err() == ControllerError.NoSuchResource(
        name='int'
    )
    assert len(registry) == 3

    assert int_op.accept(123)
    assert str_op.revoke().unwrap() == '123'
    assert instance.teardown(registry).is_ok()
    assert len(registry) == 1

    assert registry.items() == [(str, None, '123')]
    assert maybe_op.revoke().unwrap() == Just(123)
