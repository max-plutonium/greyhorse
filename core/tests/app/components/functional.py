from typing import Any, override

from greyhorse.app.abc.collectors import MutNamedCollector, NamedCollector
from greyhorse.app.abc.controllers import ControllerError
from greyhorse.app.abc.operators import AssignOperator, Operator
from greyhorse.app.abc.providers import FactoryError, FactoryProvider
from greyhorse.app.abc.selectors import NamedListSelector, NamedSelector
from greyhorse.app.abc.services import ProvisionError, ServiceError, ServiceState
from greyhorse.app.boxes import ForwardBox
from greyhorse.app.entities.controllers import SyncController, operator
from greyhorse.app.entities.services import SyncService, provider
from greyhorse.maybe import Maybe, Nothing
from greyhorse.result import Err, Ok, Result, do

from ..common.functional import FunctionalOperator, FunctionalOpProvider
from ..common.resources import (
    DictCtxProvider,
    DictMutCtxProvider,
    DictResContext,
    MutDictResContext,
)


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


class FunctionalOpProviderImpl(FactoryProvider[FunctionalOperator]):
    def __init__(self, ctx_prov: DictCtxProvider, mut_ctx_prov: DictMutCtxProvider) -> None:
        self._ctx_prov = ctx_prov
        self._mut_ctx_prov = mut_ctx_prov

    @override
    def create(self) -> Result[FunctionalOperator, FactoryError]:
        result: Result[tuple[DictResContext, MutDictResContext], str] = do(
            Ok((c1, c2))
            for c1 in self._ctx_prov.borrow()
            for c2 in self._mut_ctx_prov.acquire()
        )

        match result:
            case Ok((ctx, mut_ctx)):
                return Ok(FunctionalOperatorImpl(ctx, mut_ctx))
            case Err(e):
                return FactoryError.Internal(name='FunctionalOperator', details=e).to_result()

        return FactoryError.Internal(
            name='FunctionalOperator', details='Unexpected return'
        ).to_result()

    @override
    def destroy(self, instance: FunctionalOperatorImpl) -> None:
        self._mut_ctx_prov.release(instance.mut_ctx)
        self._ctx_prov.reclaim(instance.ctx)
        del instance


class DictOperatorService(SyncService):
    def __init__(self) -> None:
        super().__init__()
        self._res1 = None
        self._res2 = None

    @override
    def setup(
        self,
        res1: Maybe[DictResContext],
        res2: Maybe[MutDictResContext],
        selector: NamedSelector[type, Any],
        list_selector: NamedListSelector[type, Any],
    ) -> Result[ServiceState, ServiceError]:
        if not res1:
            return ServiceError.NoSuchResource(name='DictResContext').to_result()
        if not res2:
            return ServiceError.NoSuchResource(name='MutDictResContext').to_result()
        if not selector.has(DictResContext):
            return ServiceError.NoSuchResource(name='DictResContext').to_result()
        if not list_selector.has(DictResContext):
            return ServiceError.NoSuchResource(name='DictResContext').to_result()
        self._res1 = res1.unwrap()
        self._res2 = res2.unwrap()
        return super().setup()

    @override
    def teardown(
        self,
        res: Maybe[DictResContext],
        selector: NamedSelector[type, Any],
        list_selector: NamedListSelector[type, Any],
    ) -> Result[ServiceState, ServiceError]:
        if not res:
            return ServiceError.NoSuchResource(name='DictResContext').to_result()
        if not selector.has(DictResContext):
            return ServiceError.NoSuchResource(name='DictResContext').to_result()
        if not list_selector.has(DictResContext):
            return ServiceError.NoSuchResource(name='DictResContext').to_result()
        self._res1 = None
        self._res2 = None
        return super().teardown()

    def start(self) -> None:
        self._switch_to_active(True)

    def stop(self) -> None:
        self._switch_to_active(False)

    @provider(FunctionalOpProvider)
    def create_prov(self) -> Result[FunctionalOpProvider, ProvisionError]:
        return Ok(ForwardBox(FunctionalOperatorImpl(self._res1, self._res2)))


class DictOperatorCtrl(SyncController):
    def __init__(self) -> None:
        super().__init__()
        self._a = Nothing
        self._b = Nothing

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
