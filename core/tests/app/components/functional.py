from typing import Any, override

from greyhorse.app.abc.collectors import MutNamedCollector, NamedCollector
from greyhorse.app.abc.controllers import ControllerError
from greyhorse.app.abc.operators import AssignOperator, Operator
from greyhorse.app.abc.providers import FactoryError, ForwardProvider
from greyhorse.app.abc.selectors import NamedListSelector, NamedSelector
from greyhorse.app.abc.services import ServiceError, ServiceState
from greyhorse.app.boxes import ForwardBox
from greyhorse.app.entities.controllers import SyncController, operator
from greyhorse.app.entities.services import SyncService, provider
from greyhorse.maybe import Maybe, Nothing
from greyhorse.result import Ok, Result

from ..common.functional import FunctionalOperator, FunctionalOpProvider
from ..common.resources import DictResContext, MutDictResContext


class FunctionalOperatorImpl(FunctionalOperator):
    def __init__(self, ctx: DictResContext, mut_ctx: MutDictResContext) -> None:
        self.ctx = ctx
        self.mut_ctx = mut_ctx

    @override
    def add_number(self, value: int) -> Result[None, str]:
        with self.mut_ctx as ctx:
            ctx['number'] = value
            self.mut_ctx.apply()

        return Ok()

    @override
    def get_number(self) -> Result[int, str]:
        with self.ctx as ctx:
            value = Maybe(ctx.get('number'))

        return value.ok_or('Number is not initialized')

    @override
    def remove_number(self) -> Result[bool, str]:
        with self.mut_ctx as ctx:
            value = Maybe(ctx.pop('number', None))
            self.mut_ctx.apply()

        return value.ok_or('Number is not initialized').map(lambda _: True)


class DictOperatorService1(SyncService):
    def __init__(self) -> None:
        super().__init__()
        self._res1 = ForwardBox[DictResContext]()

    @override
    def setup(
        self, res: Maybe[DictResContext], selector: NamedSelector[type, Any]
    ) -> Result[ServiceState, ServiceError]:
        if not res:
            return ServiceError.NoSuchResource(name='DictResContext').to_result()
        if not selector.has(DictResContext):
            return ServiceError.NoSuchResource(name='DictResContext').to_result()
        self._res1.accept(res.unwrap())
        return super().setup()

    @override
    def teardown(
        self, res: Maybe[DictResContext], selector: NamedSelector[type, Any]
    ) -> Result[ServiceState, ServiceError]:
        if not res:
            return ServiceError.NoSuchResource(name='DictResContext').to_result()
        if not selector.has(DictResContext):
            return ServiceError.NoSuchResource(name='DictResContext').to_result()
        self._res1.revoke()
        return super().teardown()

    def start(self) -> None:
        self._switch_to_active(True)

    def stop(self) -> None:
        self._switch_to_active(False)

    @provider(ForwardProvider[DictResContext])
    def create_prov(self) -> ForwardProvider[DictResContext]:
        return self._res1


class DictOperatorService2(SyncService):
    def __init__(self) -> None:
        super().__init__()
        self._res2: MutDictResContext | None = None

    @override
    def setup(
        self, res: Maybe[MutDictResContext], list_selector: NamedListSelector[type, Any]
    ) -> Result[ServiceState, ServiceError]:
        if not res:
            return ServiceError.NoSuchResource(name='MutDictResContext').to_result()
        if not list_selector.has(MutDictResContext):
            return ServiceError.NoSuchResource(name='MutDictResContext').to_result()
        self._res2 = res.unwrap()
        return super().setup()

    @override
    def teardown(
        self, res: Maybe[MutDictResContext], list_selector: NamedListSelector[type, Any]
    ) -> Result[ServiceState, ServiceError]:
        if not res:
            return ServiceError.NoSuchResource(name='MutDictResContext').to_result()
        if not list_selector.has(MutDictResContext):
            return ServiceError.NoSuchResource(name='MutDictResContext').to_result()
        self._res2 = None
        return super().teardown()

    def start(self) -> None:
        self._switch_to_active(True)

    def stop(self) -> None:
        self._switch_to_active(False)

    @provider(FunctionalOpProvider)
    def create_prov(
        self, dependency: ForwardProvider[DictResContext]
    ) -> Result[FunctionalOpProvider, FactoryError] | None:
        if not dependency:
            return FactoryError.InsufficientDeps(name='DictResContext').to_result()
        if not self._res2:
            return None
        res1 = dependency.take().unwrap()
        yield FunctionalOperatorImpl(res1, self._res2)
        dependency.drop(res1)


class DictOperatorCtrl(SyncController):
    def __init__(self) -> None:
        super().__init__()
        self._a: Maybe[DictResContext] = Nothing
        self._b: Maybe[MutDictResContext] = Nothing

    def _setter1(self, value: Maybe[DictResContext]) -> None:
        self._a = value

    def _setter2(self, value: Maybe[MutDictResContext]) -> None:
        self._b = value

    @override
    def setup(self, collector: NamedCollector[type, Any]) -> Result[bool, ControllerError]:
        if not self._a:
            return ControllerError.NoSuchResource(name='DictResContext').to_result()
        if not self._b:
            return ControllerError.NoSuchResource(name='MutDictResContext').to_result()
        collector.add(DictResContext, self._a.unwrap())
        collector.add(MutDictResContext, self._b.unwrap())
        return super().setup(collector)

    @override
    def teardown(
        self, collector: MutNamedCollector[type, Any]
    ) -> Result[bool, ControllerError]:
        if not self._a:
            return ControllerError.NoSuchResource(name='DictResContext').to_result()
        if not self._b:
            return ControllerError.NoSuchResource(name='MutDictResContext').to_result()
        collector.remove(DictResContext, self._a.unwrap())
        collector.remove(MutDictResContext, self._b.unwrap())
        return super().teardown(collector)

    @operator(DictResContext)
    def create_op1(self) -> Operator[DictResContext]:
        return AssignOperator[DictResContext](lambda: self._a, self._setter1)

    @operator(MutDictResContext)
    def create_op2(self) -> Operator[MutDictResContext]:
        return AssignOperator[MutDictResContext](lambda: self._b, self._setter2)
