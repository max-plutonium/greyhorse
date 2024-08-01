from greyhorse.result import Result, Ok, do
from ..abc.controllers import Controller, ControllerError
from ..abc.operators import Operator
from ..abc.providers import Provider, SharedProvider, MutProvider, FactoryProvider, ForwardProvider
from ..abc.selectors import Selector


class OperatorController[T: Provider](Controller):
    init_method: str
    fini_method: str

    def __init__(
        self, class_from: type[T], class_to: type[Operator],
        key_from: str | None = None, key_to: str | None = None,
    ):
        self._class_from = class_from
        self._class_to = class_to
        self._key_from = key_from
        self._key_to = key_to

    def setup(
        self, prov_selector: Selector[T], op_selector: Selector[Operator],
    ) -> Result[bool, ControllerError]:
        return do(
            Ok(r)
            for p in prov_selector.get(class_=self._class_from, key=self._key_from) \
                .ok_or(f'Provider "{self._class_from.__name__}" not found for key "{self._key_from}"')
            for o in op_selector.get(class_=self._class_to, key=self._key_to) \
                .ok_or(f'Operator "{self._class_to.__name__}" not found for keys "{self._key_to}"')
            for r in getattr(p, self.init_method)().map_err(lambda e: e.message).map(o.accept)
        ).map_err(lambda e: ControllerError.Deps(details=e))

    def teardown(
        self, prov_selector: Selector[T], op_selector: Selector[Operator],
    ) -> Result[bool, ControllerError]:
        return do(
            Ok(r)
            for p in prov_selector.get(class_=self._class_from, key=self._key_from) \
                .ok_or(f'Provider "{self._class_from.__name__}" not found for key "{self._key_from}"')
            for o in op_selector.get(class_=self._class_to, key=self._key_to) \
                .ok_or(f'Operator "{self._class_to.__name__}" not found for keys "{self._key_to}"')
            for r in o.revoke().map(getattr(p, self.fini_method)).ok_or('Couldn\'t revoke')
        ).map_err(lambda e: ControllerError.Deps(details=e)).map(lambda _: True)


class BorrowOpController(OperatorController[SharedProvider]):
    init_method = 'borrow'
    fini_method = 'reclaim'


class AcquireOpController(OperatorController[MutProvider]):
    init_method = 'acquire'
    fini_method = 'release'


class FactoryOpController(OperatorController[FactoryProvider]):
    init_method = 'create'
    fini_method = 'destroy'


class ForwardOpController(OperatorController[ForwardProvider]):
    init_method = 'take'
    fini_method = 'drop'
