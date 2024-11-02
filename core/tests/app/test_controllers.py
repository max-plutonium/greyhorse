from greyhorse.app.abc.controllers import ControllerError
from greyhorse.app.abc.operators import Operator
from greyhorse.app.entities.controllers import ResConf, ResourceController
from greyhorse.app.resources import make_container
from greyhorse.maybe import Just, Maybe


def test_res_controller() -> None:
    confs = [
        ResConf(type=int, required=True),
        ResConf(type=str, required=False),
        ResConf(type=Maybe, required=True),
    ]

    instance = ResourceController(confs)
    container = make_container()

    res = instance.setup(container)
    assert res.is_err()
    assert res.unwrap_err() == ControllerError.NoSuchResource(name='int')

    res = instance.teardown(container)
    assert res.is_err()
    assert res.unwrap_err() == ControllerError.NoSuchResource(name='int')

    operators = []
    instance.inspect(lambda member: operators.append(member.method()))

    int_op: Operator[int] = operators[0]
    str_op: Operator[str] = operators[1]
    maybe_op: Operator[Maybe] = operators[2]

    assert len(container.registry) == 0

    with container.context:
        assert int_op.accept(123)
        assert instance.setup(container).unwrap_err() == ControllerError.NoSuchResource(
            name='Maybe'
        )
        assert len(container.registry) == 1

    with container.context:
        assert str_op.accept('123')
        assert instance.setup(container).unwrap_err() == ControllerError.NoSuchResource(
            name='Maybe'
        )
        assert len(container.registry) == 2

    with container.context:
        assert maybe_op.accept(Just(123))
        assert instance.setup(container).is_ok()
        assert len(container.registry) == 3

    with container.context:
        assert instance.setup(container).is_ok()
        assert int_op.revoke().unwrap() == 123
        assert instance.teardown(container).unwrap_err() == ControllerError.NoSuchResource(
            name='int'
        )
        assert len(container.registry) == 3

    with container.context:
        assert int_op.accept(123)
        assert instance.setup(container).is_ok()
        assert str_op.revoke().unwrap() == '123'
        assert instance.teardown(container).is_ok()
        assert len(container.registry) == 1

    assert maybe_op.revoke().unwrap() == Just(123)
