from typing import override

from greyhorse.app.abc.collectors import Collector, MutCollector
from greyhorse.app.abc.controllers import ControllerError
from greyhorse.app.abc.operators import Operator
from greyhorse.app.abc.providers import FactoryProvider, FactoryError, Provider
from greyhorse.app.abc.selectors import Selector
from greyhorse.app.abc.services import ProvisionError
from greyhorse.app.entities.controllers import SyncController
from greyhorse.app.entities.services import SyncService, provider
from greyhorse.maybe import Maybe, Nothing, Just
from greyhorse.result import Result, Ok, Err, do
from ..common.functional import FunctionalOperator, FunctionalOpProvider
from ..common.resources import DictResContext, MutDictResContext, DictCtxProvider, DictMutCtxProvider


class FunctionalOperatorImpl(FunctionalOperator):
    def __init__(self, ctx: DictResContext, mut_ctx: MutDictResContext):
        self.ctx = ctx
        self.mut_ctx = mut_ctx

    @override
    def add_number(self, value: int) -> Result[None, str]:
        with self.mut_ctx as ctx:
            ctx['number'] = value
            self.mut_ctx.apply()

        return Ok(None)

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
    def __init__(self, ctx_prov: DictCtxProvider, mut_ctx_prov: DictMutCtxProvider):
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
                return FactoryError.Internal(
                    name='FunctionalOperator', details=e,
                ).to_result()

        return FactoryError.Internal(
            name='FunctionalOperator', details='Unexpected return',
        ).to_result()

    @override
    def destroy(self, instance: FunctionalOperatorImpl):
        self._mut_ctx_prov.release(instance.mut_ctx)
        self._ctx_prov.reclaim(instance.ctx)
        del instance


class DictOperatorCtrl(SyncController):
    def __init__(self):
        self._provider: Maybe[FunctionalOpProviderImpl] = Nothing

    def get_provider(self):
        return self._provider

    @override
    def setup(
        self, selector: Selector[type[Provider], Provider],
        collector: Collector[type, Operator],
    ) -> Result[bool, ControllerError]:
        if self._provider:
            return Ok(True)

        res = do(
            Ok((ctx_prov, mut_ctx_prov))
            for ctx_prov in selector.get(DictCtxProvider).ok_or('Could not get DictCtxProvider')
            for mut_ctx_prov in selector.get(DictMutCtxProvider).ok_or('Could not get DictMutCtxProvider')
        ).map_err(lambda e: ControllerError.Deps(details=e))

        if not res:
            return res

        ctx_prov, mut_ctx_prov = res.unwrap()
        self._provider = Just(FunctionalOpProviderImpl(ctx_prov, mut_ctx_prov))
        return Ok(True)

    @override
    def teardown(
        self, selector: Selector[type[Provider], Provider],
        collector: MutCollector[type, Operator],
    ) -> Result[bool, ControllerError]:
        if not self._provider:
            return Ok(False)

        prov, self._provider = self._provider, Nothing
        del prov
        return Ok(True)


class DictOperatorService(SyncService):
    def __init__(self, ctrl: DictOperatorCtrl):
        super().__init__()
        self._ctrl = ctrl

    @provider(FunctionalOpProvider)
    def create_op(self) -> Result[FunctionalOpProvider, ProvisionError]:
        return self._ctrl.get_provider().ok_or(ProvisionError.NoSuchProvider(type_=FunctionalOpProvider.__name__))
